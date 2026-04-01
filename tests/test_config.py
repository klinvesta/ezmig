import os
from pathlib import Path

import pytest

from ezmig.config import (
    CONFIG_FILE_NAME,
    DEFAULT_PROFILE_NAME,
    DEFAULT_REPEATABLE_PATH,
    DEFAULT_VERSIONED_PATH,
    get_config_files,
    load_config,
)


def test_default_config_no_file(tmp_path, monkeypatch):
    """When no ezmig.toml exists, return minimal defaults."""
    monkeypatch.chdir(tmp_path)
    config = load_config()

    assert config.default_database is None
    assert DEFAULT_PROFILE_NAME in config.migration
    assert config.database == {}
    assert config.group == {}
    assert config.versioned_paths == [tmp_path / DEFAULT_VERSIONED_PATH]
    assert config.repeatable_paths == [tmp_path / DEFAULT_REPEATABLE_PATH]


def test_single_database_minimal(tmp_path, monkeypatch):
    """Parse a minimal single-database config."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / CONFIG_FILE_NAME).write_text(
        """
[default]
database = "dev"

[database.dev]
url = "sqlite:///dev.db"
""",
        encoding="utf-8",
    )

    config = load_config()

    assert config.default_database == "dev"
    assert "dev" in config.database
    assert config.database["dev"].url == "sqlite:///dev.db"
    assert config.database["dev"].migration == DEFAULT_PROFILE_NAME
    assert config.database["dev"].categories == {}
    assert config.database["dev"].allow_replay is False


def test_database_allow_replay_parsed_when_enabled(tmp_path, monkeypatch):
    """Parse allow_replay for database targets."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / CONFIG_FILE_NAME).write_text(
        """
[database.dev]
url = "sqlite:///dev.db"
allow_replay = true
""",
        encoding="utf-8",
    )

    config = load_config()
    assert config.database["dev"].allow_replay is True


def test_multiple_databases_with_categories(tmp_path, monkeypatch):
    """Parse multiple databases with categories."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[default]
database = "dev_local"

[migration.app]
versioned = "./migrations/versioned"
repeatable = "./migrations/repeatable"

[database.dev_local]
url = "postgresql://localhost/dev"
migration = "app"
categories = { env = "dev", location = "local" }

[database.prod_eu]
url = "postgresql://prod.eu/db"
migration = "app"
categories = { env = "prod", location = "eu" }
""",
        encoding="utf-8",
    )

    config = load_config()

    assert config.default_database == "dev_local"
    assert len(config.database) == 2
    assert config.database["dev_local"].categories == {"env": "dev", "location": "local"}
    assert config.database["prod_eu"].categories == {"env": "prod", "location": "eu"}


def test_multiple_migration_profiles(tmp_path, monkeypatch):
    """Parse multiple named migration profiles."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[default]
database = "dev"

[migration.app]
versioned = "./migrations/app/versioned"
repeatable = "./migrations/app/repeatable"

[migration.reporting]
versioned = "./migrations/reporting/versioned"
repeatable = ["./migrations/reporting/repeatable", "./migrations/reporting/views"]

[database.dev]
url = "sqlite:///dev.db"
migration = "app"
""",
        encoding="utf-8",
    )

    config = load_config()

    assert "app" in config.migration
    assert "reporting" in config.migration
    assert config.migration["app"].versioned_paths == [
        tmp_path / "migrations" / "app" / "versioned"
    ]
    assert len(config.migration["reporting"].repeatable_paths) == 2


def test_groups_with_members(tmp_path, monkeypatch):
    """Parse groups with explicit members list."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[default]
database = "dev"

[database.dev]
url = "sqlite:///dev.db"

[database.uat]
url = "sqlite:///uat.db"

[group.all_nonprod]
members = ["dev", "uat"]
""",
        encoding="utf-8",
    )

    config = load_config()

    assert "all_nonprod" in config.group
    assert config.group["all_nonprod"].members == ["dev", "uat"]
    assert config.group["all_nonprod"].filters is None


