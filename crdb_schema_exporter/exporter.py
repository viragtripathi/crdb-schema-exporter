import os
import csv
import gzip
import json
import yaml
import tarfile
import logging
from logging.handlers import TimedRotatingFileHandler
import difflib
import click
import importlib.metadata
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from concurrent.futures import ThreadPoolExecutor, as_completed

# Default logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Setup logging
def setup_logging(log_dir, verbose):
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, "crdb_exporter.log")
    file_handler = TimedRotatingFileHandler(log_filename, when='midnight', interval=1, backupCount=7)
    file_handler.setFormatter(log_formatter)
    file_handler.suffix = "%Y-%m-%d"
    logger.addHandler(file_handler)

    logger.info(f"Logging to file: {log_filename}")
    return logger

# File writing helpers
def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)
    logger.info(f"Wrote: {path}")

def archive_output(directory):
    archive_name = f"{directory}.tar.gz"
    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(directory, arcname=os.path.basename(directory))
    logger.info(f"Archived output to {archive_name}")

def dump_create_statement(engine, obj_type, full_name):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SHOW CREATE {obj_type} {full_name}"))
            rows = list(result)
            if rows and len(rows[0]) > 1:
                return rows[0][1] + ";\n"
            else:
                logger.warning(f"No DDL returned for {obj_type} {full_name}")
                return None
    except SQLAlchemyError as e:
        logger.error(f"Failed to get DDL for {obj_type} {full_name}: {e}")
        return None

def collect_objects(engine, db, obj_type):
    query_map = {
        'table': "SHOW TABLES",
        'view': "SELECT table_name FROM information_schema.views WHERE table_schema NOT IN ('pg_catalog', 'information_schema')",
        'sequence': "SHOW SEQUENCES",
        'type': "SHOW TYPES"
    }
    objs = []
    try:
        with engine.connect() as conn:
            conn.execute(text(f"USE {db}"))
            result = conn.execute(text(query_map[obj_type]))
            for row in result:
                name = row[0] if obj_type == 'view' else row[1] if obj_type in ['table', 'sequence', 'type'] else None
                if name:
                    objs.append(f"{db}.{name}")
    except SQLAlchemyError as e:
        logger.error(f"Error fetching {obj_type}s: {e}")
    return objs

