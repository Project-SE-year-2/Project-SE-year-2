"""
Tests for the zero-allocation iterators on ExamSchedule and their use in
partial constraint checkers.

Background
----------
Before the fix, every partial constraint called schedule.assignments, which:
  1. Calls schedule.placements  → builds dict #1 (Course → ExamPlacement)
  2. Builds dict #2             → (Course → date) from dict #1

Both dicts are discarded immediately after the loop.  Partial constraints run
for EVERY candidate at EVERY backtracking node, so these are the hottest
allocations in the solver.

After the fix, ExamSchedule exposes two generators:
  iter_assignments()       → yields (course, date) directly from _store
  iter_assignment_dates()  → yields date directly from _store

These tests verify:
  1. iter_assignments() yields the same data as assignments.items()
  2. iter_assignment_dates() yields the same data as assignments.values()
  3. The four partial constraints produce correct accept/reject decisions
     (regression: the refactor must not change semantics)
  4. The four partial constraints iterate via the new generators (no .assignments call)
"""

from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from src.algorithm.constraints.partial_all_gap_constraint import PartialAllGapConstraint
from src.algorithm.constraints.partial_collision_constraint import PartialCollisionConstraint
from src.algorithm.constraints.partial_daily_cap_constraint import PartialDailyCapConstraint
from src.algorithm.constraints.partial_mandatory_gap_constraint import PartialMandatoryGapConstraint
from src.models.course import Course
from src.models.enums import Evaluation, Moed, ReqType, Semester
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _period(start: date = date(2026, 1, 1), end: date = date(2026, 1, 10)) -> ExamPeriod:
    p = ExamPeriod(Semester.FALL, Moed.Aleph, start, end)
    p.possible_dates = [date(2026, 1, d) for d in range(start.day, end.day + 1)]
    return p


def _course(cid: str, students: int = 10) -> Course:
    return Course(f"Course {cid}", cid, "Prof", Evaluation.Exam, students)


def _req(program_id: str = "P1", year: int = 1, req_type: ReqType = ReqType.Obligatory) -> ProgramRequirement:
    return ProgramRequirement(program_id, year, Semester.FALL, req_type)


def _place(schedule: ExamSchedule, course: Course, exam_date: date) -> None:
    schedule.assign(course, ExamPlacement(exam_date))


# ---------------------------------------------------------------------------
# 1. iter_assignments() — content identical to assignments.items()
# ---------------------------------------------------------------------------

class TestIterAssignments:
    """iter_assignments() must yield the same (course, date) pairs as assignments.items()."""

    def test_empty_schedule_yields_nothing(self):
        schedule = ExamSchedule(_period())
        assert list(schedule.iter_assignments()) == []

    def test_single_assignment_yields_one_pair(self):
        period = _period()
        schedule = ExamSchedule(period)
        c = _course("C1")
        d = date(2026, 1, 3)
        _place(schedule, c, d)

        pairs = list(schedule.iter_assignments())
        assert len(pairs) == 1
        assert pairs[0] == (c, d)

    def test_multiple_assignments_match_assignments_dict(self):
        period = _period()
        schedule = ExamSchedule(period)
        courses = [_course(f"C{i}") for i in range(5)]
        days = [date(2026, 1, i + 1) for i in range(5)]
        for c, d in zip(courses, days):
            _place(schedule, c, d)

        via_iter = set(schedule.iter_assignments())
        via_dict = set(schedule.assignments.items())
        assert via_iter == via_dict

    def test_unassigned_course_not_yielded(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c2 = _course("C2")
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 2))
        schedule.unassign(c2)

        courses_yielded = [c for c, _ in schedule.iter_assignments()]
        assert c1 in courses_yielded
        assert c2 not in courses_yielded

    def test_yields_same_date_as_placement_dot_date(self):
        period = _period()
        schedule = ExamSchedule(period)
        c = _course("C1")
        d = date(2026, 1, 5)
        schedule.assign(c, ExamPlacement(d))

        pairs = list(schedule.iter_assignments())
        assert pairs == [(c, d)]


