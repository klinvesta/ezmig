from unittest.mock import call

from ezmig.adapters.base import DatabaseAdapter
from ezmig.runner import MigrationRunner


def test_status_ensures_schema_before_checksums(tmp_migrations, mocker):
    versioned, repeatable = tmp_migrations
    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.checksums.return_value = set()

    runner = MigrationRunner(
        adapter=adapter,
        versioned_path=versioned,
        repeatable_path=repeatable,
    )

    runner.status()

    adapter.ensure_schema.assert_called_once()
    adapter.checksums.assert_called_once()
    assert adapter.mock_calls.index(call.ensure_schema()) < adapter.mock_calls.index(
        call.checksums()
    )
