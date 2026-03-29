# Development

## Environment

```bash
uv sync --group dev
```

## Run tests

```bash
uv run pytest
```

## Lint/format (if configured locally)

```bash
uv run ruff check .
uv run ruff format .
```

## Pre-commit

Install hooks:

```bash
uv run pre-commit install
```

Run on all files:

```bash
uv run pre-commit run --all-files
```

## Serve docs locally

```bash
uv sync --group docs
uv run --group docs mkdocs serve
```

## Build docs

```bash
uv run --group docs mkdocs build --strict
```
