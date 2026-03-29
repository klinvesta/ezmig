from unittest.mock import MagicMock

import pytest

from ezmig.adapters.base import DatabaseAdapter


@pytest.fixture
def mock_adapter():
    adapter = MagicMock(spec=DatabaseAdapter)
    return adapter


@pytest.fixture
def tmp_migrations(tmp_path):
    versioned = tmp_path / "versioned"
    repeatable = tmp_path / "repeatable"
    versioned.mkdir()
    repeatable.mkdir()

    (versioned / "20260101000000_init.sql").write_text("SELECT 1;")
    (versioned / "20260102000000_add_table.sql").write_text("SELECT 2;")
    (repeatable / "view.sql").write_text("SELECT 3;")

    return versioned, repeatable
