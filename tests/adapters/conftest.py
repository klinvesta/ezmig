import pytest


@pytest.fixture(params=["sqlite", "oracle", "postgres"])
def adapter(request, tmp_path):
    if request.param == "sqlite":
        from ezmig.adapters.sqlite import SQLiteAdapter

        return SQLiteAdapter(str(tmp_path / "test.db"))

    elif request.param == "oracle":
        import importlib.util

        if importlib.util.find_spec("oracledb") is None:
            pytest.skip("oracledb not installed")

        import oracledb

        from ezmig.adapters.oracle import OracleAdapter

        try:
            adapter = OracleAdapter("user/oracle@localhost:1521/XEPDB1")
            adapter.ensure_schema()
            return adapter
        except oracledb.DatabaseError:
            pytest.skip("Oracle not available")

    elif request.param == "postgres":
        import importlib.util

        if importlib.util.find_spec("psycopg2") is None:
            pytest.skip("psycopg2 not installed")

        from ezmig.adapters.postgres import PostgresAdapter

        url = "postgresql://postgres:postgres@localhost:5432/postgres"
        try:
            adapter = PostgresAdapter(url)
            adapter.ensure_schema()
            return adapter
        except Exception:
            pytest.skip("PostgreSQL not available")
