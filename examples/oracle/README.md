# Oracle Example

This example shows how to run `ezmig` migrations against Oracle.

## Prerequisites

Install Oracle support:

```bash
pip install 'ezmig[oracle]'
```

Start Oracle from this directory:

```bash
cd examples/oracle
docker compose up -d
```

Wait for the container healthcheck to pass.

## Configure `DATABASE_URL`

`examples/oracle/ezmig.toml` already points to `${DATABASE_URL}` for target `dev`.

Bash:

```bash
export DATABASE_URL="oracle://system:oracle@localhost:1521/?service_name=XEPDB1"
```

PowerShell:

```powershell
$env:DATABASE_URL = "oracle://system:oracle@localhost:1521/?service_name=XEPDB1"
```

## Run migrations

```bash
ezmig config list
ezmig plan --database dev
ezmig apply --database dev
ezmig status --database dev
```

## Verify in Oracle

```bash
docker exec -it oracle sqlplus system/oracle@XEPDB1
```

Then run:

```sql
SELECT table_name FROM user_tables WHERE table_name IN ('USERS', 'EZMIG_MIGRATIONS');
SELECT version, type, applied_at FROM ezmig_migrations ORDER BY applied_at;
SELECT * FROM users;
SELECT * FROM users_v;
```

## Roll back last migration

```bash
ezmig rollback --database dev
```

## What this example includes

- Versioned migrations:
  - `20260101000000_init.sql`
  - `20260102000000_add_age.sql`
- Repeatable migration:
  - `user_v.sql`
