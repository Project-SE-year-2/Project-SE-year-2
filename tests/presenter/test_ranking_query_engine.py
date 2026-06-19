"""Tests for RankingQueryEngine — fetch_window returns list[tuple]."""

import pytest
from pathlib import Path
from src.presenter.scores_database import ScoresDatabase, ScheduleMetrics
from src.presenter.ranking_query_engine import RankingQueryEngine

IDX_BATCH_NUMBER   = 0
IDX_INDEX_IN_BATCH = 1
IDX_MIN_DAYS       = 2
IDX_AVG_DAYS       = 3
IDX_CONFLICTS      = 4
IDX_SPAN           = 5
IDX_DAILY_CAP      = 6


def _m(min_days=3.0, avg_days=4.0, conflicts=0, span=14, daily_cap=2):
    return ScheduleMetrics(min_days_required=min_days, avg_days_all=avg_days,
                           elective_conflicts=conflicts, span_required=span,
                           max_exams_per_day=daily_cap)


@pytest.fixture
def db_path(tmp_path): return tmp_path / "scores.db"

@pytest.fixture
def db(db_path): return ScoresDatabase(db_path)

@pytest.fixture
def engine(db_path, db): return RankingQueryEngine(db_path)


def test_fetch_window_returns_list_of_tuples(db, engine):
    db.insert("fall_a", 0, 0, _m())
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    assert isinstance(rows, list) and isinstance(rows[0], tuple)

def test_fetch_window_tuple_has_seven_elements(db, engine):
    db.insert("fall_a", 0, 0, _m())
    rows = engine.fetch_window("fall_a", ["min_days_required"], limit=10, offset=0)
    assert len(rows[0]) == 7

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
