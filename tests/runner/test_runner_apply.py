from ezmig.adapters.base import DatabaseAdapter
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
