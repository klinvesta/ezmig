from pathlib import Path

from typer.testing import CliRunner

from ezmig.cli import app


def test_config_list_filters_by_category():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("ezmig.toml").write_text(
            """
[database.dev]
url = "sqlite:///dev.db"
categories = { env = "dev" }

[database.prod]
url = "sqlite:///prod.db"
categories = { env = "prod" }
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["config", "list", "--category", "env=dev"])

        assert result.exit_code == 0
        assert "dev" in result.output
        assert "prod" not in result.output


def test_config_list_unknown_group_returns_error():
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("ezmig.toml").write_text(
            """
[database.dev]
url = "sqlite:///dev.db"
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["config", "list", "--group", "missing"])

        assert result.exit_code == 1
        assert "Group 'missing' not found" in result.output
