from datetime import datetime

import pytest

from ezmig.scaffold import create_repeatable_migration, create_versioned_migration, slugify


def test_slugify_normalizes_name():
    assert slugify("Add users table") == "add_users_table"


def test_slugify_raises_for_invalid_name():
    with pytest.raises(ValueError):
        slugify("---")


def test_create_versioned_migration_uses_timestamp_and_template(tmp_path):
    target = create_versioned_migration(
        path=tmp_path,
        name="add users table",
        now=datetime(2026, 3, 24, 11, 22, 33),
    )

    assert target.name == "20260324112233_add_users_table.sql"
    content = target.read_text(encoding="utf-8")
    assert "-- ezmig:apply" in content
    assert "-- ezmig:rollback" in content


def test_create_repeatable_migration_raises_on_collision(tmp_path):
    create_repeatable_migration(path=tmp_path, name="user view")

    with pytest.raises(FileExistsError):
        create_repeatable_migration(path=tmp_path, name="user view")
