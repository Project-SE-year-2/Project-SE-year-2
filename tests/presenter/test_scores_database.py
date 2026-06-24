"""
Tests for ScoresDatabase.

Covers:
  - WAL journal mode is active after __init__
  - scores table exists with the correct columns
  - all five ranking indexes are created
  - insert() stores a single row
  - insert_batch() stores multiple rows in one transaction
  - clear_period() removes only the targeted period's rows
  - rows from different periods are isolated from each other
  - context-manager protocol (with statement) closes cleanly
"""

import multiprocessing
import pytest
from pathlib import Path

from src.presenter.scores_database import ScoresDatabase, ScheduleMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metrics(
    min_days: float = 3.0,
    avg_days: float = 4.0,
    conflicts: int = 0,
    span: int = 14,
    daily_cap: int = 2,
) -> ScheduleMetrics:
    """Return a ScheduleMetrics instance with sensible defaults."""
    return ScheduleMetrics(
        min_days_required=min_days,
        avg_days_all=avg_days,
        elective_conflicts=conflicts,
        span_required=span,
        max_exams_per_day=daily_cap,
    )


def _row_count(db: ScoresDatabase, period_id: str) -> int:
    """Helper: count rows for a given period directly via the internal connection."""
    row = db._conn.execute(
        "SELECT COUNT(*) FROM scores WHERE period_id = ?", (period_id,)
    ).fetchone()
    return row[0]


@pytest.fixture
def db(tmp_path: Path) -> ScoresDatabase:
    """Provide a fresh database stored in a temporary directory for each test."""
    return ScoresDatabase(tmp_path / "scores.db")


# ---------------------------------------------------------------------------
# WAL configuration
# ---------------------------------------------------------------------------

def test_wal_mode_is_enabled(db: ScoresDatabase) -> None:
    """
    The journal mode must be WAL so that Engine writes and UI reads
    can proceed concurrently without blocking each other.
    """
    row = db._conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0].upper() == "WAL"


# ---------------------------------------------------------------------------
# Table schema
# ---------------------------------------------------------------------------

