import pytest

from ezmig.migration import _APPLY_TXT, _ROLLBACK_TXT, Migration, _parse_sections


@pytest.fixture
def tmp_versioned(tmp_path):
    path = tmp_path / "V001_init.sql"
    path.write_text(
        f"""{_APPLY_TXT}
CREATE TABLE users (
    id SERIAL PRIMARY KEY
);

{_ROLLBACK_TXT}
DROP TABLE users;
"""
    )
    return path


@pytest.fixture
def tmp_versioned_reversed(tmp_path):
    """Like tmp_versioned but with rollback section placed before apply."""
    path = tmp_path / "V001_reversed.sql"
    path.write_text(
        f"""{_ROLLBACK_TXT}
DROP TABLE users;

{_APPLY_TXT}
CREATE TABLE users (
    id SERIAL PRIMARY KEY
);
"""
    )
    return path


@pytest.fixture
def tmp_repeatable(tmp_path):
    path = tmp_path / "repeatable_view.sql"
    path.write_text(
        """CREATE OR REPLACE VIEW active_users AS
SELECT * FROM users WHERE active = true;"""
    )
    return path


def test_apply_sql_versioned(tmp_versioned):
    migration = Migration(
        filename=tmp_versioned.name,
        path=tmp_versioned,
        type="versioned",
    )
    expected = """CREATE TABLE users (
    id SERIAL PRIMARY KEY
);"""
    assert migration.apply_sql == expected


def test_apply_sql_repeatable(tmp_repeatable):
    migration = Migration(
        filename=tmp_repeatable.name,
        path=tmp_repeatable,
        type="repeatable",
    )
    expected = """CREATE OR REPLACE VIEW active_users AS
SELECT * FROM users WHERE active = true;"""
    assert migration.apply_sql == expected


def test_apply_sql_versioned_reversed(tmp_versioned_reversed):
    """apply_sql must return the CREATE block even when rollback comes first."""
    migration = Migration(
        filename=tmp_versioned_reversed.name,
        path=tmp_versioned_reversed,
        type="versioned",
    )
    expected = """CREATE TABLE users (
    id SERIAL PRIMARY KEY
);"""
    assert migration.apply_sql == expected


def test_down_sql_versioned_reversed(tmp_versioned_reversed):
    """down_sql must return the DROP statement even when rollback comes first."""
    migration = Migration(
        filename=tmp_versioned_reversed.name,
        path=tmp_versioned_reversed,
        type="versioned",
    )
    assert migration.down_sql == "DROP TABLE users;"


def test_down_sql_versioned(tmp_versioned):
    migration = Migration(
        filename=tmp_versioned.name,
        path=tmp_versioned,
        type="versioned",
    )
    assert migration.down_sql == "DROP TABLE users;"


def test_parse_sections_ordered(tmp_versioned):
    text = tmp_versioned.read_text()
    sections = _parse_sections(text)
    assert _APPLY_TXT in sections
    assert _ROLLBACK_TXT in sections
    assert "CREATE TABLE" in sections[_APPLY_TXT]
    assert "DROP TABLE" in sections[_ROLLBACK_TXT]


def test_parse_sections_reversed(tmp_versioned_reversed):
    text = tmp_versioned_reversed.read_text()
    sections = _parse_sections(text)
    assert "DROP TABLE" in sections[_ROLLBACK_TXT]
    assert "CREATE TABLE" in sections[_APPLY_TXT]


def test_parse_sections_missing_rollback(tmp_path):
    path = tmp_path / "no_rollback.sql"
    path.write_text(f"{_APPLY_TXT}\nCREATE TABLE foo (id INT);\n")
    sections = _parse_sections(path.read_text())
    assert _APPLY_TXT in sections
    assert _ROLLBACK_TXT not in sections


def test_migration_hash(tmp_path):
    file = tmp_path / "test.sql"
    file.write_text("SELECT 1;")

    m1 = Migration(filename=file.name, path=file, type="versioned")
    m2 = Migration(filename=file.name, path=file, type="versioned")

    assert m1.checksum == m2.checksum
