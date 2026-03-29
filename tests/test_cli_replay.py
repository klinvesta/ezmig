import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from ezmig.cli import app
from tests.utils import write_versioned


def test_replay_repeatable_force_reinstalls_unchanged_script():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("migrations/versioned").mkdir(parents=True, exist_ok=True)
        Path("migrations/repeatable").mkdir(parents=True, exist_ok=True)

        Path("ezmig.toml").write_text(
            """
[default]
database = "dev"

[database.dev]
url = "sqlite://ezmig.db"
allow_replay = true
""",
            encoding="utf-8",
        )

        write_versioned(
            Path("migrations/versioned/20260101000000_init.sql"),
            "CREATE TABLE IF NOT EXISTS replay_counter (value TEXT);",
            "SELECT 1;",
        )
        Path("migrations/repeatable/counter.sql").write_text(
            "INSERT INTO replay_counter(value) VALUES ('x');",
            encoding="utf-8",
        )

        apply_result = runner.invoke(app, ["apply"])
        assert apply_result.exit_code == 0

        replay_result = runner.invoke(app, ["replay", "--repeatable", "counter.sql", "--yes"])
        assert replay_result.exit_code == 0

        conn = sqlite3.connect("ezmig.db")
        try:
            count = conn.execute("SELECT COUNT(*) FROM replay_counter").fetchone()[0]
        finally:
            conn.close()

        assert count == 2


def test_apply_force_uses_force_engine_for_repeatables():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("migrations/versioned").mkdir(parents=True, exist_ok=True)
        Path("migrations/repeatable").mkdir(parents=True, exist_ok=True)

        Path("ezmig.toml").write_text(
            """
[default]
database = "dev"

[database.dev]
url = "sqlite://ezmig.db"
allow_replay = true
""",
            encoding="utf-8",
        )

        write_versioned(
            Path("migrations/versioned/20260101000000_init.sql"),
            "CREATE TABLE IF NOT EXISTS replay_counter (value TEXT);",
            "SELECT 1;",
        )
        Path("migrations/repeatable/counter.sql").write_text(
            "INSERT INTO replay_counter(value) VALUES ('x');",
            encoding="utf-8",
        )

        first_apply = runner.invoke(app, ["apply"])
        assert first_apply.exit_code == 0

        force_apply = runner.invoke(app, ["apply", "--force"])
        assert force_apply.exit_code == 0

        conn = sqlite3.connect("ezmig.db")
        try:
            count = conn.execute("SELECT COUNT(*) FROM replay_counter").fetchone()[0]
        finally:
            conn.close()

        assert count == 2


def test_replay_fails_when_replay_not_enabled():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("migrations/versioned").mkdir(parents=True, exist_ok=True)
        write_versioned(
            Path("migrations/versioned/20260101000000_init.sql"),
            "SELECT 1;",
            "SELECT 1;",
        )
        Path("ezmig.toml").write_text(
            """
[default]
database = "dev"

[database.dev]
url = "sqlite://ezmig.db"
""",
            encoding="utf-8",
        )

        result = runner.invoke(
            app,
            ["replay", "--migration", "20260101000000_init.sql", "--yes"],
        )
        assert result.exit_code == 1
        assert "Replay is disabled" in result.output
