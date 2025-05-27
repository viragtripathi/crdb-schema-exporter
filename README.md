[![PyPI version](https://img.shields.io/pypi/v/crdb-schema-exporter)](https://pypi.org/project/crdb-schema-exporter/)
[![Python versions](https://img.shields.io/pypi/pyversions/crdb-schema-exporter)](https://pypi.org/project/crdb-schema-exporter/)
[![License](https://img.shields.io/pypi/l/crdb-schema-exporter)](https://pypi.org/project/crdb-schema-exporter/)
[![Build status](https://github.com/viragtripathi/crdb-schema-exporter/actions/workflows/test.yml/badge.svg)](https://github.com/viragtripathi/crdb-schema-exporter/actions)

# CRDB Schema Exporter

A CLI tool to export schema definitions (DDL) from CockroachDB into SQL, JSON, or YAML formats. Supports secure TLS connections, per-table output, schema diffing, and archive packaging.

## Features
- Export tables, views, sequences, and user-defined types
- Output formats: SQL, JSON, YAML
- Optional: per-object files
- Optional: output archive (.tar.gz)
- Optional: schema diff
- Secure connection with TLS certificates

## Installation

Install from source:
```bash
pip install .
```

Build and install from source distribution:
```bash
python -m build
pip install dist/crdb_schema_exporter-0.1.0-py3-none-any.whl
```

Install from PyPI:
```bash
pip install crdb-schema-exporter
```

> ⚠️ **Note:** You must install the CockroachDB dialect:
```bash
pip install sqlalchemy-cockroachdb
```

## Usage
```bash
crdb-schema-exporter --db=mydb --host=localhost [options]
```

### Options
- `--db` **(required)** – CockroachDB database name
- `--host` – CRDB host (default: localhost)
- `--certs-dir` – Path to TLS certificate directory
- `--tables` – Comma-separated list of tables (db.table1,db.table2,...)
- `--per-table` – Output individual files per object
- `--format` – Output format: sql (default), json, yaml
- `--archive` – Package output directory into a .tar.gz file
- `--diff` – Compare exported schema against another SQL file
- `--parallel` – Enable parallel exports
- `--verbose` – Enable detailed debug logging
- `--log-dir` – Directory to store log files (default: `logs/`)

## Output
By default, exported schema files are saved under:
```
crdb_schema_dumps/<db_name>/
```
For example:
```
crdb_schema_dumps/movr/movr_schema.sql
```

## Example
```bash
crdb-schema-exporter --db=movr --per-table --format=yaml --archive --verbose
```

