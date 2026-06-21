"""
Tests for DailyCapConstraint.

DailyCapConstraint checks that no single calendar date has more than K
exam sessions scheduled across the entire institution, regardless of
program or year cohort.

Covers:
  - constructor rejects k <= 0
  - empty schedule is satisfied
  - single exam is always satisfied
  - exactly K exams on one day is satisfied (boundary)
  - K+1 exams on one day is violated (boundary)
  - fewer than K exams on one day is satisfied
  - violation on one day fails the whole schedule even if other days are fine
  - all days within cap returns True
  - courses from different programs on the same day all count toward the cap
  - exams spread across different days each count independently
  - k=1 with two exams on the same day violates
"""

import pytest
from datetime import date

from tests.algorithm.constraint_helpers import (
    make_elective_course,
    make_obligatory_course,
    make_schedule as _schedule,
)
from src.algorithm.constraints.daily_cap_constraint import DailyCapConstraint

# DailyCapConstraint is program-agnostic, so most tests don't care which 
# program a course belongs to - defaults keep the test bodies short.
def _course(course_id: str, program_id: str = "83101", year: int = 1):
    return make_obligatory_course(course_id, program_id, year)


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

def test_constructor_rejects_zero_k():
    with pytest.raises(ValueError):
        DailyCapConstraint(0)


def test_constructor_rejects_negative_k():
    with pytest.raises(ValueError):
        DailyCapConstraint(-5)


def test_constructor_accepts_positive_k():
    DailyCapConstraint(1)
    DailyCapConstraint(10)


# ---------------------------------------------------------------------------
# Edge cases: empty and single-exam schedules
# ---------------------------------------------------------------------------

def test_empty_schedule_is_satisfied():
    """A schedule with no assignments cannot violate a daily cap."""
    constraint = DailyCapConstraint(k=3)
    sched = _schedule()
    assert constraint.is_satisfied(sched) is True


def test_single_exam_is_always_satisfied():
    """One exam in the whole schedule can never breach any positive cap."""
    constraint = DailyCapConstraint(k=1)
    c1 = _course("C1")
    sched = _schedule((c1, date(2026, 1, 10)))
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Boundary tests (k = 3)
# ---------------------------------------------------------------------------

def test_exactly_k_exams_on_one_day_is_satisfied():
    """K exams on a single day must pass (count == K is allowed)."""
    constraint = DailyCapConstraint(k=3)
    c1 = _course("C1")
    c2 = _course("C2")
    c3 = _course("C3")
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
        (c3, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is True


def test_k_plus_one_exams_on_one_day_is_violated():
    """K+1 exams on a single day must fail."""
    constraint = DailyCapConstraint(k=3)
    c1 = _course("C1")
    c2 = _course("C2")
    c3 = _course("C3")
    c4 = _course("C4")
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
        (c3, date(2026, 1, 5)),
        (c4, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is False


def test_fewer_than_k_exams_on_one_day_is_satisfied():
    """Fewer than K exams on any single day must pass."""
    constraint = DailyCapConstraint(k=3)
    c1 = _course("C1")
    c2 = _course("C2")
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Multiple days
# ---------------------------------------------------------------------------

def test_violation_on_one_day_fails_whole_schedule():
    """A cap breach on a single day fails even when all other days are fine."""
    constraint = DailyCapConstraint(k=2)
    c1 = _course("C1")
    c2 = _course("C2")
    c3 = _course("C3")
    c4 = _course("C4")
    c5 = _course("C5")
    c6 = _course("C6")
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 2)),
        (c3, date(2026, 1, 2)),
        (c4, date(2026, 1, 3)),
        (c5, date(2026, 1, 3)),
        (c6, date(2026, 1, 3)),
    )
    assert constraint.is_satisfied(sched) is False


def test_all_days_within_cap_returns_true():
    """When every day stays at or below K, is_satisfied must return True."""
    constraint = DailyCapConstraint(k=2)
    c1 = _course("C1")
    c2 = _course("C2")
    c3 = _course("C3")
    c4 = _course("C4")
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 1)),
        (c3, date(2026, 1, 2)),
        (c4, date(2026, 1, 3)),
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Cross-program counting
# ---------------------------------------------------------------------------

def test_courses_from_different_programs_on_same_day_all_count():
    """
    Exams from entirely different programs on the same day must all count
    toward the cap - the constraint is institution-wide, not per-cohort.
    """
    constraint = DailyCapConstraint(k=2)
    c1 = _course("C1", program_id="83101", year=1)
    c2 = _course("C2", program_id="83102", year=2)
    c3 = _course("C3", program_id="83103", year=3)
    sched = _schedule(
        (c1, date(2026, 1, 10)),
        (c2, date(2026, 1, 10)),
        (c3, date(2026, 1, 10)),
    )
    assert constraint.is_satisfied(sched) is False


def test_exams_on_different_days_each_count_independently():
    """Exams spread across distinct dates never collide toward the cap."""
    constraint = DailyCapConstraint(k=1)
    c1 = _course("C1")
    c2 = _course("C2")
    c3 = _course("C3")
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 2)),
        (c3, date(2026, 1, 3)),
    )
    assert constraint.is_satisfied(sched) is True


def test_k_equals_one_two_exams_same_day_violates():
    """With k=1, two exams on the same day must fail."""
    constraint = DailyCapConstraint(k=1)
    c1 = _course("C1")
    c2 = _course("C2")
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is False


# ---------------------------------------------------------------------------
# Elective and obligatory courses both count
# ---------------------------------------------------------------------------

def test_elective_and_obligatory_both_count_toward_cap():
    """
    The cap applies to every exam session regardless of requirement type.
    One elective + one obligatory on the same day must both count toward K.
    """
    constraint = DailyCapConstraint(k=1)
    elective = make_elective_course("E1", "83101")
    obligatory = make_obligatory_course("O1", "83101")
    sched = _schedule(
        (elective,   date(2026, 1, 5)),
        (obligatory, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is False