# ---------------------------------------------------------------------------
# 2. iter_assignment_dates() — content identical to assignments.values()
# ---------------------------------------------------------------------------

class TestIterAssignmentDates:
    """iter_assignment_dates() must yield the same dates as assignments.values()."""

    def test_empty_schedule_yields_nothing(self):
        assert list(ExamSchedule(_period()).iter_assignment_dates()) == []

    def test_dates_match_assignments_values(self):
        period = _period()
        schedule = ExamSchedule(period)
        courses = [_course(f"C{i}") for i in range(4)]
        days = [date(2026, 1, i + 2) for i in range(4)]
        for c, d in zip(courses, days):
            _place(schedule, c, d)

        assert sorted(schedule.iter_assignment_dates()) == sorted(schedule.assignments.values())

    def test_duplicate_dates_preserved(self):
        """Two courses on the same date → date appears twice in the iterator."""
        period = _period()
        schedule = ExamSchedule(period)
        d = date(2026, 1, 3)
        _place(schedule, _course("C1"), d)
        _place(schedule, _course("C2"), d)

        dates = list(schedule.iter_assignment_dates())
        assert dates.count(d) == 2


# ---------------------------------------------------------------------------
# 3. PartialAllGapConstraint — correctness
# ---------------------------------------------------------------------------

class TestPartialAllGapConstraintCorrectness:

    def test_accepts_when_gap_satisfied(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 4))  # gap = 3 days ≥ k=3

        assert PartialAllGapConstraint(3).is_still_valid(schedule) is True

    def test_rejects_when_gap_too_small(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 2))  # gap = 1 day < k=3

        assert PartialAllGapConstraint(3).is_still_valid(schedule) is False

    def test_different_cohorts_are_independent(self):
        """Close dates in different cohorts must not cause rejection."""
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1)]
        c2 = _course("C2")
        c2.requirements = [_req("P2", 1)]  # different program
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 2))  # gap = 1 but different cohort

        assert PartialAllGapConstraint(3).is_still_valid(schedule) is True

    def test_no_dict_allocation_uses_iter_assignments(self):
        """is_still_valid must call iter_assignments(), not .assignments."""
        period = _period()
        schedule = ExamSchedule(period)
        c = _course("C1")
        c.requirements = [_req()]
        _place(schedule, c, date(2026, 1, 1))

        with patch.object(type(schedule), "assignments", new_callable=lambda: property(
            lambda self: (_ for _ in ()).throw(AssertionError("assignments called — use iter_assignments"))
        )):
            # Should not raise — constraint must use iter_assignments.
            PartialAllGapConstraint(2).is_still_valid(schedule)


# ---------------------------------------------------------------------------
# 4. PartialMandatoryGapConstraint — correctness
# ---------------------------------------------------------------------------

class TestPartialMandatoryGapConstraintCorrectness:

    def test_accepts_when_gap_satisfied(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1, ReqType.Obligatory)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1, ReqType.Obligatory)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 5))  # gap = 4 ≥ k=3

        assert PartialMandatoryGapConstraint(3).is_still_valid(schedule) is True

    def test_rejects_when_gap_too_small(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1, ReqType.Obligatory)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1, ReqType.Obligatory)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 2))  # gap = 1 < k=3

        assert PartialMandatoryGapConstraint(3).is_still_valid(schedule) is False

    def test_elective_courses_ignored(self):
        """Elective courses must not participate in the mandatory gap check."""
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1, ReqType.Elective)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1, ReqType.Elective)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 2))  # close dates but both elective

        assert PartialMandatoryGapConstraint(3).is_still_valid(schedule) is True

    def test_no_dict_allocation_uses_iter_assignments(self):
        period = _period()
        schedule = ExamSchedule(period)
        c = _course("C1")
        c.requirements = [_req()]
        _place(schedule, c, date(2026, 1, 1))

        with patch.object(type(schedule), "assignments", new_callable=lambda: property(
            lambda self: (_ for _ in ()).throw(AssertionError("assignments called — use iter_assignments"))
        )):
            PartialMandatoryGapConstraint(2).is_still_valid(schedule)


