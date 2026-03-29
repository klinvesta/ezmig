# Installation

## Linux quick install (curl | sh)

```bash
curl -fsSL https://raw.githubusercontent.com/klinvesta/ezmig/main/scripts/install.sh | BIN_DIR=$HOME/.local/bin sh
```

Optional installer variables:

- `BIN_DIR` (default: `$HOME/.local/bin`) — target directory for the binary
- `VERSION` (default: `latest`) — release tag, e.g. `v0.1.0`

## Option 1 — Standalone binary (no Python required)

Pre-built binaries are attached to every [GitHub release](https://github.com/klinvesta/ezmig/releases).

| Platform | File |
|----------|------|
| Linux (amd64) | `ezmig-linux-amd64` |
| macOS (Apple Silicon) | `ezmig-macos-aarch64` |
| Windows (amd64) | `ezmig-windows-amd64.exe` |

### Linux / macOS

```bash
curl -fsSL https://github.com/klinvesta/ezmig/releases/latest/download/ezmig-linux-amd64 -o ezmig
chmod +x ezmig
sudo mv ezmig /usr/local/bin/
```

### Windows

Download `ezmig-windows-amd64.exe` from the releases page, rename it to `ezmig.exe`,
and place it somewhere on your `PATH`.

---

## Option 2 — pipx (Python required)

```bash
pipx install ezmig
```

---

## Option 3 — uv tool install (Python required)

```bash
uv tool install ezmig
uv tool install 'ezmig[postgres]'
uv tool install 'ezmig[oracle]'
uv tool install 'ezmig[all]'
```

---

## Option 4 — uvx (run without installing)

```bash
uvx ezmig --help
uvx --from 'ezmig[postgres]' ezmig status --database dev
uvx --from 'ezmig[oracle]' ezmig plan --database dev
```

Use `uvx` when you want one-off or CI execution without managing a persistent tool install.

---

## Option 5 — pip

```bash
pip install ezmig                  # SQLite only
pip install 'ezmig[postgres]'      # + PostgreSQL
pip install 'ezmig[oracle]'        # + Oracle
pip install 'ezmig[all]'           # everything
```

---

## Uninstall

### If installed with Linux quick install (`curl | sh`)

```bash
rm -f "${BIN_DIR:-$HOME/.local/bin}/ezmig"
```

### If installed as a standalone binary

```bash
sudo rm -f /usr/local/bin/ezmig
```

### If installed with pipx

```bash
pipx uninstall ezmig
```

### If installed with uv tool

```bash
uv tool uninstall ezmig
```

### If installed with pip

```bash
pip uninstall ezmig
```

---

## Build the binary locally

```bash
uv sync --group dev
uv run pyinstaller --onefile --name ezmig src/ezmig/__main__.py
# output: dist/ezmig  (or dist/ezmig.exe on Windows)
```
