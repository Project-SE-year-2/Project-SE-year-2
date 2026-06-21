"""
Tests for SpreadConstraint.

SpreadConstraint checks that the calendar window from the earliest to the
latest Obligatory exam in a (program_id, year) cohort spans at least K days.
Elective courses are excluded; cohorts with fewer than two Obligatory exams
are silently skipped.

Covers:
  - constructor rejects k <= 0
  - empty schedule is satisfied
  - single obligatory exam (span undefined) is skipped and satisfied
  - cohort with only elective courses is skipped and satisfied
  - span exactly K days is satisfied (boundary)
  - span exactly K-1 days is violated (boundary)
  - span greater than K is satisfied
  - elective courses are excluded from the span calculation
  - violation in one cohort fails the whole schedule even when others pass
  - all cohorts passing returns True
  - same course in two cohorts contributes to both spans independently
  - three obligatory exams: span is first-to-last, not adjacent
"""

import pytest
from datetime import date

from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, ReqType
from tests.algorithm.constraint_helpers import (
    make_elective_course as _elective_course,
    make_obligatory_course as _obligatory_course,
    make_schedule as _schedule,
)
from src.algorithm.constraints.spread_constraint import SpreadConstraint


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

def test_constructor_rejects_zero_k():
    with pytest.raises(ValueError):
        SpreadConstraint(0)


def test_constructor_rejects_negative_k():
    with pytest.raises(ValueError):
        SpreadConstraint(-5)


def test_constructor_accepts_positive_k():
    SpreadConstraint(1)
    SpreadConstraint(14)


# ---------------------------------------------------------------------------
# Edge cases: empty, single-exam, and elective-only cohorts
# ---------------------------------------------------------------------------

def test_empty_schedule_is_satisfied():
    """A schedule with no assignments has no cohorts to check."""
    constraint = SpreadConstraint(k=7)
    sched = _schedule()
    assert constraint.is_satisfied(sched) is True


def test_single_obligatory_exam_is_skipped():
    """
    A cohort with exactly one Obligatory exam produces no span.
    It must be skipped rather than treated as a violation.
    """
    constraint = SpreadConstraint(k=10)
    c1 = _obligatory_course("C1", "83101")
    sched = _schedule((c1, date(2026, 1, 5)))
    assert constraint.is_satisfied(sched) is True


def test_cohort_with_only_elective_courses_is_skipped():
    """
    A (program_id, year) group that has exams but all are Elective must be
    skipped - there are zero Obligatory dates, so the span is undefined.
    """
    constraint = SpreadConstraint(k=5)
    e1 = _elective_course("E1", "83101")
    e2 = _elective_course("E2", "83101")
    sched = _schedule(
        (e1, date(2026, 1, 1)),
        (e2, date(2026, 1, 2)),
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Span boundary tests (k = 10)
# ---------------------------------------------------------------------------

def test_span_exactly_k_is_satisfied():
    """A span of exactly K days must pass (span == K is allowed)."""
    constraint = SpreadConstraint(k=10)
    c1 = _obligatory_course("C1", "83101")
    c2 = _obligatory_course("C2", "83101")
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 11)),
    )
    assert constraint.is_satisfied(sched) is True


def test_span_one_less_than_k_is_violated():
    """A span of K-1 days must fail."""
    constraint = SpreadConstraint(k=10)
    c1 = _obligatory_course("C1", "83101")
    c2 = _obligatory_course("C2", "83101")
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 10)),
    )
    assert constraint.is_satisfied(sched) is False


def test_span_greater_than_k_is_satisfied():
    """A span larger than K must pass."""
    constraint = SpreadConstraint(k=10)
    c1 = _obligatory_course("C1", "83101")
    c2 = _obligatory_course("C2", "83101")
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 20)),
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Elective courses are excluded from the span
# ---------------------------------------------------------------------------

def test_elective_courses_do_not_widen_the_span():
    """
    Elective exams on dates outside the obligatory window must not count.
    The span is measured only between the first and last Obligatory dates.
    """
    constraint = SpreadConstraint(k=10)
    o1 = _obligatory_course("O1", "83101")
    o2 = _obligatory_course("O2", "83101")
    e1 = _elective_course("E1", "83101")

    sched = _schedule(
        (o1, date(2026, 1, 5)),
        (o2, date(2026, 1, 9)),
        (e1, date(2026, 1, 30)),
    )
    # If electives were counted, span would be 25 days (passes).
    # Since only obligatory matters, span = 4 days < K=10 → fails.
    assert constraint.is_satisfied(sched) is False


