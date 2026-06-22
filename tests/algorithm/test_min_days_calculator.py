from datetime import date
from math import inf

from src.algorithm.scoring.min_days_calculator import MinDaysCalculator
from tests.algorithm.constraint_helpers import (
    make_obligatory_course as _obligatory,
    make_elective_course as _elective,
    make_schedule as _schedule,
)

PROG_A = "83101"
PROG_B = "83102"


def test_field_name_returns_min_days_required():
    """Verify that field_name maps to the correct scores database column."""
    assert MinDaysCalculator().field_name() == "min_days_required"


def test_empty_schedule_returns_infinity():
    """Verify that an empty schedule has no measurable obligatory gap."""
    assert MinDaysCalculator().compute(_schedule()) == inf


def test_single_obligatory_exam_returns_infinity():
    """Verify that one Obligatory exam is not enough to calculate a gap."""
    c1 = _obligatory("O1", PROG_A, year=1)
    sched = _schedule((c1, date(2026, 1, 5)))

    assert MinDaysCalculator().compute(sched) == inf


def test_two_obligatory_exams_same_cohort_returns_gap():
    """Verify that two Obligatory exams in the same cohort produce their day gap."""
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _obligatory("O2", PROG_A, year=1)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 11)),
    )

    assert MinDaysCalculator().compute(sched) == 10.0


def test_three_obligatory_exams_returns_smallest_consecutive_gap():
    """Verify that the calculator returns the minimum consecutive gap, not the span."""
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _obligatory("O2", PROG_A, year=1)
    c3 = _obligatory("O3", PROG_A, year=1)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 6)),
        (c3, date(2026, 1, 21)),
    )

    assert MinDaysCalculator().compute(sched) == 5.0


def test_elective_courses_are_ignored():
    """Verify that Elective exams do not participate in minimum gap scoring."""
    e1 = _elective("E1", PROG_A, year=1)
    e2 = _elective("E2", PROG_A, year=1)
    sched = _schedule(
        (e1, date(2026, 1, 1)),
        (e2, date(2026, 1, 2)),
    )

    assert MinDaysCalculator().compute(sched) == inf


def test_different_years_are_separate_cohorts():
    """Verify that exams from different years do not create cross-year gaps."""
    y1 = _obligatory("O1", PROG_A, year=1)
    y2 = _obligatory("O2", PROG_A, year=2)
    sched = _schedule(
        (y1, date(2026, 1, 1)),
        (y2, date(2026, 1, 2)),
    )

    assert MinDaysCalculator().compute(sched) == inf


def test_different_programs_are_separate_cohorts():
    """Verify that exams from different programs do not create cross-program gaps."""
    a1 = _obligatory("O1", PROG_A, year=1)
    b1 = _obligatory("O2", PROG_B, year=1)
    sched = _schedule(
        (a1, date(2026, 1, 1)),
        (b1, date(2026, 1, 2)),
    )

    assert MinDaysCalculator().compute(sched) == inf


def test_global_minimum_is_taken_across_all_cohorts():
    """Verify that the final score is the smallest gap found in any cohort."""
    a1 = _obligatory("A1", PROG_A, year=1)
    a2 = _obligatory("A2", PROG_A, year=1)
    b1 = _obligatory("B1", PROG_B, year=1)
    b2 = _obligatory("B2", PROG_B, year=1)

    sched = _schedule(
        (a1, date(2026, 1, 1)),
        (a2, date(2026, 1, 11)),  # gap 10
        (b1, date(2026, 1, 5)),
        (b2, date(2026, 1, 8)),   # gap 3
    )

    assert MinDaysCalculator().compute(sched) == 3.0


def test_duplicate_same_day_dates_are_deduplicated():
    """Verify that multiple Obligatory exams on the same date are treated as one date."""
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _obligatory("O2", PROG_A, year=1)
    c3 = _obligatory("O3", PROG_A, year=1)

    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 1)),
        (c3, date(2026, 1, 6)),
    )

    assert MinDaysCalculator().compute(sched) == 5.0