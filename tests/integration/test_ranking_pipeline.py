"""
EP-106 — Integration & regression tests for the ranking pipeline.

The unit tests cover each component alone: test_schedule_scorer (scoring),
test_scores_database (storage), test_ranking_query_engine (queries). What none
of them prove is that the three fit together — that a real schedule scored by
ScheduleScorer, written through ScoresDatabase, comes back out of
RankingQueryEngine in the right order with the right values.

This suite drives the full path end to end:

    ExamSchedule -> ScheduleScorer.compute_scores -> ScoresDatabase.insert
                 -> RankingQueryEngine.fetch_window / best_score / count

Schedules are built from real Course/ExamSchedule objects (constraint_helpers),
so the metric values are produced by the actual calculators, never hand-faked.
Most assertions check *ordering* against the values the query itself returns,
so they stay correct even if a calculator's exact formula is tweaked later.
"""

from datetime import date

import pytest

from src.algorithm.scoring.schedule_scorer import ScheduleScorer
from src.presenter.scores_database import ScoresDatabase
from src.presenter.ranking_query_engine import RankingQueryEngine
from tests.algorithm.constraint_helpers import (
    make_obligatory_course,
    make_elective_course,
    make_schedule,
)

# Column positions in the tuples fetch_window() returns.
IDX_BATCH     = 0
IDX_INDEX     = 1
IDX_MIN_DAYS  = 2
IDX_AVG_DAYS  = 3
IDX_CONFLICTS = 4
IDX_SPAN      = 5
IDX_DAILY_CAP = 6
IDX_ROOM_DIST = 7

PERIOD = "fall_a"


@pytest.fixture
def scorer() -> ScheduleScorer:
    return ScheduleScorer.default()


@pytest.fixture
def db(tmp_path) -> ScoresDatabase:
    # Real on-disk SQLite file in a temp dir — the same class the Engine uses.
    return ScoresDatabase(tmp_path / "scores.db")


@pytest.fixture
def engine(tmp_path, db) -> RankingQueryEngine:
    # Opens its own read-only connection to the very same file the db writes to.
    return RankingQueryEngine(tmp_path / "scores.db")


def _score_and_insert(scorer, db, schedule, batch=0, index=0, period=PERIOD):
    """Run a schedule through the scorer and persist it; return its metrics."""
    metrics = scorer.compute_scores(schedule)
    db.insert(period, batch_number=batch, index_in_batch=index, metrics=metrics)
    return metrics


# ---------------------------------------------------------------------------
# Full round-trip: every scored value survives the storage layer
# ---------------------------------------------------------------------------

def test_all_six_metrics_persist_through_pipeline(scorer, db, engine):
    """What the scorer computes is exactly what the query returns."""
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    sched = make_schedule((c1, date(2026, 1, 1)), (c2, date(2026, 1, 11)))

    metrics = _score_and_insert(scorer, db, sched)

    rows = engine.fetch_window(PERIOD, ["avg_days_all"], limit=10, offset=0)
    assert len(rows) == 1
    row = rows[0]
    assert row[IDX_AVG_DAYS]   == metrics.avg_days_all
    assert row[IDX_CONFLICTS]  == metrics.elective_conflicts
    assert row[IDX_SPAN]       == metrics.span_required
    assert row[IDX_DAILY_CAP]  == metrics.max_exams_per_day
    assert row[IDX_ROOM_DIST]  == metrics.avg_room_distance


def test_pointer_columns_round_trip(scorer, db, engine):
    """batch_number / index_in_batch are the pointer ResultsReader needs later."""
    c1 = make_obligatory_course("C1", "P1")
    sched = make_schedule((c1, date(2026, 1, 5)))

    _score_and_insert(scorer, db, sched, batch=3, index=17)

    row = engine.fetch_window(PERIOD, ["avg_days_all"], limit=10, offset=0)[0]
    assert row[IDX_BATCH] == 3
    assert row[IDX_INDEX] == 17


