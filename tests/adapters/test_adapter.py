from ezmig.migration import Migration


def test_ensure_schema(adapter):
    adapter.ensure_schema()


def test_record_and_list_migrations(adapter, tmp_path):
    adapter.ensure_schema()

    migration_file = tmp_path / "V001__test.sql"
    migration_file.write_text("SELECT 1;")

    m = Migration(
        filename="V001__test.sql",
        path=migration_file,
        type="versioned",
    )

    adapter.record_migration(m)

    migrations = adapter.migrations()

    assert len(migrations) == 1
    assert migrations[0].filename == "V001__test.sql"


def test_checksums(adapter, tmp_path):
    adapter.ensure_schema()

    f = tmp_path / "V001__test.sql"
    f.write_text("SELECT 1;")

    m = Migration(
        filename="V001__test.sql",
        path=f,
        type="versioned",
    )

    adapter.record_migration(m)

    checksums = adapter.checksums()

    assert m.checksum in checksums


def test_remove_migration(adapter, tmp_path):
    adapter.ensure_schema()

    f = tmp_path / "V001__test.sql"
    f.write_text("SELECT 1;")

    m = Migration(
        filename="V001__test.sql",
        path=f,
        type="versioned",
    )

    adapter.record_migration(m)
    adapter.remove_migration(m.checksum)

    assert adapter.migrations() == []
