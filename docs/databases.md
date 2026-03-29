# Databases

## SQLite

Built-in — no extra driver required.

### Install

```bash
uv tool install ezmig
# or one-off runs:
uvx ezmig --help

# pip alternative
pip install ezmig
```

### Connection URL

```toml
[database]
url = "sqlite:///path/to/db.sqlite"   # absolute
url = "sqlite://./relative/db.sqlite" # relative to cwd
url = "sqlite://:memory:"             # in-memory
```

---

## PostgreSQL

### Install

```bash
uv tool install 'ezmig[postgres]'
# or one-off runs:
uvx --from 'ezmig[postgres]' ezmig status --database dev

# pip alternative
pip install 'ezmig[postgres]'
```

### Connection URL

```toml
[database]
url = "postgresql://myuser:${DB_PASSWORD}@localhost:5432/mydb"
```

Or use the full URL from an environment variable (e.g. set by your platform):

```toml
[database]
url = "${DATABASE_URL}"
```

### Notes

- Transactions are fully supported; `ezmig apply` and `ezmig rollback` wrap each migration
- The `ezmig_migrations` tracking table is created automatically on first use

---

## Oracle

### Install

```bash
uv tool install 'ezmig[oracle]'
# or one-off runs:
uvx --from 'ezmig[oracle]' ezmig status --database dev

# pip alternative
pip install 'ezmig[oracle]'
```

### Connection URL

```toml
[database]
url = "oracle://myuser:${DB_PASSWORD}@localhost:1521/?service_name=XEPDB1"
```

Or use the full URL from an environment variable:

```toml
[database]
url = "${DATABASE_URL}"
```

### Notes

- Uses [`oracledb`](https://python-oracledb.readthedocs.io/) in thin mode (no Oracle Client libraries required)
- DDL statements auto-commit in Oracle; transactions wrap DML in rollback blocks
- Multiple repeatable directories are common for Oracle projects to separate views, packages, and GTTs:

```toml
[migrations]
repeatable = [
  "./migrations/repeatable",
  "./migrations/views",
  "./migrations/packages",
  "./migrations/gtt",
]
```

---

## All databases

### Install everything

```bash
uv tool install 'ezmig[all]'

# pip alternative
pip install 'ezmig[all]'
```