# ---------------------------------------------------------------------------
# 5. PartialDailyCapConstraint — correctness
# ---------------------------------------------------------------------------

class TestPartialDailyCapConstraintCorrectness:

    def test_accepts_when_under_cap(self):
        period = _period()
        schedule = ExamSchedule(period)
        _place(schedule, _course("C1"), date(2026, 1, 1))
        _place(schedule, _course("C2"), date(2026, 1, 2))

        assert PartialDailyCapConstraint(2).is_still_valid(schedule) is True

    def test_rejects_when_cap_exceeded(self):
        period = _period()
        schedule = ExamSchedule(period)
        _place(schedule, _course("C1"), date(2026, 1, 1))
        _place(schedule, _course("C2"), date(2026, 1, 1))
        _place(schedule, _course("C3"), date(2026, 1, 1))  # 3 on same day, cap=2

        assert PartialDailyCapConstraint(2).is_still_valid(schedule) is False

    def test_exactly_at_cap_is_valid(self):
        period = _period()
        schedule = ExamSchedule(period)
        _place(schedule, _course("C1"), date(2026, 1, 1))
        _place(schedule, _course("C2"), date(2026, 1, 1))  # 2 on same day, cap=2

        assert PartialDailyCapConstraint(2).is_still_valid(schedule) is True

    def test_no_dict_allocation_uses_iter_assignment_dates(self):
        period = _period()
        schedule = ExamSchedule(period)
        _place(schedule, _course("C1"), date(2026, 1, 1))

        with patch.object(type(schedule), "assignments", new_callable=lambda: property(
            lambda self: (_ for _ in ()).throw(AssertionError("assignments called — use iter_assignment_dates"))
        )):
            PartialDailyCapConstraint(3).is_still_valid(schedule)


# ---------------------------------------------------------------------------
# 6. PartialCollisionConstraint — correctness
# ---------------------------------------------------------------------------

class TestPartialCollisionConstraintCorrectness:

    def test_accepts_when_under_collision_cap(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1, ReqType.Elective)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1, ReqType.Elective)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 2))  # different dates

        assert PartialCollisionConstraint(1).is_still_valid(schedule) is True

    def test_rejects_when_collision_exceeds_cap(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1, ReqType.Elective)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1, ReqType.Elective)]
        c3 = _course("C3")
        c3.requirements = [_req("P1", 1, ReqType.Elective)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 1))
        _place(schedule, c3, date(2026, 1, 1))  # 3 electives same day, k=1

        assert PartialCollisionConstraint(1).is_still_valid(schedule) is False

    def test_obligatory_courses_ignored(self):
        period = _period()
        schedule = ExamSchedule(period)
        c1 = _course("C1")
        c1.requirements = [_req("P1", 1, ReqType.Obligatory)]
        c2 = _course("C2")
        c2.requirements = [_req("P1", 1, ReqType.Obligatory)]
        _place(schedule, c1, date(2026, 1, 1))
        _place(schedule, c2, date(2026, 1, 1))  # 2 obligatory same day — ignored

        assert PartialCollisionConstraint(0).is_still_valid(schedule) is True

    def test_no_dict_allocation_uses_iter_assignments(self):
        period = _period()
        schedule = ExamSchedule(period)
        c = _course("C1")
        c.requirements = [_req("P1", 1, ReqType.Elective)]
        _place(schedule, c, date(2026, 1, 1))

        with patch.object(type(schedule), "assignments", new_callable=lambda: property(
            lambda self: (_ for _ in ()).throw(AssertionError("assignments called — use iter_assignments"))
        )):
            PartialCollisionConstraint(1).is_still_valid(schedule)