# ---------------------------------------------------------------------------
# Ranking order matches the scored values
# ---------------------------------------------------------------------------

def test_higher_is_better_metric_ranked_first(scorer, db, engine):
    """avg_days_all is higher-is-better: the widest-spread schedule ranks #1."""
    # Three single-cohort schedules with deliberately different average gaps.
    tight = make_schedule(
        (make_obligatory_course("A1", "P1"), date(2026, 1, 1)),
        (make_obligatory_course("A2", "P1"), date(2026, 1, 3)),   # gap 2
    )
    wide = make_schedule(
        (make_obligatory_course("B1", "P1"), date(2026, 1, 1)),
        (make_obligatory_course("B2", "P1"), date(2026, 1, 21)),  # gap 20
    )
    mid = make_schedule(
        (make_obligatory_course("C1", "P1"), date(2026, 1, 1)),
        (make_obligatory_course("C2", "P1"), date(2026, 1, 11)),  # gap 10
    )
    _score_and_insert(scorer, db, tight, index=0)
    _score_and_insert(scorer, db, wide, index=1)
    _score_and_insert(scorer, db, mid, index=2)

    rows = engine.fetch_window(PERIOD, ["avg_days_all"], limit=10, offset=0)
    avg_values = [r[IDX_AVG_DAYS] for r in rows]
    # Best (largest gap) first, descending.
    assert avg_values == sorted(avg_values, reverse=True)
    assert rows[0][IDX_AVG_DAYS] == max(avg_values)


def test_lower_is_better_metric_ranked_ascending(scorer, db, engine):
    """elective_conflicts is lower-is-better: the cleanest schedule ranks #1."""
    # Zero conflicts: two electives on different days.
    clean = make_schedule(
        (make_elective_course("E1", "P1"), date(2026, 1, 1)),
        (make_elective_course("E2", "P1"), date(2026, 1, 2)),
    )
    # Two conflicts: three electives stacked on the same day, same program.
    messy = make_schedule(
        (make_elective_course("F1", "P1"), date(2026, 1, 5)),
        (make_elective_course("F2", "P1"), date(2026, 1, 5)),
        (make_elective_course("F3", "P1"), date(2026, 1, 5)),
    )
    _score_and_insert(scorer, db, clean, index=0)
    _score_and_insert(scorer, db, messy, index=1)

    rows = engine.fetch_window(PERIOD, ["elective_conflicts"], limit=10, offset=0)
    conflict_values = [r[IDX_CONFLICTS] for r in rows]
    assert conflict_values == sorted(conflict_values)       # ascending
    assert rows[0][IDX_CONFLICTS] == min(conflict_values)   # fewest first


def test_best_score_reflects_scored_value(scorer, db, engine):
    """best_score() returns the same top value fetch_window ranks first."""
    s1 = make_schedule(
        (make_obligatory_course("A1", "P1"), date(2026, 1, 1)),
        (make_obligatory_course("A2", "P1"), date(2026, 1, 6)),
    )
    s2 = make_schedule(
        (make_obligatory_course("B1", "P1"), date(2026, 1, 1)),
        (make_obligatory_course("B2", "P1"), date(2026, 1, 31)),
    )
    _score_and_insert(scorer, db, s1, index=0)
    _score_and_insert(scorer, db, s2, index=1)

    top = engine.fetch_window(PERIOD, ["avg_days_all"], limit=1, offset=0)[0]
    assert engine.best_score(PERIOD, "avg_days_all") == top[IDX_AVG_DAYS]


# ---------------------------------------------------------------------------
# Regression: infinity from MinDaysCalculator must not break storage
# ---------------------------------------------------------------------------

