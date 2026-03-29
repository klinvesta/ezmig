from tests.utils import write_versioned

from ezmig.adapters.base import DatabaseAdapter
from ezmig.checksum import compute_checksum
from ezmig.migration import Migration
from ezmig.runner import MigrationRunner


def test_replay_multiple_versioned_runs_in_lexical_order(tmp_path, mocker):
    versioned = tmp_path / "versioned"
    repeatable = tmp_path / "repeatable"
    versioned.mkdir()
    repeatable.mkdir()

    first = versioned / "20260101000000_first.sql"
    second = versioned / "20260102000000_second.sql"
    write_versioned(first, "SELECT 'up1';", "SELECT 'down1';")
    write_versioned(second, "SELECT 'up2';", "SELECT 'down2';")

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = [
        Migration(
            filename=first.name,
            path=None,
            type="versioned",
            stored_checksum=compute_checksum(first.read_bytes()),
        ),
        Migration(
            filename=second.name,
            path=None,
            type="versioned",
            stored_checksum=compute_checksum(second.read_bytes()),
        ),
    ]

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)
    runner.replay(versioned_patterns=["*.sql"], allow_replay=True)

    calls = [call.args[0] for call in adapter.execute.call_args_list]
    assert calls == ["SELECT 'down1';", "SELECT 'up1';", "SELECT 'down2';", "SELECT 'up2';"]
    assert adapter.record_migration.call_count == 2


def test_replay_repeatable_force_applies_even_if_unchanged(tmp_path, mocker):
    versioned = tmp_path / "versioned"
    repeatable = tmp_path / "repeatable"
    versioned.mkdir()
    repeatable.mkdir()

    repeatable_file = repeatable / "view.sql"
    repeatable_file.write_text("SELECT 1;", encoding="utf-8")

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = []

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)
    runner.replay(repeatable_patterns=["view.sql"], allow_replay=True)

    adapter.execute.assert_called_once_with("SELECT 1;")
    adapter.record_migration.assert_called_once()


def test_replay_requires_allow_replay_flag(tmp_path, mocker):
    versioned = tmp_path / "versioned"
    repeatable = tmp_path / "repeatable"
    versioned.mkdir()
    repeatable.mkdir()
    write_versioned(
        versioned / "20260101000000_first.sql",
        "SELECT 'up1';",
        "SELECT 'down1';",
    )

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = []
    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    try:
        runner.replay(versioned_patterns=["*.sql"])
    except RuntimeError as exc:
        assert "Replay is disabled" in str(exc)
    else:
        raise AssertionError("Expected replay to require allow_replay")


def test_replay_fails_without_rollback_for_applied_versioned(tmp_path, mocker):
    versioned = tmp_path / "versioned"
    repeatable = tmp_path / "repeatable"
    versioned.mkdir()
    repeatable.mkdir()

    migration_file = versioned / "20260101000000_first.sql"
    migration_file.write_text("-- ezmig:apply\nSELECT 'up1';\n", encoding="utf-8")

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = [
        Migration(
            filename=migration_file.name,
            path=None,
            type="versioned",
            stored_checksum=compute_checksum(migration_file.read_bytes()),
        )
    ]

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    try:
        runner.replay(versioned_patterns=[migration_file.name], allow_replay=True)
    except RuntimeError as exc:
        assert "requires -- ezmig:rollback" in str(exc)
    else:
        raise AssertionError("Expected replay to fail when rollback section is missing")
