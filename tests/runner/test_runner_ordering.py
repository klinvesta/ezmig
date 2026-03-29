"""
Tests that verify versioned migrations are executed in correct lexicographic
order regardless of the naming convention used by the team.

ezmig imposes no filename format — it sorts versioned migrations
lexicographically. Timestamps (YYYYMMDDHHmmss) are the recommended convention
because they are unique across parallel branches and sort correctly, but teams
are free to use any scheme as long as filenames sort in the intended order.
"""

from unittest.mock import MagicMock

from ezmig.adapters.base import DatabaseAdapter
from ezmig.runner import MigrationRunner


def _make_runner(tmp_path, filenames: list[tuple[str, str]], mocker=None, adapter=None):
    """
    Helper: write versioned SQL files and return a runner with a mock adapter.
    ``filenames`` is a list of (filename, sql_content) tuples written in the
    provided order — the test then checks that the runner applies them in
    lexicographic order, not creation order.
    """
    versioned = tmp_path / "versioned"
    repeatable = tmp_path / "repeatable"
    versioned.mkdir()
    repeatable.mkdir()

    for name, sql in filenames:
        (versioned / name).write_text(sql)

    if adapter is None:
        adapter = MagicMock(spec=DatabaseAdapter)
        adapter.checksums.return_value = set()

    runner = MigrationRunner(
        adapter=adapter,
        versioned_path=versioned,
        repeatable_path=repeatable,
    )
    return runner, adapter


def _applied_order(adapter) -> list[str]:
    """Return the SQL strings that were passed to adapter.execute(), in order."""
    return [call.args[0] for call in adapter.execute.call_args_list]


# ---------------------------------------------------------------------------
# Recommended convention: timestamp prefix (YYYYMMDDHHmmss)
# ---------------------------------------------------------------------------


def test_ordering_timestamp_prefix(tmp_path):
    """Timestamp-prefixed filenames sort lexicographically = chronologically."""
    files = [
        # intentionally written out of order to prove sorting is by name
        ("20260323120000_add_index.sql", "SELECT 3;"),
        ("20260101000000_init.sql", "SELECT 1;"),
        ("20260215093000_add_users.sql", "SELECT 2;"),
    ]
    runner, adapter = _make_runner(tmp_path, files)
    runner.apply()

    order = _applied_order(adapter)
    assert order == ["SELECT 1;", "SELECT 2;", "SELECT 3;"], (
        "Timestamp-prefixed migrations must be applied in chronological order"
    )


def test_ordering_timestamp_parallel_branches(tmp_path):
    """
    Simulates two developers creating migrations on separate branches at the
    same time. Timestamps ensure no collision and a deterministic merge order.
    """
    files = [
        ("20260323093000_add_payments.sql", "SELECT 'payments';"),  # developer A
        ("20260323094512_add_audit_log.sql", "SELECT 'audit';"),  # developer B
        ("20260101000000_init.sql", "SELECT 'init';"),  # baseline
    ]
    runner, adapter = _make_runner(tmp_path, files)
    runner.apply()

    order = _applied_order(adapter)
    assert order[0] == "SELECT 'init';"
    assert order[1] == "SELECT 'payments';"
    assert order[2] == "SELECT 'audit';"


# ---------------------------------------------------------------------------
# Alternative convention: zero-padded sequential numbers
# ---------------------------------------------------------------------------


def test_ordering_zero_padded_sequential(tmp_path):
    """Zero-padded numbers (001, 002, …) sort lexicographically = numerically."""
    files = [
        ("003_add_index.sql", "SELECT 3;"),
        ("001_init.sql", "SELECT 1;"),
        ("002_add_users.sql", "SELECT 2;"),
    ]
    runner, adapter = _make_runner(tmp_path, files)
    runner.apply()

    assert _applied_order(adapter) == ["SELECT 1;", "SELECT 2;", "SELECT 3;"]


def test_ordering_zero_padded_does_not_need_v_prefix(tmp_path):
    """No V prefix required — plain numeric prefix works fine."""
    files = [
        ("002_second.sql", "SELECT 2;"),
        ("001_first.sql", "SELECT 1;"),
    ]
    runner, adapter = _make_runner(tmp_path, files)
    runner.apply()

    assert _applied_order(adapter) == ["SELECT 1;", "SELECT 2;"]


# ---------------------------------------------------------------------------
# Warning: unpadded sequential numbers break lexicographic order
# ---------------------------------------------------------------------------


def test_ordering_unpadded_numbers_sort_lexicographically(tmp_path):
    """
    ⚠️  Unpadded numbers sort lexicographically, NOT numerically.
    '10_foo.sql' sorts before '2_bar.sql' because '1' < '2' as a string.
    This test documents the behaviour so teams are aware of the pitfall.
    Use zero-padding or timestamps to avoid this.
    """
    files = [
        ("10_tenth.sql", "SELECT 10;"),
        ("2_second.sql", "SELECT 2;"),
        ("1_first.sql", "SELECT 1;"),
    ]
    runner, adapter = _make_runner(tmp_path, files)
    runner.apply()

    order = _applied_order(adapter)
    # lexicographic on the full filename string: "10_" < "1_" < "2_"
    # because '0' (ASCII 48) < '_' (ASCII 95), so "10_tenth" < "1_first"
    assert order == ["SELECT 10;", "SELECT 1;", "SELECT 2;"], (
        "Unpadded numbers sort lexicographically — use zero-padding or timestamps instead"
    )


# ---------------------------------------------------------------------------
# Repeatable migrations always run after all versioned ones
# ---------------------------------------------------------------------------


def test_repeatables_run_after_versioned(tmp_path):
    versioned = tmp_path / "versioned"
    repeatable = tmp_path / "repeatable"
    versioned.mkdir()
    repeatable.mkdir()

    (versioned / "20260101000000_init.sql").write_text("SELECT 'v1';")
    (versioned / "20260102000000_second.sql").write_text("SELECT 'v2';")
    (repeatable / "my_view.sql").write_text("SELECT 'rep';")

    adapter = MagicMock(spec=DatabaseAdapter)
    adapter.checksums.return_value = set()

    runner = MigrationRunner(
        adapter=adapter,
        versioned_path=versioned,
        repeatable_path=repeatable,
    )
    runner.apply()

    order = _applied_order(adapter)
    assert order == ["SELECT 'v1';", "SELECT 'v2';", "SELECT 'rep';"], (
        "Repeatable migrations must always run after all versioned migrations"
    )