def test_scores_table_exists(db: ScoresDatabase) -> None:
    """The scores table must be created during __init__."""
    tables = {
        r[0]
        for r in db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "scores" in tables


def test_scores_table_has_required_columns(db: ScoresDatabase) -> None:
    """
    The scores table must contain all columns needed by the ranking queries
    and by ResultsReader (batch_number, index_in_batch).
    """
    columns = {
        row[1]
        for row in db._conn.execute("PRAGMA table_info(scores)").fetchall()
    }
    required = {
        "id",
        "period_id",
        "batch_number",
        "index_in_batch",
        "min_days_required",
        "avg_days_all",
        "elective_conflicts",
        "span_required",
        "max_exams_per_day",
    }
    assert required.issubset(columns)


# ---------------------------------------------------------------------------
# Ranking indexes
# ---------------------------------------------------------------------------

def test_all_five_ranking_indexes_exist(db: ScoresDatabase) -> None:
    """
    One composite index must exist for each of the five metric columns.
    Missing indexes would force full-table scans on every page fetch.
    """
    indexes = {
        r[0]
        for r in db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    expected = {
        "idx_scores_min_days",
        "idx_scores_avg_days",
        "idx_scores_span",
        "idx_scores_conflicts",
        "idx_scores_daily_cap",
    }
    assert expected.issubset(indexes)


# ---------------------------------------------------------------------------
# insert
# ---------------------------------------------------------------------------

def test_insert_stores_one_row(db: ScoresDatabase) -> None:
    """A single insert() call must add exactly one row to the scores table."""
    db.insert("fall_a", batch_number=0, index_in_batch=0, metrics=_metrics())
    assert _row_count(db, "fall_a") == 1


def test_insert_persists_correct_values(db: ScoresDatabase) -> None:
    """All five metric values must be stored and retrieved exactly."""
    m = _metrics(min_days=7.5, avg_days=3.2, conflicts=2, span=21, daily_cap=4)
    db.insert("fall_a", batch_number=1, index_in_batch=3, metrics=m)

    row = db._conn.execute(
        "SELECT batch_number, index_in_batch, "
        "min_days_required, avg_days_all, elective_conflicts, "
        "span_required, max_exams_per_day "
        "FROM scores WHERE period_id = 'fall_a'"
    ).fetchone()

    assert row[0] == 1        # batch_number
    assert row[1] == 3        # index_in_batch
    assert row[2] == 7.5      # min_days_required
    assert row[3] == 3.2      # avg_days_all
    assert row[4] == 2        # elective_conflicts
    assert row[5] == 21       # span_required
    assert row[6] == 4        # max_exams_per_day


def test_insert_normalizes_infinite_min_days_to_zero(db: ScoresDatabase) -> None:
    """Undefined mandatory gaps must not enter scores.db as infinity."""
    db.insert("fall_a", batch_number=0, index_in_batch=0, metrics=_metrics(min_days=float("inf")))

    row = db._conn.execute(
        "SELECT min_days_required FROM scores WHERE period_id = 'fall_a'"
    ).fetchone()

    assert row[0] == 0.0


# ---------------------------------------------------------------------------
# insert_batch
# ---------------------------------------------------------------------------

def test_insert_batch_stores_all_rows(db: ScoresDatabase) -> None:
    """insert_batch() must store every element of the provided list."""
    rows = [(0, i, _metrics(min_days=float(i))) for i in range(10)]
    db.insert_batch("spring_b", rows)
    assert _row_count(db, "spring_b") == 10


def test_insert_batch_empty_list_is_safe(db: ScoresDatabase) -> None:
    """Calling insert_batch() with an empty list must not raise an error."""
    db.insert_batch("fall_a", [])
    assert _row_count(db, "fall_a") == 0


# ---------------------------------------------------------------------------
# Isolation between periods
# ---------------------------------------------------------------------------

def test_rows_are_isolated_per_period(db: ScoresDatabase) -> None:
    """
    Rows inserted for one period must not be visible when querying another.
    """
    db.insert("fall_a",   0, 0, _metrics())
    db.insert("spring_b", 0, 0, _metrics())
    db.insert("spring_b", 0, 1, _metrics())

    assert _row_count(db, "fall_a")   == 1
    assert _row_count(db, "spring_b") == 2


# ---------------------------------------------------------------------------
# clear_period
# ---------------------------------------------------------------------------

def test_clear_period_removes_all_rows_for_that_period(db: ScoresDatabase) -> None:
    """clear_period() must delete every row belonging to the given period_id."""
    db.insert_batch("fall_a", [(0, i, _metrics()) for i in range(5)])
    db.clear_period("fall_a")
    assert _row_count(db, "fall_a") == 0


def test_clear_period_does_not_affect_other_periods(db: ScoresDatabase) -> None:
    """Clearing one period must leave rows for other periods untouched."""
    db.insert("fall_a",   0, 0, _metrics())
    db.insert("spring_b", 0, 0, _metrics())

    db.clear_period("fall_a")

    assert _row_count(db, "fall_a")   == 0
    assert _row_count(db, "spring_b") == 1


def test_clear_period_on_nonexistent_period_is_safe(db: ScoresDatabase) -> None:
    """clear_period() on an unknown period_id must not raise an error."""
    db.clear_period("does_not_exist")  # should be a no-op


# ---------------------------------------------------------------------------
# Queue integration (cross-process notifications)
# ---------------------------------------------------------------------------

def test_insert_puts_batch_written_event_on_queue(tmp_path: Path) -> None:
    """insert() must post a batch_written event so EngineListener wakes up."""
    q: multiprocessing.Queue = multiprocessing.Queue()
    db = ScoresDatabase(tmp_path / "scores.db", queue=q)

    db.insert("fall_a", batch_number=0, index_in_batch=0, metrics=_metrics())

    # multiprocessing.Queue serialises items through a background pipe thread,
    # so get_nowait() may race.  Use a generous timeout instead.
    event = q.get(timeout=2)
    assert event["event"] == "batch_written"
    assert event["period_id"] == "fall_a"


def test_insert_batch_puts_single_event_on_queue(tmp_path: Path) -> None:
    """insert_batch() must post exactly one event regardless of batch size."""
    q: multiprocessing.Queue = multiprocessing.Queue()
    db = ScoresDatabase(tmp_path / "scores.db", queue=q)

    rows = [(0, i, _metrics()) for i in range(5)]
    db.insert_batch("spring_b", rows)

    # Exactly one notification for the whole batch
    event = q.get(timeout=2)
    assert event["event"] == "batch_written"
    # No second event should arrive
    assert q.empty()


def test_mark_done_puts_engine_done_event_on_queue(tmp_path: Path) -> None:
    """mark_done() must post an engine_done event so EngineListener can stop."""
    q: multiprocessing.Queue = multiprocessing.Queue()
    db = ScoresDatabase(tmp_path / "scores.db", queue=q)

    db.mark_done()

    event = q.get(timeout=2)
    assert event["event"] == "engine_done"


def test_no_queue_insert_does_not_raise(db: ScoresDatabase) -> None:
    """When no queue is supplied, insert() must work silently without errors."""
    db.insert("fall_a", 0, 0, _metrics())  # queue=None by default in fixture


def test_no_queue_mark_done_does_not_raise(db: ScoresDatabase) -> None:
    """When no queue is supplied, mark_done() must be a silent no-op."""
    db.mark_done()  # queue=None by default in fixture


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

def test_context_manager_closes_connection(tmp_path: Path) -> None:
    """
    Using ScoresDatabase as a context manager must close the connection
    without raising an error.
    """
    with ScoresDatabase(tmp_path / "ctx.db") as db:
        db.insert("fall_a", 0, 0, _metrics())

    # After __exit__, further use of the closed connection should raise
    with pytest.raises(Exception):
        db._conn.execute("SELECT 1")
