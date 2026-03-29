import os

import pytest


def _postgres_available() -> bool:
    try:
        import psycopg2
    except ImportError:
        return False

    # In docker compose, use service name; otherwise localhost
    host = os.getenv("POSTGRES_HOST", "localhost")

    try:
        conn = psycopg2.connect(
            f"postgresql://postgres:postgres@{host}:5432/example",
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_available(),
    reason="PostgreSQL not available",
)


@requires_postgres
def test_postgres_example_apply(example_env):
    """Test that postgres adapter can apply migrations."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    os.environ["DATABASE_URL"] = f"postgresql://postgres:postgres@{host}:5432/example"
    example_env.load("postgres")

    result = example_env.run("apply")

    assert result.exit_code == 0
