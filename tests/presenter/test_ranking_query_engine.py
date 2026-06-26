"""Tests for RankingQueryEngine — fetch_window returns list[tuple]."""

import pytest
from pathlib import Path
from src.presenter.scores_database import ScoresDatabase, ScheduleMetrics
from src.presenter.ranking_query_engine import RankingQueryEngine

IDX_BATCH_NUMBER    = 0
IDX_INDEX_IN_BATCH  = 1
IDX_MIN_DAYS        = 2
IDX_AVG_DAYS        = 3
IDX_CONFLICTS       = 4
IDX_SPAN            = 5
IDX_DAILY_CAP       = 6
IDX_ROOM_DIST       = 7


def _m(min_days=3.0, avg_days=4.0, conflicts=0, span=14, daily_cap=2, avg_room_distance=0.0):
    return ScheduleMetrics(min_days_required=min_days, avg_days_all=avg_days,
                           elective_conflicts=conflicts, span_required=span,
                           max_exams_per_day=daily_cap, avg_room_distance=avg_room_distance)


@pytest.fixture
def db_path(tmp_path): return tmp_path / "scores.db"

@pytest.fixture
def db(db_path): return ScoresDatabase(db_path)

@pytest.fixture
def engine(db_path, db): return RankingQueryEngine(db_path)


def test_fetch_window_returns_list_of_tuples(db, engine):
    db.insert("fall_a", 0, 0, _m())
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    assert isinstance(rows, list)
    assert type(rows[0]).__name__ in ("tuple", "Row")

def test_fetch_window_tuple_has_eight_elements(db, engine):
    db.insert("fall_a", 0, 0, _m())
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    assert len(rows[0]) == 8

def test_fetch_window_desc_for_higher_is_better_column(db, engine):
    db.insert("fall_a", 0, 0, _m(min_days=1.0))
    db.insert("fall_a", 0, 1, _m(min_days=9.0))
    db.insert("fall_a", 0, 2, _m(min_days=5.0))
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    vals = [r[IDX_MIN_DAYS] for r in rows]
    assert vals == sorted(vals, reverse=True)

def test_fetch_window_asc_for_lower_is_better_column(db, engine):
    db.insert("fall_a", 0, 0, _m(conflicts=5))
    db.insert("fall_a", 0, 1, _m(conflicts=0))
    db.insert("fall_a", 0, 2, _m(conflicts=3))
    rows = engine.fetch_window("fall_a", ["elective_conflicts"], limit=10, offset=0)
    vals = [r[IDX_CONFLICTS] for r in rows]
    assert vals == sorted(vals)

def test_fetch_window_multi_column_sort(db, engine):
    db.insert("fall_a", 0, 0, _m(min_days=5.0, avg_days=2.0))
    db.insert("fall_a", 0, 1, _m(min_days=5.0, avg_days=8.0))
    db.insert("fall_a", 0, 2, _m(min_days=9.0, avg_days=1.0))
    rows = engine.fetch_window("fall_a", ["min_days_required", "avg_days_all"], limit=10, offset=0)
    assert rows[0][IDX_MIN_DAYS] == 9.0
    assert rows[1][IDX_AVG_DAYS] == 8.0
    assert rows[2][IDX_AVG_DAYS] == 2.0

def test_fetch_window_example_from_task_description(db, engine):
    db.insert("fall_a", 0, 0, _m(avg_days=3.0, span=10, conflicts=2))
    db.insert("fall_a", 0, 1, _m(avg_days=7.0, span=20, conflicts=0))
    db.insert("fall_a", 0, 2, _m(avg_days=7.0, span=15, conflicts=1))
    rows = engine.fetch_window("fall_a", ["avg_days_all", "span_required", "elective_conflicts"], limit=10, offset=0)
    assert rows[0][IDX_AVG_DAYS] == 7.0
    assert rows[1][IDX_AVG_DAYS] == 7.0
    assert rows[0][IDX_SPAN] == 20
    assert rows[2][IDX_AVG_DAYS] == 3.0

def test_fetch_window_limit_restricts_result_size(db, engine):
    db.insert_batch("fall_a", [(0, i, _m(min_days=float(i))) for i in range(20)])
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=5, offset=0)
    assert len(rows) == 5

