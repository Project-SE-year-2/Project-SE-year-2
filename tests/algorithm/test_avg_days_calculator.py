"""Unit tests for AvgDaysCalculator (EP-97)."""

from datetime import date

import pytest

from src.algorithm.scoring.avg_days_calculator import AvgDaysCalculator
from tests.algorithm.constraint_helpers import (
    make_obligatory_course,
    make_elective_course,
    make_schedule,
)


@pytest.fixture
def calc() -> AvgDaysCalculator:
    return AvgDaysCalculator()


def test_field_name_returns_avg_days_all(calc):
    assert calc.field_name() == "avg_days_all"


def test_empty_schedule_returns_zero(calc):
    sched = make_schedule()
    assert calc.compute(sched) == 0.0


def test_single_exam_returns_zero(calc):
    c = make_obligatory_course("C1", "P1")
    sched = make_schedule((c, date(2026, 1, 10)))
    assert calc.compute(sched) == 0.0


def test_two_exams_same_cohort_correct_average(calc):
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    sched = make_schedule(
        (c1, date(2026, 1, 10)),
        (c2, date(2026, 1, 20)),
    )
    assert calc.compute(sched) == 10.0


def test_three_exams_average_of_two_gaps(calc):
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    c3 = make_obligatory_course("C3", "P1")
    sched = make_schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 11)),  # gap 10
        (c3, date(2026, 1, 17)),  # gap 6 → mean = 8.0
    )
    assert calc.compute(sched) == 8.0


def test_different_years_same_program_tracked_separately(calc):
    c1 = make_obligatory_course("C1", "P1", year=1)
    c2 = make_obligatory_course("C2", "P1", year=2)
    sched = make_schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 5)),
    )
    # Each cohort has only one exam → no gap within either cohort.
    assert calc.compute(sched) == 0.0


def test_multiple_programs_gaps_averaged_together(calc):
    # Program P1: gap 10; Program P2: gap 4 → mean = 7.0
    p1_c1 = make_obligatory_course("A1", "P1")
    p1_c2 = make_obligatory_course("A2", "P1")
    p2_c1 = make_obligatory_course("B1", "P2")
    p2_c2 = make_obligatory_course("B2", "P2")
    sched = make_schedule(
        (p1_c1, date(2026, 1, 1)),
        (p1_c2, date(2026, 1, 11)),
        (p2_c1, date(2026, 1, 1)),
        (p2_c2, date(2026, 1, 5)),
    )
    assert calc.compute(sched) == 7.0


def test_same_day_duplicates_are_deduplicated(calc):
    c1 = make_obligatory_course("C1", "P1")
    c2 = make_obligatory_course("C2", "P1")
    c3 = make_obligatory_course("C3", "P1")
    sched = make_schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 1)),  # duplicate — removed before gap calc
        (c3, date(2026, 1, 11)),
    )
    assert calc.compute(sched) == 10.0


def test_elective_courses_contribute_to_average(calc):
    obl = make_obligatory_course("C1", "P1")
    elc = make_elective_course("C2", "P1")
    sched = make_schedule(
        (obl, date(2026, 1, 1)),
        (elc, date(2026, 1, 8)),  # gap 7 — elective counted uniformly
    )
    assert calc.compute(sched) == 7.0