def test_groups_with_filters(tmp_path, monkeypatch):
    """Parse groups with category-based filters."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[default]
database = "dev"

[database.dev]
url = "sqlite:///dev.db"
categories = { env = "dev" }

[database.uat]
url = "sqlite:///uat.db"
categories = { env = "uat" }

[database.prod]
url = "sqlite:///prod.db"
categories = { env = "prod" }

[group.nonprod]
filters = { env = ["dev", "uat"] }
""",
        encoding="utf-8",
    )

    config = load_config()

    assert config.group["nonprod"].filters == {"env": ["dev", "uat"]}
    assert config.group["nonprod"].members is None


def test_env_var_expansion_database_url(tmp_path, monkeypatch):
    """Environment variables in database URLs are expanded."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEV_DB_URL", "postgresql://localhost/dev")
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "${DEV_DB_URL}"
""",
        encoding="utf-8",
    )

    config = load_config()
    assert config.database["dev"].url == "postgresql://localhost/dev"


def test_env_var_expansion_migration_paths(tmp_path, monkeypatch):
    """Environment variables in migration paths are expanded."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MIGRATIONS_ROOT", "./db")
    (tmp_path / "ezmig.toml").write_text(
        """
[migration.app]
versioned = "${MIGRATIONS_ROOT}/versioned"
repeatable = ["${MIGRATIONS_ROOT}/repeatable", "${MIGRATIONS_ROOT}/views"]
""",
        encoding="utf-8",
    )

    config = load_config()
    assert config.migration["app"].versioned_paths == [tmp_path / "db" / "versioned"]
    assert config.migration["app"].repeatable_paths == [
        tmp_path / "db" / "repeatable",
        tmp_path / "db" / "views",
    ]


def test_dotenv_loaded_automatically(tmp_path, monkeypatch):
    """When .env exists, it is loaded automatically."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUTO_DB_URL", raising=False)
    (tmp_path / ".env").write_text("AUTO_DB_URL=postgresql://localhost/dev\n", encoding="utf-8")
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "${AUTO_DB_URL}"
""",
        encoding="utf-8",
    )

    config = load_config()
    assert config.database["dev"].url == "postgresql://localhost/dev"
    os.environ.pop("AUTO_DB_URL", None)


def test_dotenv_respects_existing_env(tmp_path, monkeypatch):
    """Environment variables take precedence over .env."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OVERRIDE_URL", "postgresql://prod/db")
    (tmp_path / ".env").write_text("OVERRIDE_URL=postgresql://dev/db\n", encoding="utf-8")
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "${OVERRIDE_URL}"
""",
        encoding="utf-8",
    )

    config = load_config()
    assert config.database["dev"].url == "postgresql://prod/db"


def test_backward_compat_url_property(tmp_path, monkeypatch):
    """Backward-compat property 'url' returns default database's URL."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[default]
database = "dev"

[database.dev]
url = "sqlite:///dev.db"
""",
        encoding="utf-8",
    )

    config = load_config()
    assert config.url == "sqlite:///dev.db"


def test_backward_compat_paths(tmp_path, monkeypatch):
    """Backward-compat properties for versioned/repeatable paths."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[default]
database = "dev"

[migration.app]
versioned = "./migrations/app/versioned"
repeatable = "./migrations/app/repeatable"

[database.dev]
url = "sqlite:///dev.db"
migration = "app"
""",
        encoding="utf-8",
    )

    config = load_config()
    assert config.versioned_path == tmp_path / "migrations" / "app" / "versioned"
    assert config.repeatable_path == tmp_path / "migrations" / "app" / "repeatable"
    assert len(config.versioned_paths) == 1
    assert len(config.repeatable_paths) == 1


def test_resolve_by_name(tmp_path, monkeypatch):
    """resolve_database by explicit name."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"

[database.prod]
url = "sqlite:///prod.db"
""",
        encoding="utf-8",
    )

    config = load_config()
    dev = config.resolve_database(name="dev")
    assert dev.name == "dev"
    assert dev.url == "sqlite:///dev.db"


def test_resolve_by_categories(tmp_path, monkeypatch):
    """resolve_database by category filters."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev_uk]
url = "sqlite:///dev_uk.db"
categories = { env = "dev", location = "uk" }

[database.dev_eu]
url = "sqlite:///dev_eu.db"
categories = { env = "dev", location = "eu" }

