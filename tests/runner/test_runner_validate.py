import pytest

from ezmig.adapters.base import DatabaseAdapter
from ezmig.checksum import compute_checksum
from ezmig.migration import Migration
from ezmig.runner import MigrationRunner


def _db_migration_from_file(path):
    return Migration(
        filename=path.name,
        path=None,
        type="versioned",
        stored_checksum=compute_checksum(path.read_bytes()),
    )


def test_validate_passes_when_applied_prefix_matches_disk(tmp_migrations, mocker):
    versioned, repeatable = tmp_migrations
    first = versioned / "20260101000000_init.sql"

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = [_db_migration_from_file(first)]

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    runner.validate()

    adapter.ensure_schema.assert_called_once()


def test_validate_fails_on_checksum_drift(tmp_migrations, mocker):
    versioned, repeatable = tmp_migrations
    first = versioned / "20260101000000_init.sql"

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = [
        Migration(
            filename=first.name,
            path=None,
            type="versioned",
            stored_checksum="deadbeef",
        )
    ]

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    with pytest.raises(RuntimeError, match="Checksum drift detected"):
        runner.validate()


def test_validate_fails_when_applied_file_missing_on_disk(tmp_migrations, mocker):
    versioned, repeatable = tmp_migrations

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = [
        Migration(
            filename="20250101000000_missing.sql",
            path=None,
            type="versioned",
            stored_checksum="abc123",
        )
    ]

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    with pytest.raises(RuntimeError, match="missing on disk"):
        runner.validate()


def test_validate_fails_on_out_of_order_applied_versioned(tmp_migrations, mocker):
    versioned, repeatable = tmp_migrations
    second = versioned / "20260102000000_add_table.sql"

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.migrations.return_value = [_db_migration_from_file(second)]

    runner = MigrationRunner(adapter=adapter, versioned_path=versioned, repeatable_path=repeatable)

    with pytest.raises(RuntimeError, match="Out-of-order applied migration"):
        runner.validate()