def export_table_data(engine, table, out_dir, export_format, split, limit, compress):
    try:
        db, tbl = table.split('.')
        base_name = tbl.replace('.', '_')
        with engine.connect() as conn:
            cols_res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{tbl}'"))
            columns = [row[0] for row in cols_res]

            offset = 0
            batch_size = 1000
            all_rows = []

            while True:
                query = f"SELECT * FROM {table} OFFSET {offset} LIMIT {batch_size}"
                if limit and offset >= limit:
                    break
                rows = conn.execute(text(query)).fetchall()
                if not rows:
                    break
                all_rows.extend(rows)
                offset += batch_size
                if limit and len(all_rows) >= limit:
                    all_rows = all_rows[:limit]
                    break

            out_path = os.path.join(out_dir, f"{base_name}.csv.gz" if compress else f"{base_name}.csv") if export_format == 'csv' else os.path.join(out_dir, f"{base_name}_data.sql")

            if export_format == 'csv':
                open_func = gzip.open if compress else open
                mode = 'wt' if compress else 'w'
                with open_func(out_path, mode, newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(all_rows)
            elif export_format == 'sql':
                with open(out_path, 'w') as f:
                    for row in all_rows:
                        vals = ", ".join([repr(v).replace("'", "''") if v is not None else 'NULL' for v in row])
                        f.write(f"INSERT INTO {tbl} ({', '.join(columns)}) VALUES ({vals});\n")

            logger.info(f"Exported data for {table} to {out_path}")

    except SQLAlchemyError as e:
        logger.error(f"Failed to export data for {table}: {e}")

@click.command()
@click.option('--db', required=True, help='Database name')
@click.option('--host', default='localhost', help='CRDB host')
@click.option('--certs-dir', default=None, help='Path to TLS certs directory')
@click.option('--tables', default=None, help='Comma-separated list of db.table names')
@click.option('--per-table', is_flag=True, help='Output per-object files')
@click.option('--format', 'out_format', type=click.Choice(['sql', 'json', 'yaml']), default='sql', help='Schema output format')
@click.option('--archive', is_flag=True, help='Compress output directory')
@click.option('--diff', 'diff_file', default=None, help='Compare output with existing SQL file')
@click.option('--parallel', is_flag=True, help='Enable parallel DDL export')
@click.option('--verbose', is_flag=True, help='Enable debug logging')
@click.option('--log-dir', default='logs', help='Directory to store log files')
@click.option('--data', is_flag=True, help='Dump table data as INSERT or CSV')
@click.option('--data-format', type=click.Choice(['sql', 'csv']), default='sql', help='Data export format')
@click.option('--data-split', is_flag=True, help="Write each table's data to a separate file")
@click.option('--data-limit', type=int, default=None, help='Limit number of rows per table')
@click.option('--data-compress', is_flag=True, help='Compress CSV data output as .csv.gz')
@click.version_option(importlib.metadata.version("crdb-schema-exporter"))
def main(db, host, certs_dir, tables, per_table, out_format, archive, diff_file, parallel, verbose, log_dir, data, data_format, data_split, data_limit, data_compress):
    global logger
    logger = setup_logging(log_dir, verbose)

    out_dir = f"crdb_schema_dumps/{db}"
    os.makedirs(out_dir, exist_ok=True)

    conn_url = f"cockroachdb://root@{host}:26257/{db}"
    if certs_dir:
        conn_url += f"?sslmode=verify-full&sslrootcert={certs_dir}/ca.crt&sslcert={certs_dir}/client.root.crt&sslkey={certs_dir}/client.root.key"
    else:
        conn_url += "?sslmode=disable"

    engine = create_engine(conn_url, echo=verbose)

    table_list = tables.split(',') if tables else collect_objects(engine, db, 'table')
    views = collect_objects(engine, db, 'view')
    sequences = collect_objects(engine, db, 'sequence')
    types = collect_objects(engine, db, 'type')

    all_objects = [("TABLE", name) for name in table_list] + \
                  [("VIEW", name) for name in views] + \
                  [("SEQUENCE", name) for name in sequences] + \
                  [("TYPE", name) for name in types]

    dump_data = []

    def process_object(obj_type, full_name):
        ddl = dump_create_statement(engine, obj_type, full_name)
        if ddl:
            if out_format in ["json", "yaml"]:
                dump_data.append({"name": full_name, "type": obj_type, "ddl": ddl.strip()})
            elif per_table:
                filename = f"{out_dir}/{obj_type.lower()}_{full_name.split('.')[-1]}.sql"
                write_file(filename, f"-- {obj_type}: {full_name}\n{ddl}\n")
            else:
                with open(f"{out_dir}/{db}_schema.sql", "a") as f:
                    f.write(f"-- {obj_type}: {full_name}\n{ddl}\n\n")

    if parallel:
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_object, obj_type, full_name) for obj_type, full_name in all_objects]
            for future in as_completed(futures):
                future.result()
    else:
        for obj_type, full_name in all_objects:
            process_object(obj_type, full_name)

    if out_format == "json":
        write_file(f"{out_dir}/{db}_schema.json", json.dumps(dump_data, indent=2))
    elif out_format == "yaml":
        write_file(f"{out_dir}/{db}_schema.yaml", yaml.dump(dump_data))

    if data:
        for table in table_list:
            export_table_data(engine, table, out_dir, data_format, data_split, data_limit, data_compress)

    if diff_file:
        diff_result = diff_schemas(f"{out_dir}/{db}_schema.sql", diff_file)
        print("\n🕵️  Schema Diff:")
        print(diff_result if diff_result else "No differences found.")

        diff_path = os.path.join(out_dir, f"{db}_schema.diff")
        with open(diff_path, "w") as f:
            f.write(diff_result if diff_result else "No differences found.\n")
        logger.info(f"Diff saved to: {diff_path}")

    if archive:
        archive_output(out_dir)

if __name__ == '__main__':
    main()