[database.prod_eu]
url = "sqlite:///prod_eu.db"
categories = { env = "prod", location = "eu" }
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.resolve_database(categories={"env": "dev", "location": "eu"})
    assert result.name == "dev_eu"


def test_resolve_by_group_members(tmp_path, monkeypatch):
    """resolve_database from a group with explicit members."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"

[group.manual]
members = ["dev"]
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.resolve_database(group="manual")
    assert result.name == "dev"


def test_resolve_by_group_filters(tmp_path, monkeypatch):
    """resolve_database from a group with filters."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"
categories = { env = "dev" }

[group.devs]
filters = { env = ["dev"] }
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.resolve_database(group="devs")
    assert result.name == "dev"


def test_resolve_by_default(tmp_path, monkeypatch):
    """resolve_database falls back to [default].database."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[default]
database = "dev"

[database.dev]
url = "sqlite:///dev.db"
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.resolve_database()
    assert result.name == "dev"


def test_resolve_ambiguous_categories(tmp_path, monkeypatch):
    """resolve_database raises when categories match multiple targets."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev_uk]
url = "sqlite:///dev_uk.db"
categories = { env = "dev" }

[database.dev_eu]
url = "sqlite:///dev_eu.db"
categories = { env = "dev" }
""",
        encoding="utf-8",
    )

    config = load_config()
    with pytest.raises(ValueError, match="Ambiguous target selection"):
        config.resolve_database(categories={"env": "dev"})


def test_resolve_unknown_database(tmp_path, monkeypatch):
    """resolve_database raises when named database does not exist."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"
""",
        encoding="utf-8",
    )

    config = load_config()
    with pytest.raises(ValueError, match="Database 'unknown' not found"):
        config.resolve_database(name="unknown")


def test_resolve_no_match(tmp_path, monkeypatch):
    """resolve_database raises when categories match nothing."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"
categories = { env = "dev" }
""",
        encoding="utf-8",
    )

    config = load_config()
    with pytest.raises(ValueError, match="No database target found"):
        config.resolve_database(categories={"env": "prod"})


def test_filter_database_targets_by_group_members(tmp_path, monkeypatch):
    """filter_database_targets returns group members in configured order."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"

[database.uat]
url = "sqlite:///uat.db"

[database.prod]
url = "sqlite:///prod.db"

[group.nonprod]
members = ["uat", "dev"]
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.filter_database_targets(group="nonprod")

    assert [target.name for target in result] == ["uat", "dev"]


def test_filter_database_targets_by_group_filters(tmp_path, monkeypatch):
    """filter_database_targets returns targets matching group filters."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev_uk]
url = "sqlite:///dev_uk.db"
categories = { env = "dev", location = "uk" }

[database.dev_eu]
url = "sqlite:///dev_eu.db"
categories = { env = "dev", location = "eu" }

[database.prod_eu]
url = "sqlite:///prod_eu.db"
categories = { env = "prod", location = "eu" }

[group.dev_any]
filters = { env = ["dev"] }
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.filter_database_targets(group="dev_any")

    assert {target.name for target in result} == {"dev_uk", "dev_eu"}


def test_filter_database_targets_by_categories(tmp_path, monkeypatch):
    """filter_database_targets returns targets matching category key-value pairs."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev_uk]
url = "sqlite:///dev_uk.db"
categories = { env = "dev", location = "uk" }

[database.dev_eu]
url = "sqlite:///dev_eu.db"
categories = { env = "dev", location = "eu" }
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.filter_database_targets(categories={"env": "dev", "location": "eu"})

    assert [target.name for target in result] == ["dev_eu"]


def test_filter_database_targets_without_filters_returns_all(tmp_path, monkeypatch):
    """filter_database_targets returns all targets when no filters are provided."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"

[database.prod]
url = "sqlite:///prod.db"
""",
        encoding="utf-8",
    )

    config = load_config()
    result = config.filter_database_targets()

    assert {target.name for target in result} == {"dev", "prod"}


def test_filter_database_targets_unknown_group_raises(tmp_path, monkeypatch):
    """filter_database_targets raises ValueError for unknown group."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"
""",
        encoding="utf-8",
    )

    config = load_config()
    with pytest.raises(ValueError, match="Group 'missing' not found"):
        config.filter_database_targets(group="missing")