def test_elective_on_same_day_does_not_narrow_the_span():
    """
    An elective between two obligatory exams must not affect the span.
    The measurement is always min-obligatory to max-obligatory.
    """
    constraint = SpreadConstraint(k=5)
    o1 = _obligatory_course("O1", "83101")
    o2 = _obligatory_course("O2", "83101")
    e1 = _elective_course("E1", "83101")

    sched = _schedule(
        (o1, date(2026, 1, 1)),
        (e1, date(2026, 1, 4)),
        (o2, date(2026, 1, 7)),
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Multiple cohorts
# ---------------------------------------------------------------------------

def test_violation_in_one_cohort_fails_whole_schedule():
    """
    A span violation in a single cohort must fail the entire schedule
    even when all other cohorts pass.
    """
    constraint = SpreadConstraint(k=7)

    o1 = _obligatory_course("O1", "83101", year=1)
    o2 = _obligatory_course("O2", "83101", year=1)

    o3 = _obligatory_course("O3", "83102", year=2)
    o4 = _obligatory_course("O4", "83102", year=2)

    sched = _schedule(
        # Cohort (83101, 1) - passes (span = 14 days >= K=7)
        (o1, date(2026, 1, 1)),
        (o2, date(2026, 1, 15)),
        # Cohort (83102, 2) - violates (span = 3 days < K=7)
        (o3, date(2026, 1, 1)),
        (o4, date(2026, 1, 4)),
    )
    assert constraint.is_satisfied(sched) is False


def test_all_cohorts_passing_returns_true():
    """When every cohort's span meets K, is_satisfied must return True."""
    constraint = SpreadConstraint(k=7)
    o1 = _obligatory_course("O1", "83101", year=1)
    o2 = _obligatory_course("O2", "83101", year=1)
    o3 = _obligatory_course("O3", "83102", year=2)
    o4 = _obligatory_course("O4", "83102", year=2)

    sched = _schedule(
        (o1, date(2026, 1, 1)),
        (o2, date(2026, 1, 10)),
        (o3, date(2026, 1, 5)),
        (o4, date(2026, 1, 20)),
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Course belonging to multiple cohorts
# ---------------------------------------------------------------------------

def test_course_in_two_cohorts_contributes_to_both_spans():
    """
    An Obligatory course shared between two programs must extend both cohorts'
    exam windows.

    Each program has two other obligatory exams only 2 days apart
    (span = 2 < K=3).  The shared course on Jan 1 widens both windows (>= K=3). 
    If the shared date were missing from either cohort, that cohort would 
    violate K and the True assertion would catch it.
    """
    constraint = SpreadConstraint(k=3)

    # shared is Obligatory for both 83101 and 83102
    shared = Course("Shared", "SH1", "Prof", Evaluation.Exam)
    shared.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))
    shared.add_requirement(ProgramRequirement("83102", 1, Semester.FALL, ReqType.Obligatory))

    o_83101_a = _obligatory_course("A1", "83101")
    o_83101_b = _obligatory_course("A2", "83101")
    o_83102_a = _obligatory_course("B1", "83102")
    o_83102_b = _obligatory_course("B2", "83102")

    sched = _schedule(
        (shared,    date(2026, 1, 1)),
        (o_83101_a, date(2026, 1, 2)),
        (o_83101_b, date(2026, 1, 4)),
        (o_83102_a, date(2026, 1, 5)),
        (o_83102_b, date(2026, 1, 7)),
    )
    # If shared doesn't reach either program, that program's span = 2 < K=3 → would fail.
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Three-exam sequences - span is first-to-last, not adjacent
# ---------------------------------------------------------------------------

def test_three_exams_span_is_first_to_last():
    """
    With three exams, the span is measured from the first to the last date,
    not as the sum of adjacent gaps.
    """
    constraint = SpreadConstraint(k=10)
    o1 = _obligatory_course("O1", "83101")
    o2 = _obligatory_course("O2", "83101")
    o3 = _obligatory_course("O3", "83101")

    sched = _schedule(
        (o1, date(2026, 1, 1)),
        (o2, date(2026, 1, 3)),
        (o3, date(2026, 1, 15)),
    )
    # Span = Jan 1 → Jan 15 = 14 days >= K=10 → passes
    assert constraint.is_satisfied(sched) is True


def test_three_exams_small_gap_at_end_does_not_affect_span():
    """
    Mirror of test_three_exams_span_is_first_to_last with the small gap
    between the 2nd and 3rd exam instead of the 1st and 2nd.
    The span is still first-to-last (14 days >= K=10) - the position of the
    small gap does not matter.
    """
    constraint = SpreadConstraint(k=10)
    o1 = _obligatory_course("O1", "83101")
    o2 = _obligatory_course("O2", "83101")
    o3 = _obligatory_course("O3", "83101")

    sched = _schedule(
        (o1, date(2026, 1, 1)),
        (o2, date(2026, 1, 13)),
        (o3, date(2026, 1, 15)),
    )
    # Span = Jan 1 → Jan 15 = 14 days >= K=10 → passes
    assert constraint.is_satisfied(sched) is True