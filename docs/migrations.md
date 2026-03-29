# Migrations

## File structure

```
migrations/
├── versioned/
│   ├── 20260101000000_init.sql
│   └── 20260315093000_add_users.sql
└── repeatable/
    ├── users_v.sql
    └── audit_fn.sql
```

---

## Versioned migrations

Versioned migrations are applied once and tracked by checksum.

### Format

```sql
-- ezmig:apply
CREATE TABLE users (
  id   SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE
);

-- ezmig:rollback
DROP TABLE users;
```

- `-- ezmig:apply` marks the section applied by `ezmig apply`
- `-- ezmig:rollback` marks the section run by `ezmig rollback`
- The two sections can appear in **any order** — EZMig detects boundaries by marker position, not file order
- The rollback block is **required** if you want rollback support

### Naming convention

EZMig sorts versioned migrations **lexicographically by filename**. The strongly recommended prefix is a 14-digit timestamp:

```
YYYYMMDDHHmmss_description.sql
```

Example:

```
20260323093000_add_payments_table.sql
20260323094512_add_audit_log.sql
```

**Why timestamps over sequential numbers?**

Sequential numbers (`001`, `002`) break when two developers independently create
`003_foo.sql` and `003_bar.sql` on separate branches. Timestamps are globally
unique per second per developer with no coordination needed.

### Immutability

Once applied, a versioned migration is **immutable**:

- Its checksum is recorded in `ezmig_migrations`
- Editing the file causes a checksum drift error on the next `ezmig validate`
- To fix something, add a new migration with a later timestamp

---

## Repeatable migrations

Repeatable migrations are re-applied whenever their content changes.

### Format

```sql
CREATE OR REPLACE VIEW active_users AS
SELECT * FROM users WHERE active = true;
```

No `-- ezmig:apply` marker is needed. The entire file is executed.

### Behaviour

- Identified by **filename** (used as primary key in `ezmig_migrations`)
- Tracked by **checksum** — re-applied when content changes
- Always applied **after** all versioned migrations in a given run
- Sorted alphabetically within themselves

Repeatable migrations are ideal for objects that can be safely recreated: views,
functions, stored procedures, and packages.

---

## Replay / force apply (dev)

For iterative development, you can force re-run migrations:

```bash
ezmig replay --migration "202601*.sql" --allow-replay --database dev
ezmig replay --repeatable "*.sql" --allow-replay --database dev
ezmig replay --all --allow-replay --database dev

# equivalent shortcut for replaying everything
ezmig apply --force --allow-replay --database dev
```

Behaviour:

- Applied versioned migrations: execute `-- ezmig:rollback`, then `-- ezmig:apply`
- Pending versioned migrations: apply normally
- Selected repeatables: execute even when checksum is unchanged

Replay/force is disabled by default; enable with `--allow-replay` or `allow_replay = true` on the target config.

---

## Migration states

| State | Meaning |
|-------|---------|
| `PENDING` | Not yet applied |
| `APPLIED` | Applied and unchanged |
| `CHANGED` | Repeatable with a new checksum (will be re-applied) |
| `UNCHANGED` | Repeatable with the same checksum (skipped) |
| `UNKNOWN` | No adapter / offline mode |

---

## Tracking table

EZMig records all applied migrations in:

```sql
CREATE TABLE ezmig_migrations (
  version      VARCHAR PRIMARY KEY,
  type         VARCHAR NOT NULL,
  checksum     VARCHAR NOT NULL,
  applied_at   TIMESTAMP NOT NULL,
  execution_ms INTEGER
);
```