def test_fetch_window_offset_skips_top_rows(db, engine):
    db.insert_batch("fall_a", [(0, i, _m(min_days=float(i))) for i in range(20)])
    p1 = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    p2 = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=10)
    v1 = {r[IDX_MIN_DAYS] for r in p1}
    v2 = {r[IDX_MIN_DAYS] for r in p2}
    assert v1.isdisjoint(v2) and min(v1) > max(v2)

def test_fetch_window_offset_beyond_total_returns_empty(db, engine):
    db.insert("fall_a", 0, 0, _m())
    assert engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=999) == []

def test_fetch_window_empty_period_returns_empty_list(db, engine):
    assert engine.fetch_window("nonexistent", ["min_days_required"], limit=10, offset=0) == []

def test_fetch_window_pointer_values_are_correct(db, engine):
    db.insert("fall_a", batch_number=3, index_in_batch=17, metrics=_m())
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    assert rows[0][IDX_BATCH_NUMBER] == 3
    assert rows[0][IDX_INDEX_IN_BATCH] == 17

def test_fetch_window_unknown_column_raises(db, engine):
    with pytest.raises(ValueError, match="Unknown sort column"):
        engine.fetch_window("fall_a", ["DROP TABLE scores; --"], limit=10, offset=0)

def test_fetch_window_empty_sort_cols_raises(db, engine):
    with pytest.raises(ValueError):
        engine.fetch_window("fall_a", [], limit=10, offset=0)

def test_best_score_returns_max_for_higher_is_better_column(db, engine):
    db.insert_batch("fall_a", [(0, 0, _m(min_days=1.0)), (0, 1, _m(min_days=9.0)), (0, 2, _m(min_days=4.0))])
    assert engine.best_score("fall_a", "min_days_required") == 9.0

def test_best_score_returns_min_for_lower_is_better_column(db, engine):
    db.insert_batch("fall_a", [(0, 0, _m(conflicts=5)), (0, 1, _m(conflicts=0)), (0, 2, _m(conflicts=3))])
    assert engine.best_score("fall_a", "elective_conflicts") == 0

def test_best_score_returns_none_when_no_rows(db, engine):
    assert engine.best_score("empty_period", "min_days_required") is None

def test_best_score_unknown_column_raises(db, engine):
    with pytest.raises(ValueError, match="Unknown metric column"):
        engine.best_score("fall_a", "nonexistent_col")

def test_count_returns_correct_total(db, engine):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(7)])
    assert engine.count("fall_a") == 7

def test_count_is_zero_for_unknown_period(db, engine):
    assert engine.count("unknown_period") == 0

def test_fetch_window_isolated_per_period(db, engine):
    db.insert("fall_a",   0, 0, _m(min_days=10.0))
    db.insert("spring_b", 0, 0, _m(min_days=1.0))
    fall   = engine.fetch_window("fall_a",   ["min_days_required"], limit=10, offset=0)
    spring = engine.fetch_window("spring_b", ["min_days_required"], limit=10, offset=0)
    assert len(fall) == 1 and len(spring) == 1
    assert fall[0][IDX_MIN_DAYS] == 10.0 and spring[0][IDX_MIN_DAYS] == 1.0

def test_same_data_different_sort_cols_returns_different_order(db, engine):
    db.insert("fall_a", 0, 0, _m(min_days=1.0, conflicts=5))
    db.insert("fall_a", 0, 1, _m(min_days=9.0, conflicts=0))
    by_days = engine.fetch_window("fall_a", ["min_days_required"],  limit=10, offset=0)
    by_conf = engine.fetch_window("fall_a", ["elective_conflicts"], limit=10, offset=0)
    assert by_days[0][IDX_MIN_DAYS] == 9.0
    assert by_conf[0][IDX_CONFLICTS] == 0

def test_fetch_window_asc_for_avg_room_distance(db, engine):
    db.insert("fall_a", 0, 0, _m(avg_room_distance=3.0))
    db.insert("fall_a", 0, 1, _m(avg_room_distance=1.0))
    db.insert("fall_a", 0, 2, _m(avg_room_distance=2.0))
    rows = engine.fetch_window("fall_a", ["avg_room_distance"], limit=10, offset=0)
    vals = [r[IDX_ROOM_DIST] for r in rows]
    assert vals == sorted(vals)

def test_best_score_returns_min_for_avg_room_distance(db, engine):
    db.insert_batch("fall_a", [
        (0, 0, _m(avg_room_distance=3.0)),
        (0, 1, _m(avg_room_distance=1.0)),
        (0, 2, _m(avg_room_distance=2.0)),
    ])
    assert engine.best_score("fall_a", "avg_room_distance") == 1.0