def test_infinite_min_days_normalized_to_zero_through_pipeline(scorer, db, engine):
    """
    A schedule with no obligatory *pair* makes MinDaysCalculator return inf.
    SQLite cannot store inf cleanly, so ScoresDatabase normalizes it to 0.0.
    This guards that scorer↔database boundary end to end.
    """
    lone = make_schedule((make_obligatory_course("A1", "P1"), date(2026, 1, 1)))

    metrics = scorer.compute_scores(lone)
    assert metrics.min_days_required == float("inf")   # scorer side

    db.insert(PERIOD, 0, 0, metrics)                   # must not raise

    row = engine.fetch_window(PERIOD, ["min_days_required"], limit=10, offset=0)[0]
    assert row[IDX_MIN_DAYS] == 0.0                    # stored side


# ---------------------------------------------------------------------------
# Counting and period isolation
# ---------------------------------------------------------------------------

def test_count_matches_number_of_scored_schedules(scorer, db, engine):
    for i in range(5):
        sched = make_schedule((make_obligatory_course(f"C{i}", "P1"), date(2026, 1, 1 + i)))
        _score_and_insert(scorer, db, sched, index=i)

    assert engine.count(PERIOD) == 5


def test_periods_are_isolated_in_ranking(scorer, db, engine):
    """Schedules scored into different periods never bleed into each other."""
    fall = make_schedule(
        (make_obligatory_course("A1", "P1"), date(2026, 1, 1)),
        (make_obligatory_course("A2", "P1"), date(2026, 1, 3)),
    )
    spring = make_schedule(
        (make_obligatory_course("B1", "P1"), date(2026, 1, 1)),
        (make_obligatory_course("B2", "P1"), date(2026, 1, 21)),
    )
    _score_and_insert(scorer, db, fall, period="fall_a")
    _score_and_insert(scorer, db, spring, period="spring_b")

    assert engine.count("fall_a") == 1
    assert engine.count("spring_b") == 1
    fall_row = engine.fetch_window("fall_a", ["avg_days_all"], limit=10, offset=0)[0]
    spring_row = engine.fetch_window("spring_b", ["avg_days_all"], limit=10, offset=0)[0]
    assert fall_row[IDX_AVG_DAYS] != spring_row[IDX_AVG_DAYS]


# ---------------------------------------------------------------------------
# Batch path: insert_batch is what the Engine actually calls
# ---------------------------------------------------------------------------

def test_insert_batch_path_matches_individual_scoring(scorer, db, engine):
    """The Engine scores a batch then insert_batch()es it — verify that path."""
    schedules = [
        make_schedule(
            (make_obligatory_course(f"A{i}", "P1"), date(2026, 1, 1)),
            (make_obligatory_course(f"B{i}", "P1"), date(2026, 1, 1 + (i + 1) * 2)),
        )
        for i in range(4)
    ]
    rows = [
        (0, i, scorer.compute_scores(sched))
        for i, sched in enumerate(schedules)
    ]
    db.insert_batch(PERIOD, rows)

    assert engine.count(PERIOD) == 4
    fetched = engine.fetch_window(PERIOD, ["avg_days_all"], limit=10, offset=0)
    avg_values = [r[IDX_AVG_DAYS] for r in fetched]
    assert avg_values == sorted(avg_values, reverse=True)


# ---------------------------------------------------------------------------
# Deterministic ordering when scored values tie
# ---------------------------------------------------------------------------

def test_tied_scores_break_by_pointer(scorer, db, engine):
    """Identical schedules score identically; order falls back to (batch, index)."""
    for i in (2, 0, 1):
        sched = make_schedule(
            (make_obligatory_course(f"A{i}", "P1"), date(2026, 1, 1)),
            (make_obligatory_course(f"B{i}", "P1"), date(2026, 1, 11)),
        )
        _score_and_insert(scorer, db, sched, batch=0, index=i)

    rows = engine.fetch_window(PERIOD, ["avg_days_all"], limit=10, offset=0)
    indices = [r[IDX_INDEX] for r in rows]
    assert indices == [0, 1, 2]
