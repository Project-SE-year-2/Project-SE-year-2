"""
Tests for CollisionCalculator.

CollisionCalculator counts the total number of elective date collisions across
the entire schedule.  For each (program_id, date) cell with N elective exams,
max(0, N - 1) conflicts are recorded.  Obligatory courses are invisible to
this metric; the grouping key is program_id alone (not year), matching the
logic of CollisionConstraint.

Covers:
  - field_name returns 'elective_conflicts'
  - empty schedule returns 0
  - single elective on any day returns 0 (no one to collide with)
  - two electives on different days returns 0
  - two electives in different programs on the same day returns 0
  - obligatory courses on the same day are not counted
  - two electives same program same day → count = 1
  - three electives same program same day → count = 2
  - conflicts accumulate across multiple days
  - conflicts accumulate across multiple programs
  - mixed obligatory + elective: only electives count
  - year does not isolate grouping (program_id alone, not year)
  - multi-requirement course: counts only toward programs where it is Elective
  - course that is Elective in both programs counts toward both cells
"""

from datetime import date

from src.models.course import Course
from src.models.enums import Evaluation, Semester, ReqType
from src.models.program_requirement import ProgramRequirement
from src.algorithm.scoring.collision_calculator import CollisionCalculator
from tests.algorithm.constraint_helpers import (
    make_elective_course as _elective,
    make_obligatory_course as _obligatory,
    make_schedule as _schedule,
)

PROG_A = "83101"
PROG_B = "83102"


# ---------------------------------------------------------------------------
# field_name
# ---------------------------------------------------------------------------

def test_field_name_returns_elective_conflicts():
    assert CollisionCalculator().field_name() == 'elective_conflicts'


# ---------------------------------------------------------------------------
# Empty / zero-conflict cases
# ---------------------------------------------------------------------------

def test_empty_schedule_returns_zero():
    assert CollisionCalculator().compute(_schedule()) == 0


def test_single_elective_returns_zero():
    c1 = _elective("E1", PROG_A)
    assert CollisionCalculator().compute(_schedule((c1, date(2026, 1, 5)))) == 0


def test_two_electives_different_days_no_conflict():
    c1 = _elective("E1", PROG_A)
    c2 = _elective("E2", PROG_A)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 6)),
    )
    assert CollisionCalculator().compute(sched) == 0


def test_electives_in_different_programs_same_day_no_conflict():
    """Each program gets its own cell — no collision between programs."""
    c1 = _elective("E1", PROG_A)
    c2 = _elective("E2", PROG_B)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert CollisionCalculator().compute(sched) == 0


def test_obligatory_courses_not_counted():
    """Obligatory courses on the same day must not contribute to the metric."""
    o1 = _obligatory("O1", PROG_A)
    o2 = _obligatory("O2", PROG_A)
    sched = _schedule(
        (o1, date(2026, 1, 5)),
        (o2, date(2026, 1, 5)),
    )
    assert CollisionCalculator().compute(sched) == 0


# ---------------------------------------------------------------------------
# Conflict counting
# ---------------------------------------------------------------------------

def test_two_electives_same_program_same_day_counts_one():
    c1 = _elective("E1", PROG_A)
    c2 = _elective("E2", PROG_A)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
    )
    assert CollisionCalculator().compute(sched) == 1


def test_three_electives_same_program_same_day_counts_two():
    c1 = _elective("E1", PROG_A)
    c2 = _elective("E2", PROG_A)
    c3 = _elective("E3", PROG_A)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
        (c3, date(2026, 1, 5)),
    )
    assert CollisionCalculator().compute(sched) == 2


def test_conflicts_accumulate_across_multiple_days():
    """Two separate conflict cells (2 electives each) → total = 2."""
    c1 = _elective("E1", PROG_A)
    c2 = _elective("E2", PROG_A)
    c3 = _elective("E3", PROG_A)
    c4 = _elective("E4", PROG_A)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
        (c3, date(2026, 1, 10)),
        (c4, date(2026, 1, 10)),
    )
    assert CollisionCalculator().compute(sched) == 2


def test_conflicts_accumulate_across_multiple_programs():
    """Each program contributes its own collision on the same day → total = 2."""
    c1 = _elective("E1", PROG_A)
    c2 = _elective("E2", PROG_A)
    c3 = _elective("E3", PROG_B)
    c4 = _elective("E4", PROG_B)
    sched = _schedule(
        (c1, date(2026, 1, 5)),
        (c2, date(2026, 1, 5)),
        (c3, date(2026, 1, 5)),
        (c4, date(2026, 1, 5)),
    )
    assert CollisionCalculator().compute(sched) == 2


def test_mixed_obligatory_and_elective_only_electives_count():
    """Obligatory + two electives on the same day for the same program → 1 conflict."""
    obl = _obligatory("O1", PROG_A)
    el1 = _elective("E1", PROG_A)
    el2 = _elective("E2", PROG_A)
    sched = _schedule(
        (obl, date(2026, 1, 5)),
        (el1, date(2026, 1, 5)),
        (el2, date(2026, 1, 5)),
    )
    assert CollisionCalculator().compute(sched) == 1


# ---------------------------------------------------------------------------
# Year is not part of the grouping key
# ---------------------------------------------------------------------------

def test_year_does_not_isolate_elective_counts():
    """
    Year-1 and year-2 electives in the same program both count toward the same
    (program_id, date) cell — same behaviour as CollisionConstraint.
    """
    e1 = _elective("E1", PROG_A, year=1)
    e2 = _elective("E2", PROG_A, year=2)
    sched = _schedule(
        (e1, date(2026, 1, 5)),
        (e2, date(2026, 1, 5)),
    )
    assert CollisionCalculator().compute(sched) == 1


# ---------------------------------------------------------------------------
# Multi-requirement course
# ---------------------------------------------------------------------------

def test_course_elective_in_one_program_obligatory_in_another():
    """
    A course with Elective for program A and Obligatory for program B must
    count only toward A's cell, not B's.
    """
    shared = Course("Shared", "SH1", "Prof", Evaluation.Exam)
    shared.add_requirement(ProgramRequirement(PROG_A, 1, Semester.FALL, ReqType.Elective))
    shared.add_requirement(ProgramRequirement(PROG_B, 1, Semester.FALL, ReqType.Obligatory))

    e2 = _elective("E2", PROG_A)

    # shared alone: A has 1 elective → no conflict
    sched = _schedule((shared, date(2026, 1, 10)))
    assert CollisionCalculator().compute(sched) == 0

    # Add a second elective for A on the same day → 1 conflict
    sched.assign(e2, date(2026, 1, 10))
    assert CollisionCalculator().compute(sched) == 1


def test_course_elective_in_both_programs_counts_for_both():
    """
    A course that is Elective in both program A and program B on the same day
    as a second elective in each program causes a conflict in each program.
    """
    # shared is Elective in both A and B
    shared = Course("Shared", "SH1", "Prof", Evaluation.Exam)
    shared.add_requirement(ProgramRequirement(PROG_A, 1, Semester.FALL, ReqType.Elective))
    shared.add_requirement(ProgramRequirement(PROG_B, 1, Semester.FALL, ReqType.Elective))

    e_a = _elective("E_A", PROG_A)
    e_b = _elective("E_B", PROG_B)

    sched = _schedule(
        (shared, date(2026, 1, 10)),
        (e_a, date(2026, 1, 10)),
        (e_b, date(2026, 1, 10)),
    )
    # PROG_A cell: shared + e_a → 2 electives → 1 conflict
    # PROG_B cell: shared + e_b → 2 electives → 1 conflict
    assert CollisionCalculator().compute(sched) == 2
