"""Tests for WindowState."""

import pytest
from pathlib import Path
from src.presenter.scores_database import ScoresDatabase, ScheduleMetrics
from src.presenter.ranking_query_engine import RankingQueryEngine
from src.presenter.window_state import WindowState, DEFAULT_PAGE_SIZE


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

@pytest.fixture
def state(engine): return WindowState(period_id="fall_a", engine=engine)


# load()
def test_load_fetches_rows(db, state):
    db.insert("fall_a", 0, 0, _m()); db.insert("fall_a", 0, 1, _m())
    state.load()
    assert len(state.rows) == 2

def test_load_resets_offset_to_zero(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(5)])
    state.offset = 99
    state.load()
    assert state.offset == 0

def test_load_clears_pending_flag(db, state):
    db.insert("fall_a", 0, 0, _m())
    state.set_pending()
    state.load()
    assert state.pending is False

def test_load_updates_total(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(7)])
    state.load()
    assert state.total == 7

def test_load_empty_period_gives_empty_rows(state):
    state.load()
    assert state.rows == [] and state.total == 0


# refresh()
def test_refresh_updates_rows_with_new_data(db, state):
    db.insert("fall_a", 0, 0, _m())
    state.load()
    db.insert("fall_a", 0, 1, _m())
    state.refresh()
    assert len(state.rows) == 2

def test_refresh_does_not_reset_offset(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(DEFAULT_PAGE_SIZE + 5)])
    state.load()
    state.next_page()
    offset_before = state.offset
    state.refresh()
    assert state.offset == offset_before

def test_refresh_clears_pending_flag(db, state):
    db.insert("fall_a", 0, 0, _m())
    state.set_pending()
    state.refresh()
    assert state.pending is False


# set_sort()
def test_set_sort_changes_row_order(db, state):
    db.insert("fall_a", 0, 0, _m(min_days=1.0, conflicts=5))
    db.insert("fall_a", 0, 1, _m(min_days=9.0, conflicts=0))
    state.set_sort(["min_days_required"])
    first_by_min = state.rows[0]["min_days_required"]
    state.set_sort(["elective_conflicts"])
    first_by_conf = state.rows[0]["elective_conflicts"]
    assert first_by_min == 9.0
    assert first_by_conf == 0

def test_set_sort_resets_to_page_one(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(DEFAULT_PAGE_SIZE + 5)])
    state.load(); state.next_page()
    assert state.offset > 0
    state.set_sort(["avg_days_all"])
    assert state.offset == 0

def test_set_sort_updates_sort_cols(state):
    state.set_sort(["avg_days_all", "span_required"])
    assert state.sort_cols == ["avg_days_all", "span_required"]

def test_set_sort_unknown_column_raises(state):
    with pytest.raises(ValueError):
        state.set_sort(["nonexistent_column"])

def test_set_sort_empty_raises(state):
    with pytest.raises(ValueError):
        state.set_sort([])

def test_set_sort_clears_pending(db, state):
    db.insert("fall_a", 0, 0, _m())
    state.set_pending()
    state.set_sort(["min_days_required"])
    assert state.pending is False


# Pagination
def test_next_page_advances_offset(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(DEFAULT_PAGE_SIZE + 5)])
    state.load()
    assert state.next_page() is True
    assert state.offset == DEFAULT_PAGE_SIZE

def test_next_page_returns_false_on_last_page(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(3)])
    state.load()
    assert state.next_page() is False
    assert state.offset == 0

def test_prev_page_decreases_offset(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(DEFAULT_PAGE_SIZE + 5)])
    state.load(); state.next_page()
    assert state.prev_page() is True
    assert state.offset == 0

def test_prev_page_returns_false_on_first_page(db, state):
    db.insert("fall_a", 0, 0, _m())
    state.load()
    assert state.prev_page() is False
    assert state.offset == 0

def test_pagination_pages_cover_all_rows_without_overlap(db, state):
    n = DEFAULT_PAGE_SIZE + 10
    db.insert_batch("fall_a", [(0, i, _m(min_days=float(i))) for i in range(n)])
    state.load()
    v1 = {r["min_days_required"] for r in state.rows}
    state.next_page()
    v2 = {r["min_days_required"] for r in state.rows}
    assert v1.isdisjoint(v2) and len(v1) + len(v2) == n


# current_page / total_pages
def test_current_page_starts_at_one(state):
    assert state.current_page == 1

def test_current_page_increments_after_next_page(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(DEFAULT_PAGE_SIZE + 5)])
    state.load(); state.next_page()
    assert state.current_page == 2

def test_total_pages_single_page(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(3)])
    state.load()
    assert state.total_pages == 1

def test_total_pages_multiple_pages(db, state):
    db.insert_batch("fall_a", [(0, i, _m()) for i in range(DEFAULT_PAGE_SIZE + 1)])
    state.load()
    assert state.total_pages == 2

def test_total_pages_is_one_when_empty(state):
    state.load()
    assert state.total_pages == 1


# set_pending
def test_set_pending_sets_flag(state):
    state.set_pending()
    assert state.pending is True

def test_set_pending_does_not_change_rows(db, state):
    db.insert("fall_a", 0, 0, _m())
    state.load()
    rows_before = list(state.rows)
    state.set_pending()
    assert state.rows == rows_before
