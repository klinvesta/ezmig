# EZMig (Easy Migration)

**EZMig** is a lightweight, SQL-first database migration tool designed for simplicity and CI/CD.

It is:
- simple
- deterministic
- database-agnostic
- language-agnostic (just SQL)
- easy to integrate into pipelines

---

## ✨ Philosophy

EZMig follows a simple rule:

> **SQL is the source of truth.**

No ORM.
No schema diffing.
No magic.

Just:
- versioned SQL files
- applied in order
- tracked safely

---

## 🚀 Features

- ✅ Plain SQL migrations
- ✅ Linear, predictable execution
- ✅ Checksum validation (detect drift)
- ✅ Repeatable migrations (views, functions)
- ✅ Transaction support (when available)
- ✅ Rollback support via --ezmig:rollback
- ✅ Migration status tracking (pending, applied, changed…)
- ✅ Replay / force apply for dev iteration
- ✅ CLI-first design (CI/CD ready)
- ✅ Migration scaffolding via `ezmig new`

---

## 🗄️ Supported Databases

| Database | Driver | Install | Example |
|----------|--------|---------|---------|
| SQLite | Built-in | `uv tool install ezmig` | [`examples/sqlite`](./examples/sqlite/README.md) |
| PostgreSQL | psycopg2 | `uv tool install 'ezmig[postgres]'` | [`examples/postgres`](./examples/postgres/README.md) |
| Oracle | oracledb | `uv tool install 'ezmig[oracle]'` | [`examples/oracle`](./examples/oracle/README.md) |

Install just what you need:
- `uv tool install ezmig` — SQLite support only
- `uv tool install 'ezmig[postgres]'` — PostgreSQL support
- `uv tool install 'ezmig[oracle]'` — Oracle support
- `uv tool install 'ezmig[all]'` — All databases
- `uvx ezmig --help` — run without installing

---

## 📦 Installation

### Linux one-line install

```bash
curl -fsSL https://raw.githubusercontent.com/klinvesta/ezmig/main/scripts/install.sh | BIN_DIR=$HOME/.local/bin sh
```

### Standalone binary (no Python required)

