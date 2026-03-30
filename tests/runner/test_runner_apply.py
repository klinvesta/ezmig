import pytest

from ezmig.adapters.base import DatabaseAdapter, SQLExecutionError
from ezmig.runner import MigrationRunner


def test_apply_with_mock(tmp_migrations, mocker):
    versioned, repeatable = tmp_migrations

    # create runner with a fake adapter
    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    # apply migrations
    runner.apply()

    # assert schema migration check was called
    runner.adapter.ensure_schema.assert_called_once()

    # assert execute_script called for each migration
    assert runner.adapter.execute.call_count == 3
    calls = [call.args[0] for call in runner.adapter.execute.call_args_list]
    assert "SELECT 1;" in calls[0]
    assert "SELECT 2;" in calls[1]
    assert "SELECT 3;" in calls[2]

    # assert begin/commit were called for each migration
    assert runner.adapter.begin.call_count == 3
    assert runner.adapter.commit.call_count == 3


def test_apply_logs_failed_statement_context(tmp_migrations, mocker, caplog):
    versioned, repeatable = tmp_migrations

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.execute.side_effect = SQLExecutionError(
        message="Oracle statement execution failed",
        statement="SELECT FROM dual",
        statement_index=1,
        total_statements=1,
        original_error=RuntimeError("ORA-00900: invalid SQL statement"),
    )

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    caplog.set_level("ERROR", logger="ezmig.runner")

    with pytest.raises(SQLExecutionError):
        runner.apply()

    assert "statement 1/1" in caplog.text
    assert "SELECT FROM dual" in caplog.text
    assert "Failed to apply 20260101000000_init.sql" in caplog.text
    adapter.rollback.assert_called_once()
