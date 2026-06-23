"""
Tests for SpreadCalculator.

SpreadCalculator computes the average calendar span (in days) of obligatory
exam blocks across all (program_id, year) cohorts. 
For each cohort the span is (max(dates) - min(dates)).days. 
Cohorts with fewer than two obligatory exams are skipped. 
Elective courses are ignored entirely.

Covers:
  - field_name returns 'span_required'
  - empty schedule returns 0
  - single obligatory exam per cohort (skipped) returns 0
  - elective courses are not counted
  - two obligatory exams in the same cohort → correct span in days
  - three obligatory exams in the same cohort → span is max minus min (not sum)
  - different cohorts (same program, different year) are tracked separately
  - average is taken across multiple cohorts
  - cohorts with only one exam are skipped when averaging
  - obligatory exams across different programs are tracked separately
  - electives before or after the obligatory window do not extend the measured span
"""

from datetime import date

from src.algorithm.scoring.spread_calculator import SpreadCalculator
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

def test_field_name_returns_span_required():
    assert SpreadCalculator().field_name() == 'span_required'


# ---------------------------------------------------------------------------
# Empty / zero cases
# ---------------------------------------------------------------------------

def test_empty_schedule_returns_zero():
    assert SpreadCalculator().compute(_schedule()) == 0


def test_single_obligatory_exam_returns_zero():
    """One exam per cohort → no span to measure → skipped → 0."""
    c1 = _obligatory("O1", PROG_A, year=1)
    sched = _schedule((c1, date(2026, 1, 5)))
    assert SpreadCalculator().compute(sched) == 0


def test_elective_courses_are_not_counted():
    """Elective courses must be completely ignored, even when two share a cohort."""
    e1 = _elective("E1", PROG_A, year=1)
    e2 = _elective("E2", PROG_A, year=1)
    sched = _schedule(
        (e1, date(2026, 1, 1)),
        (e2, date(2026, 1, 20)),
    )
    assert SpreadCalculator().compute(sched) == 0


# ---------------------------------------------------------------------------
# Span calculation
# ---------------------------------------------------------------------------

def test_two_obligatory_exams_same_cohort_correct_span():
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _obligatory("O2", PROG_A, year=1)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 11)),
    )
    assert SpreadCalculator().compute(sched) == 10


def test_three_obligatory_exams_span_is_max_minus_min():
    """The span is max - min, not the sum of consecutive gaps."""
    c1 = _obligatory("O1", PROG_A, year=1)
    c2 = _obligatory("O2", PROG_A, year=1)
    c3 = _obligatory("O3", PROG_A, year=1)
    sched = _schedule(
        (c1, date(2026, 1, 1)),
        (c2, date(2026, 1, 6)),
        (c3, date(2026, 1, 21)),
    )
    assert SpreadCalculator().compute(sched) == 20


# ---------------------------------------------------------------------------
# Multiple cohorts
# ---------------------------------------------------------------------------

def test_different_years_same_program_tracked_separately():
    """Year-1 and year-2 cohorts of the same program are independent."""
    y1_c1 = _obligatory("O1", PROG_A, year=1)
    y1_c2 = _obligatory("O2", PROG_A, year=1)
    y2_c1 = _obligatory("O3", PROG_A, year=2)
    y2_c2 = _obligatory("O4", PROG_A, year=2)
    sched = _schedule(
        (y1_c1, date(2026, 1, 1)),
        (y1_c2, date(2026, 1, 11)),
        (y2_c1, date(2026, 1, 1)),
        (y2_c2, date(2026, 1, 21)),
    )
    # Year 1 span = 10, Year 2 span = 20 → average = 15
    assert SpreadCalculator().compute(sched) == 15.0


def test_average_taken_across_multiple_cohorts():
    """Average span across two programs with different spans."""
    a1 = _obligatory("A1", PROG_A, year=1)
    a2 = _obligatory("A2", PROG_A, year=1)
    b1 = _obligatory("B1", PROG_B, year=1)
    b2 = _obligatory("B2", PROG_B, year=1)
    sched = _schedule(
        (a1, date(2026, 1, 1)),
        (a2, date(2026, 1, 11)),
        (b1, date(2026, 1, 1)),
        (b2, date(2026, 1, 31)),
    )
    # PROG_A span = 10, PROG_B span = 30 → average = 20
    assert SpreadCalculator().compute(sched) == 20.0


def test_elective_on_outer_date_does_not_extend_span():
    """
    Electives scheduled before the first or after the last obligatory exam
    must not widen the measured span - only obligatory dates count.
    """
    o1 = _obligatory("O1", PROG_A, year=1)
    o2 = _obligatory("O2", PROG_A, year=1)
    e1 = _elective("E1", PROG_A, year=1)
    e2 = _elective("E2", PROG_A, year=1)
    sched = _schedule(
        (e1, date(2026, 1, 1)),
        (o1, date(2026, 1, 10)),
        (o2, date(2026, 1, 20)),
        (e2, date(2026, 1, 30)),
    )
    # Obligatory span = 10, electives do not affect the span → average = 10
    assert SpreadCalculator().compute(sched) == 10


def test_cohort_with_single_exam_is_skipped_in_average():
    """A cohort with only one exam is excluded from the average entirely."""
    a1 = _obligatory("A1", PROG_A, year=1)
    a2 = _obligatory("A2", PROG_A, year=1)
    lone = _obligatory("B1", PROG_B, year=1)
    sched = _schedule(
        (a1, date(2026, 1, 1)),
        (a2, date(2026, 1, 21)),
        (lone, date(2026, 1, 10)),
    )
    # PROG_A span = 20, PROG_B is skipped → average = 20
    assert SpreadCalculator().compute(sched) == 20.0