Download a pre-built binary from the [releases page](https://github.com/klinvesta/ezmig/releases).

### uv tool install

```bash
uv tool install ezmig
uv tool install 'ezmig[postgres]'
uv tool install 'ezmig[oracle]'
uv tool install 'ezmig[all]'
```

### uvx (run without installing)

```bash
uvx ezmig --help
uvx --from 'ezmig[postgres]' ezmig status --database dev
uvx --from 'ezmig[oracle]' ezmig plan --database dev
```

### pipx

```bash
pipx install ezmig
```

### pip

```bash
pip install ezmig                  # SQLite only
pip install 'ezmig[postgres]'      # + PostgreSQL
pip install 'ezmig[oracle]'        # + Oracle
pip install 'ezmig[all]'           # everything
```

See the [Installation docs](docs/installation.md) for full platform instructions and local binary builds.

---

## 🧰 Usage

```bash
ezmig new "create users"   # create versioned migration template
ezmig new "users_v" -r     # create repeatable migration template
ezmig status --database dev    # show current state for target
ezmig plan --database dev      # show pending migrations for target
ezmig apply --database dev     # apply migrations to target
ezmig apply --force --allow-replay --database dev   # force apply all (dev)
ezmig replay --migration "202601*.sql" --allow-replay --database dev
ezmig replay --repeatable "*.sql" --allow-replay --database dev
ezmig rollback --database dev  # rollback last migration on target

# inspect configured targets
ezmig config list
ezmig config show dev
ezmig config validate
```

---

## 📁 Project structure

```
migrations/
├── versioned/
│   ├── 20260101000000_init.sql
│   └── 20260315093000_add_users.sql
└── repeatable/
    ├── my_function.sql
    └── my_view.sql
```

---

## 📝 Migration format

### Versioned migration

```sql
-- ezmig:apply
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE
);

-- ezmig:rollback
DROP TABLE users;
```

- `-- ezmig:apply` → applied during ezmig apply
- `-- ezmig:rollback` → used during rollback (ezmig rollback)
- Required for rollback support

---

### Repeatable migration

```sql
CREATE OR REPLACE VIEW active_users AS
SELECT * FROM users WHERE active = true;
```

---

## 🔢 Versioning

### Versioned migrations

ezmig imposes **no required filename format**. Versioned migrations are sorted **lexicographically by filename** and executed in that order. You choose the naming convention.

### Recommended convention: timestamps

For teams with more than one developer, the strongly recommended approach is a **timestamp prefix**:

```
20260323093000_add_payments_table.sql
20260323094512_add_audit_log.sql
```

Use `YYYYMMDDHHmmss` (14 digits). This works well because:

- Timestamps are **globally unique per developer per second** with no coordination needed.
- They sort correctly **lexicographically**, which is exactly how ezmig orders files.
- No two developers on separate branches will accidentally pick the same prefix.
- Merging branches never causes ordering conflicts — each migration keeps its natural position in time.

> **Why not sequential numbers?**
> `001`, `002`, `003` only work on a single branch. As soon as two developers independently create `003_foo.sql` and `003_bar.sql` on different branches, you have a conflict with no safe resolution. Timestamps eliminate this class of problem entirely.

### Execution order

Files are sorted **lexicographically by filename** and applied strictly in that order. With a timestamp prefix, lexicographic order equals chronological order, so the behaviour is intuitive.

> ⚠️ **Never rename or edit** a versioned migration file once it has been applied. ezmig stores the checksum of each file in `ezmig_migrations`. A rename looks like a missing file; a content change looks like drift. Both cause an error.

### Immutability

Once a versioned migration has been applied, it is **immutable**:

- Its checksum is recorded in `ezmig_migrations`.
- If the file content changes, ezmig detects the mismatch during validation and refuses to proceed.
- To modify the schema after the fact, add a *new* migration with a later timestamp.

### Repeatable migrations

Repeatable migrations have no ordering constraints. They are:

- Identified by their **filename** (used as the primary key in `ezmig_migrations`).
- Tracked by **checksum** — ezmig re-applies them whenever their content changes.
- Always applied **after** all versioned migrations in a given `ezmig apply` run.
- Sorted alphabetically among themselves.

Repeatable migrations are ideal for objects that can be safely recreated: views, functions, and stored procedures.

---

## 📊 Migration states

ezmig classifies migrations internally:

- PENDING → not yet applied
- APPLIED → already executed
- CHANGED → repeatable updated
- UNCHANGED → repeatable unchanged
- UNKNOWN → no adapter / offline mode

These states power both:

```sh
ezmig plan
ezmig status
```

---

## 🧾 Migration table

ezmig tracks applied migrations using:

```sql
CREATE TABLE ezmig_migrations (
  version      VARCHAR PRIMARY KEY,
  type         VARCHAR NOT NULL,
  checksum     VARCHAR NOT NULL,
  applied_at   TIMESTAMP NOT NULL,
  execution_ms INTEGER
);
```

---

🔄 Rollback

Rollback is explicit and safe:

```sh
ezmig rollback        # rollback last migration
ezmig rollback -n 3   # rollback last 3 migrations
```

- Executes -- ezmig:rollback blocks
- Runs in reverse order
- Wrapped in transactions (when supported)

---

## 🔁 Replay / force apply (dev)

For iterative local development, you can force re-apply migrations.

```sh
ezmig replay --migration "202601*.sql" --allow-replay --database dev
ezmig replay --repeatable "*.sql" --allow-replay --database dev
ezmig replay --all --allow-replay --database dev

# alias to replay everything in the target profile
ezmig apply --force --allow-replay --database dev
```

Safety gates:

- replay/force is disabled by default
- enable per-target with `allow_replay = true` in `ezmig.toml`, or pass `--allow-replay`

---

## 🔍 Validation

Before applying migrations, ezmig checks:

- checksum integrity
- missing migrations
- order consistency

Use it directly:

```bash
ezmig validate
```

`ezmig validate` exits with:

- `0` when validation passes
- `1` when validation fails

Validation fails include:

- applied versioned migration file missing on disk
- checksum drift on applied versioned migration
- out-of-order applied versioned migration history

Typical failure output:

```text
Validation failed:
- Applied migration missing on disk: 20260101000000_init.sql
- Checksum drift detected for migration: 20260102000000_add_age.sql
```

Repeatable migration checksum changes are reported as warnings (they are expected to be re-applied on `ezmig apply`).

---

## ⚙️ Configuration

`ezmig.toml`:

```toml
[default]
database = "dev"

[migration.default]
versioned = "./migrations/versioned"
repeatable = [
  "./migrations/repeatable",
  "./migrations/views",
  "./migrations/packages",
  "./migrations/gtt",
]

[database.dev]
url = "postgresql://user:pass@localhost:5432/db"
migration = "default"
categories = { env = "dev", location = "local" }
```

Target selection options for DB commands:

- `--database <name>`
- `--category <key=value>` (repeatable)
- `--group <name>`

See [docs/configuration.md](docs/configuration.md) for full schema and examples.

---

## 🔄 CI/CD Example

```bash
ezmig validate --database prod
ezmig plan --database prod
ezmig apply --database prod
```

Fail-fast CI pattern:

```bash
ezmig validate --database prod && ezmig apply --database prod
```

---

## 📚 Documentation

Project documentation is now organized under `docs/` using MkDocs.

- Site config: `mkdocs.yml`
- Home: `docs/index.md`
- Deployment guide: `docs/deployment.md`
- Development guide: `docs/development.md`

Build docs locally:

```bash
uv sync --group docs
uv run --group docs mkdocs serve
```

---

## 🧱 Design goals

- Keep the core small
- Avoid abstraction layers
- Favor explicit SQL over generated code
- Make failures obvious and safe

---

## ⚠️ Non-goals

ezmig intentionally does NOT:

- ❌ generate schema diffs
- ❌ manage ORM models
- ❌ support complex migration graphs

---

## Why EZMig?

Because schema evolution should be:

- incremental
- continuous
- and quietly effective

---

## 📜 License

MIT
