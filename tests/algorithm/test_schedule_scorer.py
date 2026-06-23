"""Unit tests for ScheduleScorer orchestrator (EP-102)."""

from datetime import date

import pytest

from src.algorithm.scoring.schedule_scorer import ScheduleScorer
from src.algorithm.scoring.schedule_metrics import ScheduleMetrics
from tests.algorithm.constraint_helpers import (
    make_obligatory_course,
    make_schedule,
)


@pytest.fixture
def scorer() -> ScheduleScorer:
    return ScheduleScorer()


def test_calculators_list_is_not_empty(scorer):
    assert len(scorer._calculators) > 0


def test_all_field_names_map_to_schedule_metrics_attributes(scorer):
    metric_fields = {f.name for f in ScheduleMetrics.__dataclass_fields__.values()}
    for calc in scorer._calculators:
        assert calc.field_name() in metric_fields


def test_compute_scores_returns_schedule_metrics_instance(scorer):
    sched = make_schedule()
    result = scorer.compute_scores(sched)
    assert isinstance(result, ScheduleMetrics)


def test_compute_scores_empty_schedule_all_zero(scorer):
    sched = make_schedule()
    result = scorer.compute_scores(sched)
    assert result.avg_days_all == 0.0
    assert result.min_days_required == 0.0
    assert result.elective_conflicts == 0
    assert result.span_required == 0
    assert result.max_exams_per_day == 0


def test_compute_scores_avg_days_all_correctly_delegated(scorer):
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    sched = make_schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 11)),
    )
    result = scorer.compute_scores(sched)
    assert result.avg_days_all == 10.0


def test_compute_scores_populates_all_fields(scorer):
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    sched = make_schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 11)),
    )
    result = scorer.compute_scores(sched)
    # All five fields must be present and numeric.
    assert isinstance(result.min_days_required, float)
    assert isinstance(result.avg_days_all, float)
    assert isinstance(result.elective_conflicts, (int, float))
    assert isinstance(result.span_required, (int, float))
    assert isinstance(result.max_exams_per_day, (int, float))


def test_default_factory_returns_schedule_scorer_instance():
    scorer = ScheduleScorer.default()
    assert isinstance(scorer, ScheduleScorer)


def test_default_factory_produces_working_scorer():
    scorer = ScheduleScorer.default()
    sched = make_schedule()
    result = scorer.compute_scores(sched)
    assert isinstance(result, ScheduleMetrics)
