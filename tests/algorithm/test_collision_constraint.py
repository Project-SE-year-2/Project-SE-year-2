"""
Tests for CollisionConstraint.

CollisionConstraint checks that no single (program_id, date) cell
has more than K elective conflicts scheduled.  Obligatory courses are invisible
to this constraint; the grouping key is program_id alone (not year).

Covers:
  - constructor rejects k < 0 but accepts k = 0
  - empty schedule is satisfied
  - single elective is always satisfied
  - exactly K conflicts for a program on one day is satisfied (boundary)
  - K+1 conflicts for a program on one day is violated (boundary)
  - k=0 allows one elective but rejects two electives in the same cell
  - obligatory courses on the same day are not counted
  - replacing an elective with an obligatory removes the violation
  - programs are evaluated independently — counts are not summed across programs
  - violation in one program fails the whole schedule; fixing it makes it pass
  - courses elective in program A and obligatory in program B count only toward A
  - year does not affect grouping — year-1 and year-2 electives in the same program count together
  - k=0 fails as soon as any program has even one elective scheduled
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
from src.algorithm.constraints.collision_constraint import CollisionConstraint


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

def test_constructor_rejects_negative_k():
    with pytest.raises(ValueError):
        CollisionConstraint(-1)


def test_constructor_accepts_zero_k():
    """k=0 is valid - it means no two electives from the same program may share a day."""
    CollisionConstraint(0)


def test_constructor_accepts_positive_k():
    CollisionConstraint(1)
    CollisionConstraint(5)


# ---------------------------------------------------------------------------
# Edge cases: empty and single-exam schedules
# ---------------------------------------------------------------------------

def test_empty_schedule_is_satisfied():
    """A schedule with no assignments cannot violate any elective cap."""
    constraint = CollisionConstraint(k=2)
    sched = _schedule()
    assert constraint.is_satisfied(sched) is True


def test_single_elective_is_always_satisfied():
    """One elective for a program can never breach the cap on its own."""
    constraint = CollisionConstraint(k=1)
    c1 = _elective_course("E1", "83101")
    sched = _schedule((c1, date(2026, 1, 10)))
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# Boundary tests (k = 2)
# ---------------------------------------------------------------------------

def test_exactly_k_electives_on_one_day_is_satisfied():
    """K elective exams for the same program on one day must pass (count == K is allowed)."""
    constraint = CollisionConstraint(k=2)
    c1 = _elective_course("E1", "83101")
    c2 = _elective_course("E2", "83101")
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is True


def test_k_plus_one_electives_on_one_day_is_violated():
    """K+1 conflicts for the same program on one day must fail."""
    constraint = CollisionConstraint(k=2)
    c1 = _elective_course("E1", "83101")
    c2 = _elective_course("E2", "83101")
    c3 = _elective_course("E3", "83101")
    c4 = _elective_course("E4", "83101")
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
        (c3, date(2026, 1, 5)),
        (c4, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is False


# ---------------------------------------------------------------------------
# Obligatory courses are ignored
# ---------------------------------------------------------------------------

def test_obligatory_courses_are_not_counted():
    """
    Even if many obligatory courses share a date, they must not count toward
    the elective cap - only elective requirements trigger the constraint.
    """
    constraint = CollisionConstraint(k=1)
    e1 = _elective_course("E1", "83101")
    o1 = _obligatory_course("O1", "83101")
    o2 = _obligatory_course("O2", "83101")
    o3 = _obligatory_course("O3", "83101")
    sched = _schedule(
        (e1, date(2026, 1, 5)),
        # obligatory - not counted
        (o1, date(2026, 1, 5)),  
        (o2, date(2026, 1, 5)),
        (o3, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is True


def test_only_electives_trigger_violation():
    """Replacing a second elective with an obligatory must remove the violation."""
    constraint = CollisionConstraint(k=0)
    e1 = _elective_course("E1", "83101")
    e2 = _elective_course("E2", "83101")
    o2 = _obligatory_course("O2", "83101")

    # Two electives on the same day → 1 conflict > K=0 → violation
    violating = _schedule(
        (e1, date(2026, 1, 5)),
        (e2, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(violating) is False

    # Replace e2 with an obligatory → only 1 elective remains, no violation
    passing = _schedule(
        (e1, date(2026, 1, 5)),
        (o2, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(passing) is True


# ---------------------------------------------------------------------------
# Cross-program isolation
# ---------------------------------------------------------------------------

def test_does_not_sum_across_programs():
    """
    Elective counts must be checked per program, not summed institution-wide.
    Four electives total (2 per program) must pass when K=2, even though
    a naive global sum of 4 would exceed K.
    """
    constraint = CollisionConstraint(k=2)
    p1_e1 = _elective_course("P1_E1", "83101")
    p1_e2 = _elective_course("P1_E2", "83101")
    p2_e1 = _elective_course("P2_E1", "83102")
    p2_e2 = _elective_course("P2_E2", "83102")
    sched = _schedule(
        (p1_e1, date(2026, 1, 1)),
        (p1_e2, date(2026, 1, 1)),
        (p2_e1, date(2026, 1, 1)),
        (p2_e2, date(2026, 1, 1)),
    )
    assert constraint.is_satisfied(sched) is True


def test_different_programs_evaluated_independently():
    """
    Program B's violation must not contaminate Program A's count.
    Removing B's extra elective must make the whole schedule pass.
    """
    constraint = CollisionConstraint(k=0)
    a1 = _elective_course("A1", "83101")
    b1 = _elective_course("B1", "83102")
    b2 = _elective_course("B2", "83102")

    sched = _schedule(
        (a1, date(2026, 1, 1)),
        (b1, date(2026, 1, 1)),
        (b2, date(2026, 1, 1)),
    )
    # B has 2 electives > K=0 → whole schedule fails
    assert constraint.is_satisfied(sched) is False

    # Remove B's extra elective: A=1, B=1 - both <= K=0
    sched.unassign(b2)
    assert constraint.is_satisfied(sched) is True


def test_violation_in_one_program_fails_whole_schedule():
    """A cap breach in one program fails is_satisfied even when all other programs pass."""
    constraint = CollisionConstraint(k=0)
    a1 = _elective_course("A1", "83101")
    a2 = _elective_course("A2", "83101")
    b1 = _elective_course("B1", "83102")
    b2 = _elective_course("B2", "83102")
    sched = _schedule(
        (a1, date(2026, 1, 1)),
        (a2, date(2026, 1, 2)),
        (b1, date(2026, 1, 3)),
        (b2, date(2026, 1, 3)),
    )
    assert constraint.is_satisfied(sched) is False


# ---------------------------------------------------------------------------
# Year is not part of the grouping key
# ---------------------------------------------------------------------------

def test_year_does_not_isolate_elective_counts():
    """
    Year-1 and year-2 electives in the same program count toward the same
    daily cap - the grouping key is (program_id, date), not (program_id, year, date).
    """
    constraint = CollisionConstraint(k=0)
    e_year1 = _elective_course("E1", "83101", year=1)
    e_year2 = _elective_course("E2", "83101", year=2)
    sched = _schedule(
        # different year, same program → still 2 > K=0
        (e_year1, date(2026, 1, 5)),
        (e_year2, date(2026, 1, 5)),  
    )
    assert constraint.is_satisfied(sched) is False


# ---------------------------------------------------------------------------
# Mixed elective/ obligatory requirements on the same course
# ---------------------------------------------------------------------------

def test_course_elective_in_one_program_obligatory_in_another():
    """
    A course with Elective in program A and Obligatory in program B must count
    only toward A's elective cap.  Adding a second elective for A breaches K=1
    for A, but B remains at 0 electives, so removing the extra elective fixes it.
    """
    constraint = CollisionConstraint(k=0)

    # This course is Elective for 83101, Obligatory for 83102
    shared = Course("Shared", "SH1", "Prof", Evaluation.Exam)
    shared.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Elective))
    shared.add_requirement(ProgramRequirement("83102", 1, Semester.FALL, ReqType.Obligatory))

    e2 = _elective_course("E2", "83101")

    # shared alone: A has 1 elective (== K), B has 0 electives → passes
    sched = _schedule((shared, date(2026, 1, 10)))
    assert constraint.is_satisfied(sched) is True

    # Add e2: A now has 2 electives (> K=0) → fails; B still has 0 → not the cause
    sched.assign(e2, date(2026, 1, 10))
    assert constraint.is_satisfied(sched) is False


# ---------------------------------------------------------------------------
# k = 0 edge case
# ---------------------------------------------------------------------------

def test_k_zero_allows_single_elective():
    """With k=0, one elective is allowed because it creates 0 conflicts."""
    constraint = CollisionConstraint(k=0)
    e1 = _elective_course("E1", "83101")
    sched = _schedule((e1, date(2026, 1, 5)))
    assert constraint.is_satisfied(sched) is True


def test_k_zero_fails_when_two_electives_share_cell():
    """With k=0, two electives in the same cell create 1 conflict and must fail."""
    constraint = CollisionConstraint(k=0)
    e1 = _elective_course("E1", "83101")
    e2 = _elective_course("E2", "83101")
    sched = _schedule(
        (e1, date(2026, 1, 5)),
        (e2, date(2026, 1, 5)),
    )
    assert constraint.is_satisfied(sched) is False
