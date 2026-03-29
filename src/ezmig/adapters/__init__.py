from .base import DatabaseAdapter
from .sqlite import SQLiteAdapter


def create_adapter(url: str) -> DatabaseAdapter:
    if url.startswith("sqlite://"):
        path = url.replace("sqlite://", "", 1)
        return SQLiteAdapter(path)

    if url.startswith("oracle://"):
        try:
            from .oracle import OracleAdapter
        except ImportError as e:
            raise ImportError(
                "oracledb is required for Oracle support. "
                "Install it with: pip install 'ezmig[oracle]'"
            ) from e
        return OracleAdapter(url)

    if url.startswith("postgres://") or url.startswith("postgresql://"):
        try:
            from .postgres import PostgresAdapter
        except ImportError as e:
            raise ImportError(
                "psycopg2 is required for PostgreSQL support. "
                "Install it with: pip install 'ezmig[postgres]'"
            ) from e
        return PostgresAdapter(url)

    raise ValueError(f"Unsupported database URL: {url}")
