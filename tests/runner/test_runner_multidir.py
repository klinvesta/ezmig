from ezmig.adapters.base import DatabaseAdapter
from ezmig.runner import MigrationRunner


def test_status_loads_from_multiple_directories(tmp_path, mocker):
    versioned_a = tmp_path / "versioned_a"
    versioned_b = tmp_path / "versioned_b"
    repeatable_a = tmp_path / "repeatable_a"
    repeatable_b = tmp_path / "repeatable_b"

    for directory in (versioned_a, versioned_b, repeatable_a, repeatable_b):
        directory.mkdir()

    (versioned_a / "20260101000000_init.sql").write_text("SELECT 1;")
    (versioned_b / "20260102000000_add_table.sql").write_text("SELECT 2;")
    (repeatable_a / "users_v.sql").write_text("SELECT 3;")
    (repeatable_b / "packages_v.sql").write_text("SELECT 4;")

    adapter = mocker.MagicMock(spec=DatabaseAdapter)
    adapter.checksums.return_value = set()

    runner = MigrationRunner(
        adapter=adapter,
        versioned_path=[versioned_a, versioned_b],
        repeatable_path=[repeatable_a, repeatable_b],
    )

    statuses = runner.status()
    names = [migration.filename for migration in statuses]

    assert names == [
        "20260101000000_init.sql",
        "20260102000000_add_table.sql",
        "packages_v.sql",
        "users_v.sql",
    ]
