[![PyPI version](https://img.shields.io/pypi/v/crdb-schema-exporter)](https://pypi.org/project/crdb-schema-exporter/)
[![Python versions](https://img.shields.io/pypi/pyversions/crdb-schema-exporter)](https://pypi.org/project/crdb-schema-exporter/)
[![License](https://img.shields.io/pypi/l/crdb-schema-exporter)](https://pypi.org/project/crdb-schema-exporter/)
[![Build status](https://github.com/viragtripathi/crdb-schema-exporter/actions/workflows/python-ci.yml/badge.svg)](https://github.com/viragtripathi/crdb-schema-exporter/actions)

# CRDB Schema Exporter

A CLI tool to export schema definitions (DDL) and data from CockroachDB into SQL, JSON, YAML, or CSV formats. Supports secure TLS connections, per-table output, schema diffing, archive packaging, and row-level data export with batching and compression.

## Features
- Export tables, views, sequences, and user-defined types
- Output formats: SQL, JSON, YAML
- Optional: per-object files
- Optional: output archive (.tar.gz)
- Optional: schema diff
- Optional: data export with SQL `INSERT INTO` or CSV format
- Row limits and GZIP compression support for data
- Secure connection with TLS certificates

## Installation
```bash
pip install crdb-schema-exporter
```

## Usage
```bash
crdb-schema-exporter --db=mydb [options]
```

### Key Options
- `--db` **(required)** – CockroachDB database name
- `--host` – CRDB host (default: localhost)
- `--certs-dir` – Path to TLS certificate directory
- `--tables` – Comma-separated list of tables (db.table1,db.table2,...)
- `--format` – Output format: sql (default), json, yaml
- `--per-table` – Output individual files per object
- `--archive` – Package output directory into a .tar.gz file
- `--diff` – Compare exported schema against another SQL file
- `--parallel` – Enable parallel exports
- `--log-dir` – Directory to store log files (default: `logs/`)

### Data Export Options
- `--data` – Enable table data export
- `--data-format` – Format: `sql` or `csv`
- `--data-split` – Save each table's data in a separate file
- `--data-limit` – Limit number of rows exported per table
- `--data-compress` – Compress CSV as `.csv.gz` (only if `--data-format=csv`)

## Example
Export schema + data as gzipped CSV, with limits:
```bash
crdb-schema-exporter \
  --db=movr \
  --data \
  --data-format=csv \
  --data-limit=1000 \
  --data-compress \
  --per-table \
  --archive \
  --verbose
```

## Output

You can also generate a diff file from schema exports using:
```bash
crdb-schema-exporter --db=movr --diff=path/to/previous_schema.sql
```
This will display the differences and optionally write to:
```
crdb_schema_dumps/movr/movr_schema.diff
```

Schema and data files are written to:
```
crdb_schema_dumps/<db_name>/
```
Example:
```
crdb_schema_dumps/movr/movr_schema.sql
crdb_schema_dumps/movr/users.csv.gz
```

## 📆 Example: Exporting CSV Data

```bash
(venv) ➔  crdb-schema-exporter git:(main) ✗ crdb-schema-exporter --db movr --data --data-format csv --data-split

2025-05-27 21:32:28,200 [INFO] Logging to file: logs/crdb_exporter.log
2025-05-27 21:32:28,367 [INFO] Exported data for movr.promo_codes to crdb_schema_dumps/movr/promo_codes.csv
2025-05-27 21:32:28,385 [INFO] Exported data for movr.rides to crdb_schema_dumps/movr/rides.csv
2025-05-27 21:32:28,397 [INFO] Exported data for movr.user_promo_codes to crdb_schema_dumps/movr/user_promo_codes.csv
2025-05-27 21:32:28,410 [INFO] Exported data for movr.users to crdb_schema_dumps/movr/users.csv
2025-05-27 21:32:28,426 [INFO] Exported data for movr.vehicle_location_histories to crdb_schema_dumps/movr/vehicle_location_histories.csv
2025-05-27 21:32:28,439 [INFO] Exported data for movr.vehicles to crdb_schema_dumps/movr/vehicles.csv
```

Contents of the output directory:

```bash
(venv) ➔  crdb-schema-exporter git:(main) ✗ cd crdb_schema_dumps/movr
(venv) ➔  movr git:(main) ✗ ls -lrt
-rw-r--r--  movr_schema.sql
-rw-r--r--  promo_codes.csv
-rw-r--r--  rides.csv
-rw-r--r--  user_promo_codes.csv
-rw-r--r--  users.csv
-rw-r--r--  vehicle_location_histories.csv
-rw-r--r--  vehicles.csv
```

> Use `--data-compress` to generate `.csv.gz` versions.
