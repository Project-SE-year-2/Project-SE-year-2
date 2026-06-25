from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType
from typing import Protocol

from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.constraints.partial_constraint_checker import PartialConstraintChecker
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.enums import TimeSlot
from src.models.room import Room


class DomainProvider(Protocol):
    """Provides valid assignment candidates for a course in the current partial schedule."""

    def candidates_for(
        self,
        course: Course,
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        partial_constraint_checker: PartialConstraintChecker | None = None,
    ) -> list:
        ...


class PlacementFactory(Protocol):
    """Converts a domain candidate into the value stored on ExamSchedule."""

    def create(self, candidate):
        ...


class FeasibilityChecker(Protocol):
    """Checks whether every remaining course still has at least one candidate."""

    def validate_courses(self, courses: list[Course]) -> tuple[bool, str]:
        ...

    def has_viable_assignment(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        partial_constraint_checker: PartialConstraintChecker | None = None,
    ) -> bool:
        ...


@dataclass(frozen=True)
class SchedulingComponents:
    """The selected solver components for one scheduling mode."""

    domain_provider: DomainProvider
    placement_factory: PlacementFactory
    feasibility_checker: FeasibilityChecker
    room_allocator: "RoomAllocator | None" = None


class DateOnlyPlacementFactory:
    """Stores legacy date candidates directly on ExamSchedule."""

    def create(self, candidate: DateType) -> DateType:
        return candidate


class RoomPlacementFactory:
    """Stores room-aware ExamPlacement candidates on ExamSchedule."""

    def create(self, candidate: ExamPlacement) -> ExamPlacement:
        return candidate


class DateOnlyDomainProvider:
    """Builds the date-only candidate domain used by the existing solver."""

    def candidates_for(
        self,
        course: Course,
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        partial_constraint_checker: PartialConstraintChecker | None = None,
    ) -> list[DateType]:
        valid: list[DateType] = []
        for exam_date in period.getAvailableDates():
            if not constraint_validator.canAssign(course, exam_date, partial):
                continue
            if not self._passes_partial_constraints(
                course, exam_date, partial, partial_constraint_checker
            ):
                continue
            valid.append(exam_date)
        return valid

    @staticmethod
    def _passes_partial_constraints(
        course: Course,
        candidate,
        partial: ExamSchedule,
        partial_constraint_checker: PartialConstraintChecker | None,
    ) -> bool:
        if partial_constraint_checker is None:
            return True

        partial.assign(course, candidate)
        is_valid = partial_constraint_checker.is_valid_partial(partial)
        partial.unassign(course)
        return is_valid


class RoomAllocator:
    """Allocates a non-overlapping set of rooms for one exam placement."""

    def __init__(self, rooms: list[Room]) -> None:
        if not rooms:
            raise ValueError("Room scheduling requires at least one room.")
        self._rooms = tuple(sorted(rooms, key=lambda room: (room.building, room.room_id)))

    def allocate(
        self,
        course: Course,
        exam_date: DateType,
        time_slot: TimeSlot,
        partial: ExamSchedule,
    ) -> tuple[Room, ...] | None:
        available = [
            room for room in self._rooms
            if not self._is_room_occupied(room, exam_date, time_slot, partial)
        ]
        required_capacity = getattr(course, "num_students", 0)
        if required_capacity <= 0:
            return None

        return self._greedy_allocate(available, required_capacity)

    @staticmethod
    def _greedy_allocate(
        available: list[Room],
        required_capacity: int,
    ) -> tuple[Room, ...] | None:
        """
        Allocate rooms without enumerating every possible combination.

        Prefer the smallest single room that fits. If no single room is large
        enough, accumulate larger rooms first until the capacity requirement is met.
        """
        if not available:
            return None
        # Sort available rooms by capacity, then building, then room_id for deterministic selection.
        by_capacity = sorted(
            available,
            key=lambda room: (room.capacity, room.building, room.room_id),
        )
        for room in by_capacity:
            if room.capacity >= required_capacity:
                return (room,)

        selected: list[Room] = []
        total_capacity = 0
        for room in reversed(by_capacity):
            selected.append(room)
            total_capacity += room.capacity
            if total_capacity >= required_capacity:
                return tuple(
                    sorted(selected, key=lambda item: (item.building, item.room_id))
                )
        return None

    @property
    def has_room_data(self) -> bool:
        """Return True when at least one room is available for allocation."""
        return bool(self._rooms)

    @property
    def total_capacity(self) -> int:
        """Return total capacity across all rooms known to the allocator."""
        return sum(room.capacity for room in self._rooms)

    @staticmethod
    def _is_room_occupied(
        room: Room,
        exam_date: DateType,
        time_slot: TimeSlot,
        partial: ExamSchedule,
    ) -> bool:
        for _, _, placement in partial.iter_placements():
            if placement.date == exam_date and placement.time_slot == time_slot:
                if room in placement.rooms:
                    return True
        return False


