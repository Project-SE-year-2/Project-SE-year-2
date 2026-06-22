"""
Tests for DailyCapCalculator.

DailyCapCalculator returns the maximum number of exam sessions scheduled on
any single calendar day across the entire institution.  
All courses count regardless of program, year, or requirement type.

Covers:
  - field_name returns 'max_exams_per_day'
  - empty schedule returns 0
  - single exam returns 1
  - all exams on different days returns 1
  - two exams on the same day returns 2
  - peak is the single busiest day, not the total
  - courses from different programs on the same day all count
  - courses from different years on the same day all count
"""

from datetime import date

from src.algorithm.scoring.daily_cap_calculator import DailyCapCalculator
from tests.algorithm.constraint_helpers import (
    make_obligatory_course as _obligatory,
    make_elective_course as _elective,
    make_schedule as _schedule,
)

PROG_A = "83101"
PROG_B = "83102"


# ---------------------------------------------------------------------------
# field_name
# ---------------------------------------------------------------------------

def test_field_name_returns_max_exams_per_day():
    assert DailyCapCalculator().field_name() == 'max_exams_per_day'


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_schedule_returns_zero():
    assert DailyCapCalculator().compute(_schedule()) == 0


def test_single_exam_returns_one():
    c1 = _obligatory("O1", PROG_A)
    sched = _schedule((c1, date(2026, 1, 5)))
    assert DailyCapCalculator().compute(sched) == 1


def test_all_exams_on_different_days_returns_one():
    c1 = _obligatory("O1", PROG_A)
    c2 = _obligatory("O2", PROG_A)
    c3 = _obligatory("O3", PROG_A)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 2)),
        (c3, date(2026, 1, 3)),
    )
    assert DailyCapCalculator().compute(sched) == 1


# ---------------------------------------------------------------------------
# Peak detection
# ---------------------------------------------------------------------------

def test_two_exams_same_day_returns_two():
    c1 = _obligatory("O1", PROG_A)
    c2 = _obligatory("O2", PROG_A)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert DailyCapCalculator().compute(sched) == 2


def test_peak_is_busiest_day_not_total():
    """Day 1 has 3 exams, day 2 has 1 - peak should be 3, not 4."""
    c1 = _obligatory("O1", PROG_A)
    c2 = _obligatory("O2", PROG_A)
    c3 = _obligatory("O3", PROG_A)
    c4 = _obligatory("O4", PROG_A)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 1)),
        (c3, date(2026, 1, 1)),
        (c4, date(2026, 1, 2)),
    )
    assert DailyCapCalculator().compute(sched) == 3


# ---------------------------------------------------------------------------
# Scope: all programs and years count globally
# ---------------------------------------------------------------------------

def test_courses_from_different_programs_same_day_all_count():
    c1 = _obligatory("O1", PROG_A)
    c2 = _obligatory("O2", PROG_B)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert DailyCapCalculator().compute(sched) == 2


def test_courses_from_different_years_same_day_all_count():
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _obligatory("O2", PROG_A, year=2)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert DailyCapCalculator().compute(sched) == 2


def test_elective_and_obligatory_both_counted():
    """Requirement type does not filter - every scheduled exam counts."""
    o1 = _obligatory("O1", PROG_A)
    e1 = _elective("E1", PROG_A)
    sched = _schedule(
        (o1, date(2026, 1, 5)),
        (e1, date(2026, 1, 5)),
    )
    assert DailyCapCalculator().compute(sched) == 2