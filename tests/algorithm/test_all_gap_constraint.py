"""
Tests for AllGapConstraint.

AllGapConstraint checks that every (program_id, year) cohort has at least K days
between any two consecutive exam dates, treating Obligatory and Elective courses
identically.

Covers:
  - constructor rejects k <= 0
  - schedule with no assignments is satisfied
  - single-exam cohort is always satisfied
  - gap exactly equal to K is satisfied (boundary)
  - gap one day less than K is violated
  - gap strictly greater than K is satisfied
  - multiple cohorts: violation in one cohort fails the whole schedule
  - multiple cohorts: all passing means satisfied
  - elective and obligatory courses are treated identically
  - same course appearing in multiple cohorts is checked per cohort
  - non-adjacent pair is fine when all adjacent gaps are >= K
  - three exams: middle gap violation is caught
"""

import pytest
from datetime import date

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement
from src.models.exam_schedule import ExamSchedule
from src.models.enums import Evaluation, Semester, ReqType, Moed
from src.algorithm.constraints.all_gap_constraint import AllGapConstraint


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _period():
    return ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "31-01-2026")


def _obligatory_course(course_id: str, program_id: str, year: int) -> Course:
    """Create a course with one Obligatory requirement."""
    c = Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam)
    c.add_requirement(ProgramRequirement(program_id, year, Semester.FALL, ReqType.Obligatory))
    return c


def _elective_course(course_id: str, program_id: str, year: int) -> Course:
    """Create a course with one Elective requirement."""
    c = Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam)
    c.add_requirement(ProgramRequirement(program_id, year, Semester.FALL, ReqType.Elective))
    return c


def _schedule(*assignments: tuple) -> ExamSchedule:
    """
    Build an ExamSchedule from (course, date) pairs.
    Uses a shared period so assignments() returns all entries.
    """
    period = _period()
    sched = ExamSchedule(period)
    for course, exam_date in assignments:
        sched.assign(course, exam_date)
    return sched


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

def test_constructor_rejects_zero_k():
    with pytest.raises(ValueError):
        AllGapConstraint(0)


def test_constructor_rejects_negative_k():
    with pytest.raises(ValueError):
        AllGapConstraint(-3)


def test_constructor_accepts_positive_k():
    # Should not raise.
    AllGapConstraint(1)
    AllGapConstraint(10)


# ---------------------------------------------------------------------------
# Edge cases: empty and single-exam schedules
# ---------------------------------------------------------------------------

def test_empty_schedule_is_satisfied():
    """A schedule with no assignments cannot violate any gap rule."""
    constraint = AllGapConstraint(k=3)
    sched = _schedule()
    assert constraint.is_satisfied(sched) is True


def test_single_exam_cohort_is_always_satisfied():
    """One exam per cohort means no adjacent pair to check."""
    constraint = AllGapConstraint(k=5)
    c1 = _obligatory_course("C1", "83101", 1)
    sched = _schedule((c1, date(2026, 1, 10)))
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Gap boundary tests (k = 3)
# ---------------------------------------------------------------------------

def test_gap_exactly_k_is_satisfied():
    """A gap of exactly K days must pass (boundary: delta == K is allowed)."""
    constraint = AllGapConstraint(k=3)
    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 4)),  # gap = 3 days
    )
    assert constraint.is_satisfied(sched) is True


def test_gap_one_less_than_k_is_violated():
    """A gap of K-1 days must fail."""
    constraint = AllGapConstraint(k=3)
    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 3)),  # gap = 2 days < 3
    )
    assert constraint.is_satisfied(sched) is False


def test_gap_greater_than_k_is_satisfied():
    """A gap larger than K days must pass."""
    constraint = AllGapConstraint(k=3)
    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 10)),  # gap = 9 days > 3
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Elective and obligatory courses treated identically
# ---------------------------------------------------------------------------

def test_elective_course_gap_violation_is_detected():
    """
    Elective courses must be evaluated just like obligatory ones.
    A gap violation between two elective exams must return False.
    """
    constraint = AllGapConstraint(k=5)
    c1 = _elective_course("E1", "83101", 2)
    c2 = _elective_course("E2", "83101", 2)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 4)),  # gap = 3 days < 5
    )
    assert constraint.is_satisfied(sched) is False


