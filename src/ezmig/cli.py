from pathlib import Path

import typer

from . import __version__
from .adapters import create_adapter
from .config import DatabaseTargetConfig, EZMigConfig, get_config_files, load_config
from .logging import setup_logging
from .migration import MigrationState
from .runner import MigrationRunner
from .scaffold import create_repeatable_migration, create_versioned_migration
from .table import print_databases_table, print_migrations_table

app = typer.Typer(help="ezmig - deterministic DB migrations")
config_app = typer.Typer(help="Inspect and manage database targets")

_config_file: Path | None = None
_config_dir: Path | None = None
_include_user_config: bool = True
_include_system_config: bool = True


def _version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"ezmig {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
    config_file: Path | None = typer.Option(
        None,
        "--config",
        help="Path to a config file with highest precedence",
    ),
    config_dir: Path | None = typer.Option(
        None,
        "--config-dir",
        help="Directory containing ezmig.toml to use as project config",
    ),
    skip_user_config: bool = typer.Option(
        False,
        "--skip-user-config",
        help="Skip user-level config files",
    ),
    skip_system_config: bool = typer.Option(
        False,
        "--skip-system-config",
        help="Skip system-level config files",
    ),
):
    global _config_file
    global _config_dir
    global _include_user_config
    global _include_system_config

    _config_file = config_file
    _config_dir = config_dir
    _include_user_config = not skip_user_config
    _include_system_config = not skip_system_config

    level = "DEBUG" if verbose else "INFO"
    setup_logging(level)


def load_current_config() -> EZMigConfig:
    return load_config(
        config_file=_config_file,
        config_dir=_config_dir,
        include_user=_include_user_config,
        include_system=_include_system_config,
    )


def _parse_categories(category: list[str] | None) -> dict[str, str]:
    """Parse CLI category arguments in key=value format."""
    if not category:
        return {}

    parsed: dict[str, str] = {}
    for item in category:
        if "=" not in item:
            raise typer.BadParameter(f"Invalid category format: {item}. Use key=value")

        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or not value:
            raise typer.BadParameter(f"Invalid category format: {item}. Use key=value")

        parsed[key] = value

    return parsed


def get_runner(
    config: EZMigConfig,
    database: str | None = None,
    url: str | None = None,
    category: list[str] | None = None,
    group: str | None = None,
    migrations_path: Path | None = None,
    repeatables_path: Path | None = None,
) -> MigrationRunner:
    """Resolve a target database and return a MigrationRunner."""
    target = resolve_target(config, database=database, url=url, category=category, group=group)

    # Resolve migration paths
    migration_profile = config.migration.get(target.migration)
    if not migration_profile:
        typer.echo(
            f"Error: Migration profile '{target.migration}' not found",
            err=True,
        )
        raise typer.Exit(code=1)

    versioned = [migrations_path] if migrations_path else migration_profile.versioned_paths
    repeatable = [repeatables_path] if repeatables_path else migration_profile.repeatable_paths

    adapter = create_adapter(url=target.url)
    return MigrationRunner(
        adapter=adapter,
        versioned_path=versioned,
        repeatable_path=repeatable,
    )


def resolve_target(
    config: EZMigConfig,
    database: str | None = None,
    url: str | None = None,
    category: list[str] | None = None,
    group: str | None = None,
) -> DatabaseTargetConfig:
    """Resolve and return the selected database target.

    If url is provided, creates an inline target bypassing config lookup.
    Otherwise resolves by database name, category, or group.
    """
    # URL takes precedence - create an inline target
    if url:
        return DatabaseTargetConfig(
            name="inline",
            url=url,
            migration="default",
            categories={},
            allow_replay=False,
        )

    categories = _parse_categories(category)

    # Resolve the target database
    try:
        target = config.resolve_database(
            name=database,
            categories=categories if categories else None,
            group=group,
        )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e
    return target


@app.command()
def rollback(
    steps: int = typer.Option(1, "--steps", "-n", help="Number of migrations to rollback"),
    database: str | None = typer.Option(None, "--database", help="Target database name"),
    url: str | None = typer.Option(None, "--url", help="Database URL (overrides --database)"),
    category: list[str] | None = typer.Option(
        None, "--category", help="Filter by category (key=value)"
    ),
):
    """Rollback last N migrations"""
    config = load_current_config()
    runner = get_runner(config, database=database, url=url, category=category)
    runner.rollback(steps)


