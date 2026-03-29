# Configuration

EZMig supports layered configuration from system, user, project, and explicit override files.

## Minimal example

```toml
[default]
database = "dev"

[database.dev]
url = "sqlite:///./app.sqlite"
```

## Full example

```toml
[default]
database = "dev_local"

[migration.app]
versioned = "./migrations/versioned"
repeatable = [
  "./migrations/repeatable",
  "./migrations/views",
  "./migrations/functions",
]

[database.dev_local]
url = "postgresql://localhost:5432/mydb"
migration = "app"
allow_replay = true
categories = { env = "dev", location = "local" }

[database.prod_eu]
url = "postgresql://prod.eu:5432/mydb"
migration = "app"
categories = { env = "prod", location = "eu" }

[group.nonprod]
filters = { env = ["dev"] }
```

## Reference

### `[default]`

| Key | Required | Description |
|-----|----------|-------------|
| `database` | ❌ | Default target for commands when no `--database` option is provided |

### `[migration.<name>]`

Define reusable sets of migration paths. Used to support different repositories or projects.

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `versioned` | ❌ | `./migrations/versioned` | Path to versioned migration files |
| `repeatable` | ❌ | `./migrations/repeatable` | Path or list of paths to repeatable migrations |

`repeatable` accepts either a single string path or a list of paths. This is useful for separating views, functions, packages, or GTTs into distinct directories.

### `[database.<name>]`

Define named database targets. Each target specifies a URL and which migration profile to use.

| Key | Required | Description |
|-----|----------|-------------|
| `url` | ✅ | Database connection URL |
| `migration` | ❌ | Migration profile name; defaults to `default` |
| `allow_replay` | ❌ | Enable replay/force commands for this target (default `false`) |
| `categories` | ❌ | Flat map of strings to classify this target (e.g., `env = "dev"`) |

### `[group.<name>]`

Define named groups of databases for batch operations or discovery. Groups can be specified by explicit members or by filtering on categories.

| Key | Required | Description |
|-----|----------|-------------|
| `members` | ❌ | Explicit list of database names to include in this group |
| `filters` | ❌ | Category-based selector; matches when **all** keys match |

Exactly one of `members` or `filters` must be provided.

## Defaults

If no `ezmig.toml` exists, EZMig falls back to:

```
[default]
database = (none)

[migration.default]
versioned = "./migrations/versioned"
repeatable = "./migrations/repeatable"
```

EZMig searches for `ezmig.toml` in the **current working directory** at runtime.

## Configuration locations and precedence

EZMig merges config files from **lowest to highest precedence**:

1. System config
  - Windows: `C:\ProgramData\ezmig\ezmig.toml`
  - Linux/macOS: `/etc/ezmig/ezmig.toml`
  - Linux/macOS (alt): `/usr/local/etc/ezmig/ezmig.toml`
2. User config
  - `~/.ezmig/config.toml`
  - `~/.config/ezmig/ezmig.toml`
3. Project config
  - `./ezmig.toml` (current working directory)
4. `EZMIG_CONFIG` env var (if set)
5. CLI override
  - `ezmig --config <path>`

Merge behavior:

- Sections are merged by name (`migration.*`, `database.*`, `group.*`).
- If the same named entry appears in multiple files, the higher-precedence file replaces that entry.
- `[default].database` is taken from the highest-precedence file that defines it.
- Relative migration paths are resolved relative to the config file where they are defined.

Use CLI controls to alter discovery:

- `--config PATH` (highest-precedence override file)
- `--config-dir PATH` (use `PATH/ezmig.toml` as project config)
- `--skip-user-config`
- `--skip-system-config`

To inspect discovery order:

```bash
ezmig config paths
ezmig config paths --all
```

## Environment variable support

`ezmig` expands environment variables in string values in `ezmig.toml`.

Supported forms include `$VAR`, `${VAR}`, and (on Windows) `%VAR%`.

### Auto-loading `.env`

`ezmig` automatically loads a `.env` file from the current directory at startup — no plugin or extra step required. This is designed for local development workflows.

```ini
# .env  — never commit this file
DEV_DB_URL=postgresql://localhost/dev
```

```toml
# ezmig.toml  — safe to commit
[database.dev]
url = "${DEV_DB_URL}"
```

Rules:
- Variables already present in the environment are **never overridden** by `.env` (real env wins).
- `.env` is silently skipped when it does not exist.
- Add `.env` to `.gitignore` to keep credentials out of version control.

### Expand only the sensitive parts

The most readable approach — host, port, and database name stay visible in the file while only the password comes from the environment:

```toml
[database.dev]
url = "postgresql://myuser:${DB_PASSWORD}@localhost:5432/mydb"
```

```bash
export DB_PASSWORD="s3cr3t"
ezmig apply --database dev
```

### Expand the full URL

Useful when the entire URL is managed by your platform (e.g., Heroku `DATABASE_URL`, Render, Railway):

```toml
[database.prod]
url = "${DATABASE_URL}"
```

```bash
export DATABASE_URL="postgresql://myuser:s3cr3t@prod.example.com/db"
ezmig apply --database prod
```

### Configuration discovery

List all configured targets:

```bash
ezmig config list
ezmig config list --group nonprod
ezmig config list --category env=prod
```

Show details for one target:

```bash
ezmig config show prod_eu
```

Validate the configuration:

```bash
ezmig config validate
```

Show discovered config files (load order):

```bash
ezmig config paths
```
