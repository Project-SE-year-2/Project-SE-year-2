"""
Tests for RoomAndSlotConstraint and its integration into ConstraintChecker.

Two rules are verified:
  1. Room exclusivity  — the same room cannot appear in two placements that share
                         the same (date, time_slot).
  2. Capacity          — each placement's total room capacity must >= num_students.

Cross-cutting invariant: when no placement carries room data (date-only mode)
the constraint must return True without raising.
"""
from datetime import date

import pytest

from src.algorithm.constraints.constraint_checker import ConstraintChecker
from src.algorithm.constraints.room_and_slot_constraint import RoomAndSlotConstraint
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.enums import Evaluation, Moed, Semester, TimeSlot
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.room import Room


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PERIOD = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 31))

ROOM_A = Room("101", "1", 50)
ROOM_B = Room("102", "1", 50)
ROOM_C = Room("103", "1", 30)


def _course(course_id: str = "C1", students: int = 20) -> Course:
    return Course(f"Course {course_id}", course_id, "Prof", Evaluation.Exam, students)


def _schedule(*assignments: tuple[Course, ExamPlacement]) -> ExamSchedule:
    sched = ExamSchedule(PERIOD)
    for course, placement in assignments:
        sched.assign(course, placement)
    return sched


def _placement(
    exam_date: date,
    slot: TimeSlot,
    rooms: tuple[Room, ...],
) -> ExamPlacement:
    return ExamPlacement(exam_date, slot, rooms)


# ---------------------------------------------------------------------------
# Date-only mode bypass
# ---------------------------------------------------------------------------

def test_date_only_placement_is_not_room_based_and_passes():
    """
    When all placements are date-only (no rooms), the constraint must return
    True.  This ensures date-only mode is completely unaffected.
    """
    constraint = RoomAndSlotConstraint()
    sched = ExamSchedule(PERIOD)
    sched.assign(_course(), date(2026, 1, 5))  # raw date — auto-wrapped to date_only
    assert constraint.is_satisfied(sched) is True


def test_empty_schedule_passes():
    """An empty schedule has nothing to violate."""
    constraint = RoomAndSlotConstraint()
    assert constraint.is_satisfied(ExamSchedule(PERIOD)) is True


# ---------------------------------------------------------------------------
# Room exclusivity
# ---------------------------------------------------------------------------

def test_two_exams_different_rooms_same_slot_passes():
    """Two exams in the same slot but different rooms must not conflict."""
    constraint = RoomAndSlotConstraint()
    c1, c2 = _course("C1", 20), _course("C2", 20)
    sched = _schedule(
        (c1, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
        (c2, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_B,))),
    )
    assert constraint.is_satisfied(sched) is True


def test_two_exams_same_room_different_slots_passes():
    """The same room used in MORNING and AFTERNOON on the same date is fine."""
    constraint = RoomAndSlotConstraint()
    c1, c2 = _course("C1", 20), _course("C2", 20)
    sched = _schedule(
        (c1, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
        (c2, _placement(date(2026, 1, 5), TimeSlot.AFTERNOON, (ROOM_A,))),
    )
    assert constraint.is_satisfied(sched) is True


def test_two_exams_same_room_different_dates_passes():
    """The same room used on different dates is always allowed."""
    constraint = RoomAndSlotConstraint()
    c1, c2 = _course("C1", 20), _course("C2", 20)
    sched = _schedule(
        (c1, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
        (c2, _placement(date(2026, 1, 6), TimeSlot.MORNING, (ROOM_A,))),
    )
    assert constraint.is_satisfied(sched) is True


def test_duplicate_room_in_same_date_and_slot_fails():
    """Two exams assigned to the same room at the same date+slot must be rejected."""
    constraint = RoomAndSlotConstraint()
    c1, c2 = _course("C1", 20), _course("C2", 20)
    sched = _schedule(
        (c1, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
        (c2, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
    )
    assert constraint.is_satisfied(sched) is False


def test_multi_room_placement_shares_one_room_with_another_exam_fails():
    """
    When a multi-room placement shares even one room with another exam in the
    same slot, exclusivity is violated.
    """
    constraint = RoomAndSlotConstraint()
    c1, c2 = _course("C1", 70), _course("C2", 20)
    sched = _schedule(
        # C1 uses ROOM_A + ROOM_B together
        (c1, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A, ROOM_B))),
        # C2 tries to use ROOM_B in the same slot
        (c2, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_B,))),
    )
    assert constraint.is_satisfied(sched) is False


# ---------------------------------------------------------------------------
# Capacity
# ---------------------------------------------------------------------------