def test_mixed_elective_and_obligatory_gap_violation():
    """
    A gap violation between one obligatory and one elective exam in the
    same cohort must be caught — both types are included in the check.
    """
    constraint = AllGapConstraint(k=4)
    obligatory = _obligatory_course("C1", "83101", 1)
    elective    = _elective_course("C2",   "83101", 1)
    sched = _schedule(
        (obligatory, date(2026, 1, 1)),
        (elective,   date(2026, 1, 3)),  # gap = 2 days < 4
    )
    assert constraint.is_satisfied(sched) is False


def test_mixed_elective_and_obligatory_gap_satisfied():
    """
    When the gap between obligatory and elective exams meets K, must pass.
    """
    constraint = AllGapConstraint(k=4)
    obligatory = _obligatory_course("C1", "83101", 1)
    elective    = _elective_course("C2",   "83101", 1)
    sched = _schedule(
        (obligatory, date(2026, 1, 1)),
        (elective,   date(2026, 1, 5)),  # gap = 4 days == K
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Multiple cohorts
# ---------------------------------------------------------------------------

def test_violation_in_one_cohort_fails_whole_schedule():
    """
    If any single cohort violates the gap, is_satisfied must return False
    even when all other cohorts pass.
    """
    constraint = AllGapConstraint(k=3)

    # Cohort (83101, 1) — passes
    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)

    # Cohort (83102, 2) — violates (gap = 1 day)
    c3 = _obligatory_course("C3", "83102", 2)
    c4 = _obligatory_course("C4", "83102", 2)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 10)),  # gap = 9 days — fine
        (c3, date(2026, 1, 5)),
        (c4, date(2026, 1, 6)),   # gap = 1 day — violation
    )
    assert constraint.is_satisfied(sched) is False


def test_all_cohorts_passing_returns_true():
    """When every cohort satisfies the gap, the result must be True."""
    constraint = AllGapConstraint(k=3)

    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)
    c3 = _obligatory_course("C3", "83102", 2)
    c4 = _obligatory_course("C4", "83102", 2)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 5)),   # gap = 4 days >= 3
        (c3, date(2026, 1, 2)),
        (c4, date(2026, 1, 8)),   # gap = 6 days >= 3
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Courses belonging to multiple cohorts
# ---------------------------------------------------------------------------

def test_course_in_two_cohorts_checked_per_cohort():
    """
    A course with requirements in two different (program_id, year) groups
    contributes its exam date to BOTH cohorts independently.
    """
    constraint = AllGapConstraint(k=5)

    # c1 belongs to cohort (83101, 1) AND (83102, 1)
    c1 = Course("Shared", "SH1", "Prof", Evaluation.Exam)
    c1.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))
    c1.add_requirement(ProgramRequirement("83102", 1, Semester.FALL, ReqType.Obligatory))

    c2 = _obligatory_course("C2", "83101", 1)  # only in (83101, 1)
    c3 = _obligatory_course("C3", "83102", 1)  # only in (83102, 1)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 3)),   # gap with c1 in cohort (83101,1) = 2 days < 5
        (c3, date(2026, 1, 10)),  # gap with c1 in cohort (83102,1) = 9 days >= 5
    )
    # Cohort (83101,1) has gap 2 < 5 → violation
    assert constraint.is_satisfied(sched) is False


# ---------------------------------------------------------------------------
# Three-exam sequences
# ---------------------------------------------------------------------------

def test_three_exams_middle_gap_violation_is_caught():
    """
    With three exams, a violation in the middle adjacent pair must be detected
    even though the first and last exams are far apart.
    """
    constraint = AllGapConstraint(k=4)
    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)
    c3 = _obligatory_course("C3", "83101", 1)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 3)),   # gap from c1 = 2 days < 4 — violation
        (c3, date(2026, 1, 20)),  # gap from c2 = 17 days — fine
    )
    assert constraint.is_satisfied(sched) is False


def test_three_exams_all_gaps_satisfied():
    """All adjacent gaps >= K with three exams must pass."""
    constraint = AllGapConstraint(k=4)
    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)
    c3 = _obligatory_course("C3", "83101", 1)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 5)),   # gap = 4 days == K
        (c3, date(2026, 1, 12)),  # gap = 7 days > K
    )
    assert constraint.is_satisfied(sched) is True


def test_k_equals_one_adjacent_same_day_violates():
    """With k=1, two exams on the same day (gap=0) must fail."""
    constraint = AllGapConstraint(k=1)
    c1 = _obligatory_course("C1", "83101", 1)
    c2 = _obligatory_course("C2", "83101", 1)

    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),  # gap = 0 < 1
    )
    assert constraint.is_satisfied(sched) is False
