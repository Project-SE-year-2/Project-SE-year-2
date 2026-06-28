from datetime import date
from unittest.mock import MagicMock

from src.algorithm.scheduling_mode_factory import (
    DateOnlyDomainProvider,
    DateOnlyFeasibilityChecker,
    RoomAllocator,
    RoomPlacementFactory,
    RoomSchedulingDomainProvider,
    RoomSchedulingFeasibilityChecker,
)
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.enums import Evaluation, Moed, Semester, TimeSlot
from src.models.room import Room


def _course(course_id: str, students: int = 30) -> Course:
    course = Course(f"Course {course_id}", course_id, "Dr Tester", Evaluation.Exam)
    course.num_students = students
    return course


def _period() -> ExamPeriod:
    return ExamPeriod(
        Semester.FALL,
        Moed.Aleph,
        date(2026, 1, 1),
        date(2026, 1, 1),
    )


def _validator_accepting_all():
    validator = MagicMock()
    validator.canAssign.return_value = True
    return validator


def test_room_forward_checking_returns_false_when_candidates_have_no_available_room():
    """Room mode must reject a branch when every candidate exists but room allocation fails."""
    room = Room("101", "A", 30)
    allocator = RoomAllocator([room])
    domain_provider = RoomSchedulingDomainProvider()
    placement_factory = RoomPlacementFactory(allocator)

    checker = RoomSchedulingFeasibilityChecker(
        domain_provider,
        placement_factory,
        allocator,
    )

    partial = ExamSchedule(_period())

    # Occupy the only room in every time slot on the only available date.
    for idx, slot in enumerate(TimeSlot):
        blocker = _course(f"B{idx}", 10)
        partial.assign(
            blocker,
            ExamPlacement.with_rooms(
                date(2026, 1, 1),
                slot,
                (room,),
            ),
        )

    remaining_course = _course("C1", 30)

    assert checker.has_viable_assignment(
        [remaining_course],
        partial,
        _period(),
        _validator_accepting_all(),
    ) is False


def test_room_forward_checking_returns_true_when_one_candidate_can_allocate_room():
    """Room mode must keep a branch alive when at least one candidate can allocate rooms."""
    room = Room("101", "A", 30)
    allocator = RoomAllocator([room])
    domain_provider = RoomSchedulingDomainProvider()
    placement_factory = RoomPlacementFactory(allocator)

    checker = RoomSchedulingFeasibilityChecker(
        domain_provider,
        placement_factory,
        allocator,
    )

    partial = ExamSchedule(_period())
    remaining_course = _course("C1", 30)

    assert checker.has_viable_assignment(
        [remaining_course],
        partial,
        _period(),
        _validator_accepting_all(),
    ) is True


def test_room_forward_checking_does_not_mutate_partial_schedule():
    """Forward checking must only test candidates and must not assign courses into partial."""
    room = Room("101", "A", 30)
    allocator = RoomAllocator([room])
    domain_provider = RoomSchedulingDomainProvider()
    placement_factory = RoomPlacementFactory(allocator)

    checker = RoomSchedulingFeasibilityChecker(
        domain_provider,
        placement_factory,
        allocator,
    )

    partial = ExamSchedule(_period())
    before = list(partial.iter_placements())

    remaining_course = _course("C1", 30)

    checker.has_viable_assignment(
        [remaining_course],
        partial,
        _period(),
        _validator_accepting_all(),
    )

    after = list(partial.iter_placements())
    assert after == before


def test_date_only_forward_checking_behavior_is_unchanged():
    """Date-only mode must still only require at least one valid date candidate."""
    domain_provider = DateOnlyDomainProvider()
    checker = DateOnlyFeasibilityChecker(domain_provider)

    partial = ExamSchedule(_period())
    remaining_course = _course("C1", 30)

    assert checker.has_viable_assignment(
        [remaining_course],
        partial,
        _period(),
        _validator_accepting_all(),
    ) is True