@app.command()
def status(
    show_all: bool = typer.Option(True, "--all/--pending", help="Show all or pending only"),
    database: str | None = typer.Option(None, "--database", help="Target database name"),
    url: str | None = typer.Option(None, "--url", help="Database URL (overrides --database)"),
    category: list[str] | None = typer.Option(
        None, "--category", help="Filter by category (key=value)"
    ),
):
    """Show applied and pending migrations"""
    config = load_current_config()
    runner = get_runner(config, database=database, url=url, category=category)
    migrations = runner.status()

    # Filter to pending only if --pending flag is used
    if not show_all:
        print_migrations_table(migrations, filter_state=MigrationState.PENDING)
    else:
        print_migrations_table(migrations)


@app.command()
def plan(
    versioned: Path | None = typer.Option(
        None, "--versioned", help="Override versioned migrations path"
    ),
    repeatable: Path | None = typer.Option(
        None, "--repeatable", help="Override repeatable migrations path"
    ),
    database: str | None = typer.Option(None, "--database", help="Target database name"),
    url: str | None = typer.Option(None, "--url", help="Database URL (overrides --database)"),
    category: list[str] | None = typer.Option(
        None, "--category", help="Filter by category (key=value)"
    ),
):
    """Show planned migrations without applying"""
    config = load_current_config()
    runner = get_runner(
        config,
        database=database,
        url=url,
        category=category,
        migrations_path=versioned,
        repeatables_path=repeatable,
    )

    pending = runner.plan()
    if not pending:
        typer.echo("No pending migrations")
    else:
        print_migrations_table(pending)


@app.command()
def apply(
    force: bool = typer.Option(False, "--force", help="Force apply all migrations (replay mode)"),
    allow_replay: bool = typer.Option(
        False,
        "--allow-replay",
        help="Allow replay/force apply for this command",
    ),
    database: str | None = typer.Option(None, "--database", help="Target database name"),
    url: str | None = typer.Option(None, "--url", help="Database URL (overrides --database)"),
    category: list[str] | None = typer.Option(
        None, "--category", help="Filter by category (key=value)"
    ),
    group: str | None = typer.Option(None, "--group", help="Target group"),
):
    """Apply all pending migrations"""
    config = load_current_config()
    target = resolve_target(config, database=database, url=url, category=category, group=group)
    runner = get_runner(config, database=database, url=url, category=category, group=group)

    effective_allow_replay = allow_replay or target.allow_replay
    if force and not effective_allow_replay:
        typer.echo(
            "Error: Replay is disabled for this target. Use --allow-replay or set allow_replay=true in config.",
            err=True,
        )
        raise typer.Exit(code=1)

    runner.apply(force=force, allow_replay=effective_allow_replay)


@app.command()
def replay(
    migration: list[str] | None = typer.Option(
        None,
        "--migration",
        help="Versioned migration filename or glob (repeatable)",
    ),
    repeatable: list[str] | None = typer.Option(
        None,
        "--repeatable",
        help="Repeatable migration filename or glob (repeatable)",
    ),
    all_migrations: bool = typer.Option(
        False,
        "--all",
        help="Replay all versioned and force apply all repeatables",
    ),
    allow_replay: bool = typer.Option(
        False,
        "--allow-replay",
        help="Allow replay for this command",
    ),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
    database: str | None = typer.Option(None, "--database", help="Target database name"),
    url: str | None = typer.Option(None, "--url", help="Database URL (overrides --database)"),
    category: list[str] | None = typer.Option(
        None, "--category", help="Filter by category (key=value)"
    ),
    group: str | None = typer.Option(None, "--group", help="Target group"),
):
    """Replay selected migrations or force apply all migrations."""
    if not all_migrations and not migration and not repeatable:
        typer.echo("Error: specify --migration, --repeatable, or --all", err=True)
        raise typer.Exit(code=1)

    config = load_current_config()
    target = resolve_target(config, database=database, url=url, category=category, group=group)
    effective_allow_replay = allow_replay or target.allow_replay
    if not effective_allow_replay:
        typer.echo(
            "Error: Replay is disabled for this target. Use --allow-replay or set allow_replay=true in config.",
            err=True,
        )
        raise typer.Exit(code=1)

    if not yes:
        selection_parts: list[str] = []
        if all_migrations:
            selection_parts.append("all migrations")
        if migration:
            selection_parts.append(f"versioned={','.join(migration)}")
        if repeatable:
            selection_parts.append(f"repeatable={','.join(repeatable)}")
        selection_text = "; ".join(selection_parts)
        confirmed = typer.confirm(
            f"Replay will run force apply ({selection_text}) on target '{target.name}'. Continue?"
        )
        if not confirmed:
            raise typer.Exit(code=1)

    runner = get_runner(config, database=database, url=url, category=category, group=group)
    runner.replay(
        versioned_patterns=migration,
        repeatable_patterns=repeatable,
        include_all=all_migrations,
        allow_replay=effective_allow_replay,
    )


