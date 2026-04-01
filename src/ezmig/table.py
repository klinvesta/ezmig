"""Utilities for displaying tabular data in the CLI."""

from rich.console import Console
from rich.table import Table

from .config import DatabaseTargetConfig
from .migration import Migration, MigrationState


def print_migrations_table(
    migrations: list[Migration],
    *,
    filter_state: MigrationState | None = None,
    console: Console | None = None,
) -> None:
    """Display migrations in a formatted table.

    Args:
        migrations: List of Migration objects to display
        filter_state: Optional state to filter by (e.g., only show pending)
        console: Optional Console instance for custom output
    """
    if console is None:
        console = Console()

    # Filter if requested
    items = (
        migrations if filter_state is None else [m for m in migrations if m.state == filter_state]
    )

    if not items:
        return

    table = Table(title="Migrations", show_header=True, header_style="bold cyan")
    table.add_column("Filename", style="dim")
    table.add_column("Type", style="magenta")
    table.add_column("State", style="green")
    if any(m.duration_ms is not None for m in items):
        table.add_column("Duration", justify="right", style="yellow")

    for migration in items:
        row = [
            migration.filename,
            migration.type,
            _format_state(migration.state),
        ]
        if any(m.duration_ms is not None for m in items):
            duration_str = (
                f"{migration.duration_ms}ms" if migration.duration_ms is not None else "-"
            )
            row.append(duration_str)
        table.add_row(*row)

    console.print(table)


def print_databases_table(
    databases: list[DatabaseTargetConfig],
    *,
    default_database: str | None = None,
    console: Console | None = None,
) -> None:
    """Display database targets in a formatted table.

    Args:
        databases: List of configured database targets
        console: Optional Console instance for custom output
    """
    if console is None:
        console = Console()

    if not databases:
        return

    table = Table(
        title="Database Targets",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Name", style="dim")
    table.add_column("Host", style="cyan")
    table.add_column("Categories", style="magenta")
    table.add_column("Default", justify="center")

    for db in databases:
        default_marker = "✓" if db.name == default_database else ""
        table.add_row(
            db.name,
            _extract_url_host(db.url),
            _format_categories(db.categories),
            default_marker,
        )

    console.print(table)


def _format_categories(categories: dict[str, str]) -> str:
    if not categories:
        return "-"

    return ", ".join(f"{key}={value}" for key, value in sorted(categories.items()))


def _extract_url_host(url: str) -> str:
    """Extract and redact host from a database URL."""
    try:
        if url.startswith("sqlite:"):
            return "[sqlite]"
        if "://" in url:
            _, rest = url.split("://", 1)
            if "@" in rest:
                rest = rest.split("@", 1)[1]
            if "/" in rest:
                host_port = rest.split("/", 1)[0]
            else:
                host_port = rest
            return host_port[:20]
        return url[:20]
    except Exception:
        return "[unknown]"


def _format_state(state: MigrationState) -> str:
    """Format migration state with color and styling."""
    state_colors = {
        MigrationState.APPLIED: "[green]applied[/green]",
        MigrationState.PENDING: "[yellow]pending[/yellow]",
        MigrationState.UNCHANGED: "[dim]unchanged[/dim]",
        MigrationState.CHANGED: "[yellow]changed[/yellow]",
        MigrationState.UNKNOWN: "[red]unknown[/red]",
    }
    return state_colors.get(state, state.value)
