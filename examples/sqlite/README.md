# SQLite Example

This example shows how to run `ezmig` migrations using SQLite.

## Notes

`examples/sqlite/ezmig.toml` is already configured with:

```toml
[database.dev]
url = "sqlite://example.sqlite"
```

No environment variables are required.

## Run migrations

```bash
cd examples/sqlite
ezmig config list
ezmig plan --database dev
ezmig apply --database dev
ezmig status --database dev
```

## Verify in SQLite

```bash
sqlite3 example.sqlite
```

Then run:

```sql
.tables
SELECT version, type, applied_at FROM ezmig_migrations ORDER BY applied_at;
SELECT * FROM users;
SELECT * FROM users_v;
```

## Roll back last migration

```bash
ezmig rollback --database dev
```

## Reset

Delete `example.sqlite` and run `ezmig apply --database dev` again.

## What this example includes

- Versioned migrations:
  - `20260101000000_init.sql`
  - `20260102000000_add_age.sql`
- Repeatable migration:
  - `user_v.sql`
