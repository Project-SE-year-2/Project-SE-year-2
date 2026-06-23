from datetime import date

from tests.algorithm.constraint_helpers import (
    make_obligatory_course as _obligatory,
    make_elective_course as _elective,
    make_schedule as _schedule,
)
from src.algorithm.constraints.partial_all_gap_constraint import PartialAllGapConstraint
from src.algorithm.constraints.partial_collision_constraint import PartialCollisionConstraint

PROG_A = "83101"

def test_partial_all_gap_rejects_gap_smaller_than_k():
    """Verify that PartialAllGapConstraint prunes cohorts with exam gaps below K."""
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _elective("E1", PROG_A, year=1)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 3)),
    )

    assert PartialAllGapConstraint(k=3).is_still_valid(sched) is False


def test_partial_all_gap_accepts_gap_equal_to_k():
    """Verify that a gap exactly equal to K is allowed."""
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _elective("E1", PROG_A, year=1)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 4)),
    )

    assert PartialAllGapConstraint(k=3).is_still_valid(sched) is True


def test_partial_collision_k_two_allows_three_electives_same_cell():
    """Verify that K counts conflicts, so 3 electives create 2 conflicts and pass for K=2."""
    e1 = _elective("E1", PROG_A)
    e2 = _elective("E2", PROG_A)
    e3 = _elective("E3", PROG_A)

    sched = _schedule(
        (e1, date(2026, 1, 1)),
        (e2, date(2026, 1, 1)),
        (e3, date(2026, 1, 1)),
    )

    assert PartialCollisionConstraint(k=2).is_still_valid(sched) is True


def test_partial_collision_k_two_rejects_four_electives_same_cell():
    """Verify that 4 electives create 3 conflicts and fail for K=2."""
    e1 = _elective("E1", PROG_A)
    e2 = _elective("E2", PROG_A)
    e3 = _elective("E3", PROG_A)
    e4 = _elective("E4", PROG_A)

    sched = _schedule(
        (e1, date(2026, 1, 1)),
        (e2, date(2026, 1, 1)),
        (e3, date(2026, 1, 1)),
        (e4, date(2026, 1, 1)),
    )

    assert PartialCollisionConstraint(k=2).is_still_valid(sched) is False