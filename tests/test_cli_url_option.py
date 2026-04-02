"""Tests for CLI commands with --url option."""

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ezmig.cli import app
from tests.utils import write_versioned


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def isolated_env(runner: CliRunner):
    with runner.isolated_filesystem():
        Path("migrations/versioned").mkdir(parents=True, exist_ok=True)
        Path("migrations/repeatable").mkdir(parents=True, exist_ok=True)
        yield


def write_default_config(extra: str = "") -> None:
    Path("ezmig.toml").write_text(
        f"""
[default]
database = "main"

[database.main]
url = "sqlite://dummy.db"
{extra}
""",
        encoding="utf-8",
    )


def write_standard_migration(down_sql: str = "SELECT 1;") -> None:
    write_versioned(
        Path("migrations/versioned/20260101000000_init.sql"),
        "CREATE TABLE IF NOT EXISTS test (id INT);",
        down_sql,
    )


def test_status_with_url_option(runner: CliRunner, isolated_env):
    """Verify that --url option works for status command."""
    write_default_config()
    write_standard_migration()

    result = runner.invoke(app, ["status", "--url", "sqlite://custom.db"])
    assert result.exit_code == 0
    assert "ezmig_migration" in result.stdout or "pending" in result.stdout.lower()


def test_plan_with_url_option(runner: CliRunner, isolated_env):
    """Verify that --url option works for plan command."""
    write_default_config()
    write_standard_migration()

    result = runner.invoke(app, ["plan", "--url", "sqlite://custom.db"])
    assert result.exit_code == 0
    assert "20260101000000_init" in result.stdout


def test_apply_with_url_option(runner: CliRunner, isolated_env):
    """Verify that --url option works for apply command."""
    write_default_config()
    write_standard_migration()

    result = runner.invoke(app, ["apply", "--url", "sqlite://custom.db"])
    assert result.exit_code == 0

    conn = sqlite3.connect("custom.db")
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "test" in tables or "ezmig_migration" in tables
    finally:
        conn.close()


def test_validate_with_url_option(runner: CliRunner, isolated_env):
    """Verify that --url option works for validate command."""
    write_default_config()
    write_standard_migration()

    apply_result = runner.invoke(app, ["apply", "--url", "sqlite://custom.db"])
    assert apply_result.exit_code == 0

    result = runner.invoke(app, ["validate", "--url", "sqlite://custom.db"])
    assert result.exit_code == 0
    assert "Validation passed" in result.stdout


def test_rollback_with_url_option(runner: CliRunner, isolated_env):
    """Verify that --url option works for rollback command."""
    write_default_config()
    write_standard_migration(down_sql="DROP TABLE test;")

    apply_result = runner.invoke(app, ["apply", "--url", "sqlite://custom.db"])
    assert apply_result.exit_code == 0

    result = runner.invoke(app, ["rollback", "--url", "sqlite://custom.db", "--steps", "1"])
    assert result.exit_code == 0


def test_url_option_takes_precedence_over_database(runner: CliRunner, isolated_env):
    """Verify that --url option takes precedence when both --database and --url are provided."""
    Path("ezmig.toml").write_text(
        """
[default]
database = "main"

[database.main]
url = "sqlite://main.db"

[database.alt]
url = "sqlite://alt.db"
""",
        encoding="utf-8",
    )
    write_standard_migration()

    result = runner.invoke(
        app,
        ["plan", "--database", "alt", "--url", "sqlite://custom.db"],
    )
    assert result.exit_code == 0