def test_validation_missing_url(tmp_path, monkeypatch):
    """Validation fails if database has no URL."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
migration = "app"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required 'url' field"):
        load_config()


def test_validation_unknown_migration_profile(tmp_path, monkeypatch):
    """Validation fails if database references non-existent migration profile."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"
migration = "unknown_profile"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="references unknown migration profile"):
        load_config()


def test_validation_unknown_group_member(tmp_path, monkeypatch):
    """Validation fails if group references non-existent database."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"

[group.invalid]
members = ["unknown"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="references unknown database member"):
        load_config()


def test_validation_group_no_selector(tmp_path, monkeypatch):
    """Validation fails if group has neither members nor filters."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[group.empty]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must define exactly one of"):
        load_config()


def test_validation_group_both_selectors(tmp_path, monkeypatch):
    """Validation fails if group has both members and filters."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ezmig.toml").write_text(
        """
[database.dev]
url = "sqlite:///dev.db"

[group.bad]
members = ["dev"]
filters = { env = ["dev"] }
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must define exactly one of"):
        load_config()


def test_load_config_merges_user_and_project_with_precedence(tmp_path, monkeypatch):
    """Project config overrides user config while inheriting non-overlapping sections."""
    project_dir = tmp_path / "project"
    home_dir = tmp_path / "home"

    project_dir.mkdir(parents=True)
    (home_dir / ".ezmig").mkdir(parents=True)

    (home_dir / ".ezmig" / "config.toml").write_text(
        """
[default]
database = "user_db"

[migration.shared]
versioned = "./user/versioned"
repeatable = "./user/repeatable"

[database.user_db]
url = "sqlite:///user.db"
migration = "shared"
categories = { env = "user" }
""",
        encoding="utf-8",
    )

    (project_dir / CONFIG_FILE_NAME).write_text(
        """
[default]
database = "project_db"

[database.project_db]
url = "sqlite:///project.db"
migration = "shared"
categories = { env = "project" }
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    config = load_config(include_system=False)

    assert config.default_database == "project_db"
    assert set(config.database.keys()) == {"user_db", "project_db"}
    assert config.database["project_db"].url == "sqlite:///project.db"
    assert config.database["user_db"].categories == {"env": "user"}
    assert config.migration["shared"].versioned_paths == [
        home_dir / ".ezmig" / "user" / "versioned"
    ]


def test_load_config_explicit_config_file_has_highest_precedence(tmp_path, monkeypatch):
    """Explicit config_file overrides project and user defaults."""
    project_dir = tmp_path / "project"
    home_dir = tmp_path / "home"
    override_file = tmp_path / "override.toml"

    project_dir.mkdir(parents=True)
    (home_dir / ".ezmig").mkdir(parents=True)

    (home_dir / ".ezmig" / "config.toml").write_text(
        """
[default]
database = "user_db"

[database.user_db]
url = "sqlite:///user.db"
""",
        encoding="utf-8",
    )

    (project_dir / CONFIG_FILE_NAME).write_text(
        """
[default]
database = "project_db"

[database.project_db]
url = "sqlite:///project.db"
""",
        encoding="utf-8",
    )

    override_file.write_text(
        """
[default]
database = "override_db"

[database.override_db]
url = "sqlite:///override.db"
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    config = load_config(config_file=override_file, include_system=False)

    assert config.default_database == "override_db"
    assert set(config.database.keys()) == {"user_db", "project_db", "override_db"}


def test_get_config_files_includes_expected_order(tmp_path, monkeypatch):
    """get_config_files returns load order from lower to higher precedence."""
    project_dir = tmp_path / "project"
    home_dir = tmp_path / "home"

    project_dir.mkdir(parents=True)
    (home_dir / ".ezmig").mkdir(parents=True)

    user_config = home_dir / ".ezmig" / "config.toml"
    project_config = project_dir / CONFIG_FILE_NAME

    user_config.write_text("[database.dev]\nurl='sqlite:///user.db'\n", encoding="utf-8")
    project_config.write_text("[database.dev]\nurl='sqlite:///project.db'\n", encoding="utf-8")

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    paths = get_config_files(include_system=False)

    assert paths == [user_config.resolve(), project_config.resolve()]
