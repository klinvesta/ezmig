# PostgreSQL Example

This example shows how to run `ezmig` migrations against PostgreSQL.

## Prerequisites

Install PostgreSQL support:

```bash
pip install 'ezmig[postgres]'
```

Start PostgreSQL from this directory:

```bash
cd examples/postgres
docker compose up -d
docker compose exec postgres pg_isready -U postgres
```

## Configure `DATABASE_URL`

`examples/postgres/ezmig.toml` already points to `${DATABASE_URL}` for target `dev`.

Bash:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/example"
```

PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/example"
```

If `localhost` does not work in your environment (for example inside another container), use `postgres` as host:

```bash
export DATABASE_URL="postgresql://postgres:postgres@postgres:5432/example"
```

## Run migrations

```bash
ezmig config list
ezmig plan --database dev
ezmig apply --database dev
ezmig status --database dev
```

## Verify in PostgreSQL

```bash
psql postgresql://postgres:postgres@localhost:5432/example
```

Then run:

```sql
\dt
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
