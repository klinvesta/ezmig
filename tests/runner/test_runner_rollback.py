from pathlib import Path

import pytest

from ezmig.migration import _APPLY_TXT, _ROLLBACK_TXT
from ezmig.runner import Migration, MigrationRunner


@pytest.fixture
def migrations(tmp_path):
    # Create dummy migration files
    up_file = tmp_path / "001_create_users.sql"
    up_file.write_text(
        f"{_APPLY_TXT}\nCREATE TABLE users (id SERIAL PRIMARY KEY);\n{_ROLLBACK_TXT}\nDROP TABLE users;"
    )

    migration = Migration(filename=up_file.name, path=up_file, type="versioned")
    return [migration]


def test_rollback_one_step(mock_adapter, migrations, mocker):
    # Setup adapter.get_applied_migrations to return our dummy migration
    mock_adapter.migrations.return_value = migrations

    runner = MigrationRunner(
        adapter=mock_adapter,
        versioned_path=Path("/dummy"),
        repeatable_path=Path("/dummy"),
    )

    mocker.patch.object(
        runner,
        "_load_versioned",
        return_value=migrations,
    )

    # Call rollback with 1 step
    runner.rollback(steps=1)

    # Ensure rollback SQL is executed
    expected_sql = "DROP TABLE users;"
    mock_adapter.begin.assert_called_once()
    mock_adapter.execute.assert_called_once_with(expected_sql)
    mock_adapter.remove_migration.assert_called_once_with(migrations[0].checksum)
    mock_adapter.commit.assert_called_once()
    mock_adapter.rollback.assert_not_called()


def test_rollback_multiple_steps(mock_adapter, tmp_path):
    # Create two migrations
    m1 = Migration(filename="001.sql", path=tmp_path / "001.sql", type="versioned")
    m1.path.write_text(f"{_APPLY_TXT}\nCREATE TABLE a();\n{_ROLLBACK_TXT}\nDROP TABLE a;")

    m2 = Migration(filename="002.sql", path=tmp_path / "002.sql", type="versioned")
    m2.path.write_text(f"{_APPLY_TXT}\nCREATE TABLE b();\n{_ROLLBACK_TXT}\nDROP TABLE b;")

    mock_adapter.migrations.return_value = [m1, m2]

    runner = MigrationRunner(
        adapter=mock_adapter, versioned_path=tmp_path, repeatable_path=tmp_path
    )
    runner.rollback(steps=2)

    # Check that rollback executed in reverse order
    assert mock_adapter.execute.call_args_list[0][0][0] == "DROP TABLE b;"
    assert mock_adapter.execute.call_args_list[1][0][0] == "DROP TABLE a;"

    # Check that remove_migration_record was called in reverse order
    assert mock_adapter.remove_migration.call_args_list[0][0][0] == m2.checksum
    assert mock_adapter.remove_migration.call_args_list[1][0][0] == m1.checksum

    # Ensure transaction calls
    assert mock_adapter.begin.call_count == 2
    assert mock_adapter.commit.call_count == 2
    mock_adapter.rollback.assert_not_called()