def test_context_manager_closes_connection(db_path, db):
    db.insert("fall_a", 0, 0, _m())
    with RankingQueryEngine(db_path) as eng:
        assert len(eng.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)) == 1
    with pytest.raises(Exception):
        eng._conn.execute("SELECT 1")


# ---------------------------------------------------------------------------
# limit / offset validation
# ---------------------------------------------------------------------------

def test_fetch_window_zero_limit_raises(db, engine):
    with pytest.raises(ValueError, match="limit"):
        engine.fetch_window("fall_a", ["min_days_required"], limit=0, offset=0)

def test_fetch_window_negative_limit_raises(db, engine):
    with pytest.raises(ValueError, match="limit"):
        engine.fetch_window("fall_a", ["min_days_required"], limit=-1, offset=0)

def test_fetch_window_negative_offset_raises(db, engine):
    with pytest.raises(ValueError, match="offset"):
        engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=-1)

def test_fetch_window_zero_offset_is_valid(db, engine):
    db.insert("fall_a", 0, 0, _m())
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Deterministic tie-breaker
# ---------------------------------------------------------------------------

def test_fetch_window_stable_order_when_metrics_tied(db, engine):
    """Rows with identical metric values must come back in batch/index order."""
    # Insert 3 rows with identical metrics — tie-breaker should sort by (batch, index).
    db.insert("fall_a", 0, 2, _m(min_days=5.0))
    db.insert("fall_a", 0, 0, _m(min_days=5.0))
    db.insert("fall_a", 0, 1, _m(min_days=5.0))

    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)

    indices = [r[IDX_INDEX_IN_BATCH] for r in rows]
    assert indices == [0, 1, 2], "Tied rows must be ordered by index_in_batch ASC"

def test_pagination_is_stable_across_pages_with_tied_metrics(db, engine):
    """Two consecutive pages must not overlap when all metrics are identical."""
    db.insert_batch("fall_a", [(0, i, _m(min_days=3.0)) for i in range(10)])

    page1 = engine.fetch_window("fall_a", ["min_days_required"], limit=5, offset=0)
    page2 = engine.fetch_window("fall_a", ["min_days_required"], limit=5, offset=5)

    p1_idx = {r[IDX_INDEX_IN_BATCH] for r in page1}
    p2_idx = {r[IDX_INDEX_IN_BATCH] for r in page2}
    assert p1_idx.isdisjoint(p2_idx), "Pages must not overlap even with tied metrics"


def _metrics(avg_room_distance: float = 0.0) -> ScheduleMetrics:
    """Create score metrics for ranking tests."""
    return ScheduleMetrics(
        min_days_required=1,
        avg_days_all=1,
        elective_conflicts=0,
        span_required=1,
        max_exams_per_day=1,
        avg_room_distance=avg_room_distance,
    )


# ---------------------------------------------------------------------------
# Dynamic composite index (_ensure_index_for)
# ---------------------------------------------------------------------------

def test_dynamic_index_created_for_multi_column_sort(db, engine):
    """A composite index must be created when sort_cols has more than one column."""
    db.insert_batch("fall_a", [(0, i, _m(min_days=float(i), conflicts=10 - i)) for i in range(5)])
    engine.fetch_window("fall_a", ["min_days_required", "elective_conflicts"], limit=10, offset=0)

    key = ("min_days_required", "elective_conflicts")
    assert key in engine._built_indexes


def test_dynamic_index_skipped_for_single_column(db, engine):
    """Single-column combinations are covered by static indexes — no new index created."""
    db.insert("fall_a", 0, 0, _m())
    engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)

    # Key is cached but no CREATE INDEX should have been issued (static index covers it).
    assert ("min_days_required",) in engine._built_indexes


def test_dynamic_index_cached_after_first_call(db, engine):
    """Second call with the same sort_cols must not hit the DB (cache hit)."""
    db.insert("fall_a", 0, 0, _m())
    sort_cols = ["min_days_required", "elective_conflicts"]

    engine.fetch_window("fall_a", sort_cols, limit=10, offset=0)
    before = len(engine._built_indexes)

    engine.fetch_window("fall_a", sort_cols, limit=10, offset=0)
    after = len(engine._built_indexes)

    # Cache size must not grow on the second call.
    assert before == after