@app.command()
def validate(
    database: str | None = typer.Option(None, "--database", help="Target database name"),
    url: str | None = typer.Option(None, "--url", help="Database URL (overrides --database)"),
    category: list[str] | None = typer.Option(
        None, "--category", help="Filter by category (key=value)"
    ),
):
    """Validate migrations"""
    config = load_current_config()
    try:
        runner = get_runner(config, database=database, url=url, category=category)
        runner.validate()
        typer.echo("Validation passed")
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("new")
def new_migration(
    name: str,
    repeatable: bool = typer.Option(
        False, "--repeatable", "-r", help="Create a repeatable migration"
    ),
):
    """Create a new migration file"""
    config = load_current_config()

    # Use the default database's migration profile
    if config.default_database and config.default_database in config.database:
        target = config.database[config.default_database]
        profile = config.migration.get(target.migration)
    else:
        profile = config.migration.get("default")

    if not profile:
        typer.echo("Error: No migration profile found", err=True)
        raise typer.Exit(code=1)

    try:
        if repeatable:
            target_path = create_repeatable_migration(profile.repeatable_paths[0], name)
        else:
            target_path = create_versioned_migration(profile.versioned_paths[0], name)
    except ValueError as exc:
        typer.echo(f"Invalid migration name: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except FileExistsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Created migration: {target_path}")


# ==================== ezmig config sub-commands ====================


@config_app.command("list")
def config_list(
    group: str | None = typer.Option(None, "--group", help="Filter by group name"),
    category: list[str] | None = typer.Option(
        None, "--category", help="Filter by category (key=value)"
    ),
):
    """List all configured database targets"""
    config = load_current_config()

    if not config.database:
        typer.echo("No database targets configured")
        return

    categories = _parse_categories(category)
    try:
        targets_to_show = config.filter_database_targets(
            group=group,
            categories=categories if categories else None,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if not targets_to_show:
        typer.echo("No database targets match the criteria")
        return

    print_databases_table(targets_to_show, default_database=config.default_database)


@config_app.command("show")
def config_show(name: str = typer.Argument(..., help="Database target name")):
    """Show full details for one database target"""
    config = load_current_config()

    if name not in config.database:
        available = ", ".join(config.database.keys())
        typer.echo(f"Error: Database '{name}' not found. Available: {available}", err=True)
        raise typer.Exit(code=1)

    target = config.database[name]
    profile = config.migration.get(target.migration)

    typer.echo(f"Name:            {target.name}")
    typer.echo(f"URL:             {target.url}")
    typer.echo(f"Migration:       {target.migration}")
    typer.echo(f"Is default:      {name == config.default_database}")

    if target.categories:
        typer.echo("Categories:")
        for key, value in target.categories.items():
            typer.echo(f"  {key}={value}")

    if profile:
        typer.echo("Versioned paths:")
        for path in profile.versioned_paths:
            typer.echo(f"  {path}")
        typer.echo("Repeatable paths:")
        for path in profile.repeatable_paths:
            typer.echo(f"  {path}")


@config_app.command("validate")
def config_validate():
    """Validate ezmig.toml and database connectivity"""
    try:
        load_current_config()
        typer.echo("✓ Config validation passed")

        # Optionally validate connectivity for all targets (comment out if expensive)
        # for name, target in config.database.items():
        #     try:
        #         adapter = create_adapter(url=target.url)
        #         adapter.connect()
        #         typer.echo(f"✓ {name}: connected")
        #         adapter.disconnect()
        #     except Exception as e:
        #         typer.echo(f"✗ {name}: {e}", err=True)
        #         raise typer.Exit(code=1)

    except ValueError as e:
        typer.echo(f"✗ Config validation failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@config_app.command("paths")
def config_paths(
    all_paths: bool = typer.Option(
        False,
        "--all",
        help="Show discovered locations even when files do not exist",
    ),
):
    """Show resolved config file locations in precedence order."""
    config_paths_list = get_config_files(
        config_file=_config_file,
        config_dir=_config_dir,
        include_user=_include_user_config,
        include_system=_include_system_config,
        existing_only=not all_paths,
    )

    if not config_paths_list:
        typer.echo("No config files found")
        return

    typer.echo("Config files (lowest -> highest precedence):")
    for idx, path in enumerate(config_paths_list, start=1):
        suffix = ""
        if all_paths and not path.exists():
            suffix = " [missing]"
        typer.echo(f"{idx}. {path}{suffix}")


# Register config sub-commands
app.add_typer(config_app, name="config")