class RoomSchedulingDomainProvider:
    """Builds room-aware placement candidates when room scheduling is enabled."""

    def __init__(self, room_allocator: RoomAllocator) -> None:
        self._room_allocator = room_allocator

    def candidates_for(
        self,
        course: Course,
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        partial_constraint_checker: PartialConstraintChecker | None = None,
    ) -> list[ExamPlacement]:
        valid: list[ExamPlacement] = []
        for exam_date in period.getAvailableDates():
            if not constraint_validator.canAssign(course, exam_date, partial):
                continue
            for time_slot in TimeSlot:
                rooms = self._room_allocator.allocate(course, exam_date, time_slot, partial)
                if rooms is None:
                    continue
                placement = ExamPlacement(exam_date, time_slot, rooms)
                if not DateOnlyDomainProvider._passes_partial_constraints(
                    course, placement, partial, partial_constraint_checker
                ):
                    continue
                valid.append(placement)
        return valid


class DomainFeasibilityChecker:
    """Shared feasibility checker driven by the selected domain provider."""

    def __init__(self, domain_provider: DomainProvider) -> None:
        self._domain_provider = domain_provider

    def has_viable_assignment(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        partial_constraint_checker: PartialConstraintChecker | None = None,
    ) -> bool:
        for course in remaining:
            candidates = self._domain_provider.candidates_for(
                course,
                partial,
                period,
                constraint_validator,
                partial_constraint_checker,
            )
            if not candidates:
                return False
        return True

    def validate_courses(self, courses: list[Course]) -> tuple[bool, str]:
        """Validate mode-specific course requirements before solver search starts."""
        return True, ""


class DateOnlyFeasibilityChecker(DomainFeasibilityChecker):
    """Feasibility checker for date-only scheduling mode."""


class RoomSchedulingFeasibilityChecker(DomainFeasibilityChecker):
    """Feasibility checker for room-aware scheduling mode."""

    def __init__(self, domain_provider: DomainProvider, room_allocator: RoomAllocator) -> None:
        super().__init__(domain_provider)
        self._room_allocator = room_allocator

    def validate_courses(self, courses: list[Course]) -> tuple[bool, str]:
        """Validate room-mode data and capacity before any backtracking search."""
        if not self._room_allocator.has_room_data:
            return False, "Room scheduling requires room data."

        total_capacity = self._room_allocator.total_capacity
        for course in courses:
            num_students = getattr(course, "num_students", 0)
            if num_students <= 0:
                return False, (
                    f"Course '{course.course_id}' must have a positive student count "
                    "for room scheduling."
                )
            if num_students > total_capacity:
                return False, (
                    f"Course '{course.course_id}' has {num_students} students, "
                    f"but total room capacity is only {total_capacity}."
                )
        return True, ""

    def has_viable_assignment(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        partial_constraint_checker: PartialConstraintChecker | None = None,
    ) -> bool:
        is_valid, _ = self.validate_courses(remaining)
        if not is_valid:
            return False
        return super().has_viable_assignment(
            remaining,
            partial,
            period,
            constraint_validator,
            partial_constraint_checker,
        )


class SchedulingModeFactory:
    """Composes solver components according to room_scheduling_enabled."""

    @staticmethod
    def create(
        settings: ConstraintSettings | None = None,
        rooms: list[Room] | None = None,
    ) -> SchedulingComponents:
        active_settings = settings or ConstraintSettings()

        if not active_settings.room_scheduling_enabled:
            domain_provider = DateOnlyDomainProvider()
            return SchedulingComponents(
                domain_provider=domain_provider,
                placement_factory=DateOnlyPlacementFactory(),
                feasibility_checker=DateOnlyFeasibilityChecker(domain_provider),
            )

        if not rooms:
            raise ValueError("Room scheduling is enabled, but no room data was provided.")

        room_allocator = RoomAllocator(rooms)
        domain_provider = RoomSchedulingDomainProvider(room_allocator)
        return SchedulingComponents(
            domain_provider=domain_provider,
            placement_factory=RoomPlacementFactory(),
            feasibility_checker=RoomSchedulingFeasibilityChecker(domain_provider, room_allocator),
            room_allocator=room_allocator,
        )
