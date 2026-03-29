# CLI Reference

All commands accept global flags:

| Flag | Description |
|------|-------------|
| `--verbose` / `-v` | Enable debug logging |
| `--config PATH` | Load an explicit config file with highest precedence |
| `--config-dir PATH` | Use `PATH/ezmig.toml` as the project-level config |
| `--skip-user-config` | Skip user-level config locations |
| `--skip-system-config` | Skip system-level config locations |

---

## `ezmig apply`

Apply all pending migrations.

```bash
ezmig apply
ezmig apply --force --allow-replay --database dev
```

Runs all pending versioned migrations (in lexicographic order), followed by
all changed repeatable migrations.

| Option | Description |
|--------|-------------|
| `--force` | Force apply all versioned + repeatable migrations (replay mode) |
| `--allow-replay` | Allow force/replay execution for this command |
| `--database NAME` | Target database name |
| `--category key=value` | Target selector by category |
| `--group NAME` | Target selector by group |

`--force` requires replay to be enabled via `--allow-replay` or target config `allow_replay = true`.

---

## `ezmig replay`

Replay selected migrations or force apply all migrations for a target.

```bash
ezmig replay --migration "202601*.sql" --allow-replay --database dev
ezmig replay --repeatable "*.sql" --allow-replay --database dev
ezmig replay --all --allow-replay --database dev
```

| Option | Description |
|--------|-------------|
| `--migration GLOB` | Select versioned migration filename/glob (repeatable) |
| `--repeatable GLOB` | Select repeatable migration filename/glob (repeatable) |
| `--all` | Replay all versioned and force all repeatables |
| `--allow-replay` | Allow replay execution for this command |
| `--yes` | Skip confirmation prompt |
| `--database NAME` | Target database name |
| `--category key=value` | Target selector by category |
| `--group NAME` | Target selector by group |

---

## `ezmig plan`

Show what would be applied without actually running anything.

```bash
ezmig plan
ezmig plan --versioned ./migrations/versioned
ezmig plan --repeatable ./migrations/repeatable
```

| Option | Description |
|--------|-------------|
| `--versioned PATH` | Override versioned migrations directory |
| `--repeatable PATH` | Override repeatable migrations directory |

---

## `ezmig status`

Show the state of all known migrations.

```bash
ezmig status
```

Prints each migration with its type and current state (`PENDING`, `APPLIED`, `CHANGED`, `UNCHANGED`).

---

## `ezmig validate`

Validate the migration history against disk.

```bash
ezmig validate
```

Exits with:

- `0` — validation passed
- `1` — validation failed

Fails on:

- Applied versioned migration file missing on disk
- Checksum drift on an applied versioned migration
- Out-of-order applied versioned migration history

---

## `ezmig rollback`

Roll back the last N applied migrations.

```bash
ezmig rollback
ezmig rollback -n 3
```

| Option | Description |
|--------|-------------|
| `-n INT` | Number of migrations to roll back (default: `1`) |

Executes `-- ezmig:rollback` blocks in reverse order, wrapped in a transaction where supported.

---

## `ezmig new`

Scaffold a new migration file.

```bash
ezmig new "create users"       # versioned
ezmig new "users_v" --repeatable   # repeatable
ezmig new "users_v" -r             # short form
```

| Option | Description |
|--------|-------------|
| `--repeatable` / `-r` | Create a repeatable migration instead of versioned |

The file is created in the configured `versioned` or `repeatable` directory.
Versioned files get a `YYYYMMDDHHmmss_` timestamp prefix automatically.

---

## `ezmig config paths`

Show discovered configuration files in load order.

```bash
ezmig config paths
ezmig config paths --all
```

| Option | Description |
|--------|-------------|
| `--all` | Include discovered locations even when files are missing |
