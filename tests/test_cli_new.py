import re
from pathlib import Path

from typer.testing import CliRunner

from ezmig.cli import app


def test_new_creates_versioned_file_in_default_path():
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["new", "add users table"])

        assert result.exit_code == 0
        created = Path("migrations/versioned")
        files = list(created.glob("*.sql"))
        assert len(files) == 1
        assert re.match(r"^\d{14}_add_users_table\.sql$", files[0].name)

        content = files[0].read_text(encoding="utf-8")
        assert "-- ezmig:apply" in content
        assert "-- ezmig:rollback" in content


def test_new_repeatable_uses_configured_path():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("ezmig.toml").write_text(
            """
[default]
database = "dev"

[migration.app]
versioned = "./db/versioned"
repeatable = "./db/repeatable"

[database.dev]
url = "sqlite:///ezmig.db"
migration = "app"
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["new", "user view", "--repeatable"])

        assert result.exit_code == 0
        target = Path("db/repeatable/user_view.sql")
        assert target.exists()


def test_new_repeatable_fails_when_file_exists():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("migrations/repeatable").mkdir(parents=True, exist_ok=True)
        Path("migrations/repeatable/user_view.sql").write_text("SELECT 1;", encoding="utf-8")

        result = runner.invoke(app, ["new", "user view", "--repeatable"])

        assert result.exit_code == 1
        assert "Migration already exists" in result.output


def test_new_repeatable_uses_first_path_when_repeatable_is_list():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("ezmig.toml").write_text(
            """
[default]
database = "dev"

[migration.app]
versioned = "./db/versioned"
repeatable = ["./db/views", "./db/packages"]

[database.dev]
url = "sqlite:///ezmig.db"
migration = "app"
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["new", "user view", "--repeatable"])

        assert result.exit_code == 0
        assert Path("db/views/user_view.sql").exists()
        assert not Path("db/packages/user_view.sql").exists()


def test_new_honors_global_config_override_file():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("custom.toml").write_text(
            """
[default]
database = "dev"

[migration.custom]
versioned = "./custom/versioned"
repeatable = "./custom/repeatable"

[database.dev]
url = "sqlite:///ezmig.db"
migration = "custom"
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["--config", "custom.toml", "new", "create users"])

        assert result.exit_code == 0
        files = list(Path("custom/versioned").glob("*.sql"))
        assert len(files) == 1