def test_room_capacity_exactly_meets_student_count_passes():
    """Capacity equal to student count is sufficient."""
    constraint = RoomAndSlotConstraint()
    course = _course(students=50)
    sched = _schedule(
        (course, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
    )
    assert constraint.is_satisfied(sched) is True


def test_room_capacity_exceeds_student_count_passes():
    """A room larger than needed is fine."""
    constraint = RoomAndSlotConstraint()
    course = _course(students=10)
    sched = _schedule(
        (course, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
    )
    assert constraint.is_satisfied(sched) is True


def test_room_capacity_below_student_count_fails():
    """A room that cannot fit all students must cause the constraint to fail."""
    constraint = RoomAndSlotConstraint()
    course = _course(students=40)
    sched = _schedule(
        # ROOM_C has capacity 30 — too small for 40 students
        (course, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_C,))),
    )
    assert constraint.is_satisfied(sched) is False


def test_multi_room_combined_capacity_meets_student_count_passes():
    """Combined capacity of multiple rooms is summed correctly."""
    constraint = RoomAndSlotConstraint()
    course = _course(students=75)
    sched = _schedule(
        # ROOM_A(50) + ROOM_C(30) = 80 >= 75
        (course, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A, ROOM_C))),
    )
    assert constraint.is_satisfied(sched) is True


def test_multi_room_combined_capacity_below_student_count_fails():
    """Even with two rooms, if total capacity is insufficient the schedule is invalid."""
    constraint = RoomAndSlotConstraint()
    course = _course(students=90)
    sched = _schedule(
        # ROOM_A(50) + ROOM_C(30) = 80 < 90
        (course, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A, ROOM_C))),
    )
    assert constraint.is_satisfied(sched) is False


def test_course_with_zero_students_skips_capacity_check():
    """
    A course with num_students=0 means the count is unknown; the capacity
    rule should be skipped rather than incorrectly failing.
    """
    constraint = RoomAndSlotConstraint()
    course = _course(students=0)
    sched = _schedule(
        (course, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_C,))),
    )
    assert constraint.is_satisfied(sched) is True


# ---------------------------------------------------------------------------
# ConstraintChecker integration
# ---------------------------------------------------------------------------

def test_constraint_checker_adds_room_constraint_when_enabled():
    """ConstraintChecker must include RoomAndSlotConstraint when room_scheduling_enabled=True."""
    settings = ConstraintSettings(room_scheduling_enabled=True)
    checker = ConstraintChecker(settings)

    room_constraints = [c for c in checker._constraints if isinstance(c, RoomAndSlotConstraint)]
    assert len(room_constraints) == 1


def test_constraint_checker_omits_room_constraint_when_disabled():
    """ConstraintChecker must NOT add RoomAndSlotConstraint in date-only mode."""
    settings = ConstraintSettings(room_scheduling_enabled=False)
    checker = ConstraintChecker(settings)

    room_constraints = [c for c in checker._constraints if isinstance(c, RoomAndSlotConstraint)]
    assert len(room_constraints) == 0


def test_constraint_checker_rejects_duplicate_room_via_is_valid():
    """End-to-end: ConstraintChecker.is_valid() returns False on a room conflict."""
    settings = ConstraintSettings(room_scheduling_enabled=True)
    checker = ConstraintChecker(settings)

    c1, c2 = _course("C1", 20), _course("C2", 20)
    sched = _schedule(
        (c1, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
        (c2, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
    )
    assert checker.is_valid(sched) is False


def test_constraint_checker_accepts_valid_room_schedule_via_is_valid():
    """End-to-end: ConstraintChecker.is_valid() returns True when no rules are broken."""
    settings = ConstraintSettings(room_scheduling_enabled=True)
    checker = ConstraintChecker(settings)

    c1, c2 = _course("C1", 20), _course("C2", 20)
    sched = _schedule(
        (c1, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_A,))),
        (c2, _placement(date(2026, 1, 5), TimeSlot.MORNING, (ROOM_B,))),
    )
    assert checker.is_valid(sched) is True


def test_constraint_checker_date_only_mode_unaffected_by_room_constraint():
    """
    In date-only mode (room_scheduling_enabled=False) the room constraint is absent
    and must not affect schedules that only carry date placements.
    """
    settings = ConstraintSettings(room_scheduling_enabled=False)
    checker = ConstraintChecker(settings)

    sched = ExamSchedule(PERIOD)
    sched.assign(_course("C1"), date(2026, 1, 5))
    sched.assign(_course("C2"), date(2026, 1, 5))

    assert checker.is_valid(sched) is True
