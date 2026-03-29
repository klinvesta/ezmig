# Contributing

Contributions are welcome — bug reports, feature requests, and pull requests alike.

---

## Reporting a bug

Open an issue on GitHub and include:

- ezmig version (`uv run ezmig --version`)
- Database type and driver version
- The `ezmig.toml` used (redact credentials)
- The full error output

---

## Suggesting a feature

Open an issue with:

- The problem you're trying to solve
- What you'd expect the behaviour to be
- Any alternatives you considered

---

## Opening a pull request

### 1) Fork and clone

```bash
git clone https://github.com/klinvesta/ezmig.git
cd ezmig
```

### 2) Set up the dev environment

```bash
uv sync --group dev
uv run pre-commit install
```

### 3) Create a branch

Use a short, descriptive name:

```bash
git checkout -b fix/checksum-drift-message
git checkout -b feat/mysql-adapter
git checkout -b docs/add-configuration-page
```

Prefixes: `fix/`, `feat/`, `docs/`, `chore/`, `test/`

### 4) Make your changes

- Keep commits small and focused
- Add or update tests for any changed behaviour
- Use Conventional Commits so releases can be generated automatically
- Run the full suite before pushing:

```bash
uv run pytest
uv run pre-commit run --all-files
```

Commit message examples:

- `feat: add dry-run flag to plan`
- `fix: handle missing rollback section`
- `perf: reduce filesystem scans during status`
- `feat!: change configuration schema`

Release impact:

- `feat` → minor release
- `fix` / `perf` → patch release
- breaking changes (`!` or `BREAKING CHANGE:`) → major release
- `docs`, `chore`, `style`, `refactor`, `test`, `build`, `ci` → no release

### 5) Open a PR

- Target the `dev` branch
- Describe **what** changed and **why**
- Link to any related issues

---

## Code style

- Formatting and linting are enforced via [ruff](https://docs.astral.sh/ruff/)
- Type checking is enforced via [ty](https://github.com/astral-sh/ty)
- All hooks run automatically on commit via pre-commit

---

## Design principles

Before proposing a change, keep in mind EZMig's goals:

- Keep the core small
- Avoid abstraction layers
- Favour explicit SQL over generated code
- Make failures obvious and safe