def test_dynamic_index_different_combinations_cached_separately(db, engine):
    """Each unique sort_cols combination gets its own cache entry."""
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(3)])
    combos = [
        ["min_days_required", "elective_conflicts"],
        ["avg_days_all", "span_required"],
        ["elective_conflicts", "max_exams_per_day", "avg_room_distance"],
    ]
    for combo in combos:
        engine.fetch_window("fall_a", combo, limit=10, offset=0)

    for combo in combos:
        assert tuple(combo) in engine._built_indexes


def test_dynamic_index_correct_sort_order_preserved(db, engine):
    """Multi-column sort via dynamic index must return rows in the correct order."""
    db.insert("fall_a", 0, 0, _m(min_days=5.0, conflicts=3))
    db.insert("fall_a", 0, 1, _m(min_days=5.0, conflicts=1))
    db.insert("fall_a", 0, 2, _m(min_days=9.0, conflicts=0))

    rows = engine.fetch_window(
        "fall_a", ["min_days_required", "elective_conflicts"], limit=10, offset=0
    )

    # Best min_days first; for tied min_days, lowest conflicts first.
    assert rows[0][IDX_MIN_DAYS] == 9.0
    assert rows[1][IDX_CONFLICTS] == 1
    assert rows[2][IDX_CONFLICTS] == 3


def test_dynamic_index_eliminates_temp_btree_in_query_plan(db, engine):
    """EXPLAIN QUERY PLAN must show a covering index and no TEMP B-TREE for multi-column sort.

    This directly verifies the Jira acceptance criterion: multi-column sorting
    must not fall back to an in-memory sort after _ensure_index_for() runs.
    """
    db.insert_batch("fall_a", [(0, i, _m(min_days=float(i), conflicts=i % 5)) for i in range(20)])

    # Trigger dynamic index creation via fetch_window.
    engine.fetch_window("fall_a", ["min_days_required", "elective_conflicts"], limit=10, offset=0)

    # Run EXPLAIN QUERY PLAN for the same ORDER BY that fetch_window uses.
    plan_rows = engine._conn.execute(
        "EXPLAIN QUERY PLAN "
        "SELECT batch_number, index_in_batch "
        "FROM scores WHERE period_id = ? "
        "ORDER BY min_days_required DESC, elective_conflicts ASC, "
        "batch_number ASC, index_in_batch ASC "
        "LIMIT 10 OFFSET 0",
        ("fall_a",),
    ).fetchall()

    plan_details = [dict(row)["detail"] for row in plan_rows]

    # The dynamic index must be used.
    assert any("idx_dynamic" in d for d in plan_details), (
        f"Expected dynamic index in query plan, got: {plan_details}"
    )

    # No temporary B-tree sort must appear — the index covers the full ORDER BY.
    assert all("TEMP B-TREE" not in d for d in plan_details), (
        f"Unexpected TEMP B-TREE in query plan: {plan_details}"
    )


def test_dynamic_index_persists_across_multiple_fetch_calls(db, engine):
    """Index created on first call is still used by later calls without re-creation."""
    db.insert_batch("fall_a", [(0, i, _m(min_days=float(i), avg_days=float(i))) for i in range(10)])
    sort_cols = ["min_days_required", "avg_days_all"]

    for _ in range(5):
        rows = engine.fetch_window("fall_a", sort_cols, limit=5, offset=0)
        assert len(rows) == 5

    assert tuple(sort_cols) in engine._built_indexes


def test_avg_room_distance_date_only_mode_uses_tie_breaker_order(tmp_path):
    """Verify avg_room_distance sorting is stable when all date-only scores are 0.0."""
    db_path = tmp_path / "scores.db"
    db = ScoresDatabase(db_path)

    db.insert("FALL_Aleph", batch_number=1, index_in_batch=2, metrics=_metrics())
    db.insert("FALL_Aleph", batch_number=0, index_in_batch=3, metrics=_metrics())
    db.insert("FALL_Aleph", batch_number=0, index_in_batch=1, metrics=_metrics())
    db.close()

    engine = RankingQueryEngine(db_path)

    rows = engine.fetch_window(
        period_id="FALL_Aleph",
        sort_cols=["avg_room_distance"],
        limit=10,
        offset=0,
    )

    engine.close()

    assert [(row[0], row[1]) for row in rows] == [
        (0, 1),
        (0, 3),
        (1, 2),
    ]