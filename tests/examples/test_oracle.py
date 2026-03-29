import os
import socket

import pytest


def _oracle_available() -> bool:
    try:
        import oracledb
    except ImportError:
        return False

    host = os.getenv("ORACLE_HOST", "localhost")
    port = int(os.getenv("ORACLE_PORT", "1521"))
    service_name = os.getenv("ORACLE_SERVICE", "XEPDB1")
    user = os.getenv("ORACLE_USER", "system")
    password = os.getenv("ORACLE_PASSWORD", "oracle")

    try:
        with socket.create_connection((host, port), timeout=2):
            pass
    except OSError:
        return False

    try:
        conn = oracledb.connect(user=user, password=password, dsn=f"{host}:{port}/{service_name}")
        conn.close()
        return True
    except Exception:
        return False


requires_oracle = pytest.mark.skipif(
    not _oracle_available(),
    reason="Oracle not available",
)


@requires_oracle
def test_oracle_example_apply(example_env):
    """Test that oracle adapter can apply migrations."""
    host = os.getenv("ORACLE_HOST", "localhost")
    port = int(os.getenv("ORACLE_PORT", "1521"))
    service_name = os.getenv("ORACLE_SERVICE", "XEPDB1")
    user = os.getenv("ORACLE_USER", "system")
    password = os.getenv("ORACLE_PASSWORD", "oracle")
    os.environ["DATABASE_URL"] = (
        f"oracle://{user}:{password}@{host}:{port}/?service_name={service_name}"
    )
    example_env.load("oracle")

    result = example_env.run("apply")

    assert result.exit_code == 0
