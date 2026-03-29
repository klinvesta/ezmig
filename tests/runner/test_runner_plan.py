from ezmig.adapters.base import DatabaseAdapter
from ezmig.runner import MigrationRunner


def test_plan_logs_pending(tmp_migrations, mocker, caplog):
    versioned, repeatable = tmp_migrations
    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.checksums.return_value = set()

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    caplog.set_level("INFO")
    plan = runner.plan()
    names = [m.path.name for m in plan]

    assert "20260101000000_init.sql" in names
    assert "view.sql" in names
