from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType
from typing import Protocol

from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.constraints.partial_constraint_checker import PartialConstraintChecker
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.exam_block import ExamBlock
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.enums import TimeSlot
from src.models.room import Room


class SchedulingDomainProvider(Protocol):
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
    """
    Converts a domain candidate into an ExamPlacement stored on ExamSchedule.

    Receives the candidate (date or ExamBlock), the course being placed, and
    the current partial schedule so room-aware factories can check room
    availability.  Returns None when the candidate cannot produce a valid
    placement (e.g. no rooms are available for the requested slot), signalling
    the solver to skip it.
    """

    def create(
        self,
        candidate,
        course: Course,
        partial: ExamSchedule,
    ) -> ExamPlacement | None:
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

    domain_provider: SchedulingDomainProvider
    placement_factory: PlacementFactory
    feasibility_checker: FeasibilityChecker
    room_allocator: RoomAllocator | None = None


class DateOnlyPlacementFactory:
    """Wraps a raw date into an ExamPlacement with no time_slot or rooms."""

    def create(
        self,
        candidate: DateType,
        course: Course,
        partial: ExamSchedule,
    ) -> ExamPlacement:
        return ExamPlacement.date_only(candidate)


class RoomPlacementFactory:
    """
    Converts an ExamBlock (date + time_slot) into an ExamPlacement by allocating
    rooms via RoomAllocator.  Returns None when no rooms can be allocated, so
    the solver can skip this candidate without entering a dead branch.
    """

    def __init__(self, room_allocator: RoomAllocator) -> None:
        self._room_allocator = room_allocator

    def create(
        self,
        candidate: ExamBlock,
        course: Course,
        partial: ExamSchedule,
    ) -> ExamPlacement | None:
        rooms = self._room_allocator.allocate(
            course, candidate.date, candidate.time_slot, partial
        )
        if rooms is None:
            return None
        return ExamPlacement(candidate.date, candidate.time_slot, rooms)


def _passes_partial_constraints(
    course: Course,
    candidate,
    partial: ExamSchedule,
    partial_constraint_checker: PartialConstraintChecker | None,
) -> bool:
    """Module-level helper shared by both domain providers."""
    if partial_constraint_checker is None:
        return True

    # Partial constraints are date-based today. Room mode candidates are
    # ExamBlock objects, which are domain options rather than schedule values,
    # so only their date should be temporarily assigned to the schedule.
    partial.assign(course, _candidate_date(candidate))
    is_valid = partial_constraint_checker.is_valid_partial(partial)
    partial.unassign(course)
    return is_valid


def _candidate_date(candidate: DateType | ExamBlock) -> DateType:
    """Return the date represented by either a raw date or an ExamBlock candidate."""
    if isinstance(candidate, ExamBlock):
        return candidate.date
    return candidate


class DateOnlyDomainProvider:
    """
    Builds the date-only candidate list for the existing date-based solver.
    Candidates are plain date objects filtered by collision and partial constraints.
    """

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
            if not _passes_partial_constraints(
                course, exam_date, partial, partial_constraint_checker
            ):
                continue
            valid.append(exam_date)
        return valid


def _room_identity(room: Room) -> tuple[str, str]:
    """Return the stable physical identity of a room as (building, room_id).

    Two Room objects with the same identity refer to the same physical room
    regardless of any other attribute (e.g. capacity loaded from a different
    source).  This mirrors the occupancy key used by RoomAndSlotConstraint.
    """
    return (room.building, room.room_id)


class RoomAllocator:
    """
    Allocates a non-overlapping set of rooms for one exam placement.

    Allocation strategy (in priority order):
      1. Sliding-window  — scan contiguous runs of rooms within the SAME
         BUILDING (sorted by room_id) and pick the best window that satisfies
         capacity.  Selection priority: fewest rooms, then fewest distinct
         buildings (always 1 here), then lowest unused capacity.
      2. Greedy fallback — used when no single building has enough capacity.
         Accumulates the largest rooms across all buildings until the
         requirement is met.  This is the only path that combines rooms from
         different buildings.

    Occupancy checks compare rooms by (building, room_id), not by object
    identity, so two different Room objects that represent the same physical
    room are correctly treated as conflicting.
    """

    def __init__(self, rooms: list[Room]) -> None:
        if not rooms:
            raise ValueError("Room scheduling requires at least one room.")
        # Reject duplicate physical rooms early so allocation logic stays clean.
        seen: set[tuple[str, str]] = set()
        for room in rooms:
            key = _room_identity(room)
            if key in seen:
                raise ValueError(
                    f"Duplicate physical room: building='{room.building}', "
                    f"room_id='{room.room_id}'.  Each (building, room_id) "
                    "must appear at most once in the room list."
                )
            seen.add(key)
        # Sort once at construction time so sliding-window scans are stable.
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

        # Prefer nearby rooms via sliding window; fall back to greedy if needed.
        result = self._sliding_window_allocate(available, required_capacity)
        if result is not None:
            return result
        return self._greedy_allocate(available, required_capacity)

    @staticmethod
    def _sliding_window_allocate(
        available: list[Room],
        required_capacity: int,
    ) -> tuple[Room, ...] | None:
        """
        Scan every contiguous sub-sequence of available rooms where ALL rooms
        share the same building, and return the best window that satisfies
        required_capacity.

        Restricting to a single building keeps this strategy meaningful:
        nearby rooms are those physically close within one building.  When no
        single building has enough capacity the caller falls back to
        _greedy_allocate, which can combine rooms across buildings.

        available is already sorted by (building, room_id), so same-building
        rooms are always contiguous in the list.

        Selection priority (lower is better):
          1. Fewest rooms in the window.
          2. Lowest unused capacity (tightest fit).

        Same-building exclusivity is enforced by the filter above, not by the
        sort key, so distinct_buildings is always 1 for every candidate that
        reaches the comparison.

        Once a valid window of size k is found, no window of size > k is tried.
        """
        n = len(available)
        best: tuple[Room, ...] | None = None
        # Comparison key: (room_count, unused_capacity)
        best_key: tuple = (float("inf"), float("inf"))

        for size in range(1, n + 1):
            for start in range(n - size + 1):
                window = available[start : start + size]
                # Only consider windows that stay within a single building.
                if len({r.building for r in window}) > 1:
                    continue
                total = sum(r.capacity for r in window)
                if total >= required_capacity:
                    unused = total - required_capacity
                    key = (size, unused)
                    if key < best_key:
                        best = tuple(window)
                        best_key = key
            # Found at least one valid window of this size — stop growing.
            if best is not None:
                break

        return best

    @staticmethod
    def _greedy_allocate(
        available: list[Room],
        required_capacity: int,
    ) -> tuple[Room, ...] | None:
        """
        Fallback when no contiguous sliding-window solution exists.

        Prefers the smallest single room that fits alone. If no single room
        is large enough, accumulates the largest available rooms until the
        capacity requirement is satisfied.
        """
        if not available:
            return None

        by_capacity = sorted(
            available,
            key=lambda room: (room.capacity, room.building, room.room_id),
        )
        # Single-room fast path.
        for room in by_capacity:
            if room.capacity >= required_capacity:
                return (room,)

        # Multi-room accumulation — largest first.
        selected: list[Room] = []
        total = 0
        for room in reversed(by_capacity):
            selected.append(room)
            total += room.capacity
            if total >= required_capacity:
                return tuple(sorted(selected, key=lambda r: (r.building, r.room_id)))
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
        # Use _room_identity so that two Room objects with the same
        # (building, room_id) are treated as the same physical room,
        # matching the occupancy key used by RoomAndSlotConstraint.
        target = _room_identity(room)
        for _, _, placement in partial.iter_placements():
            if placement.date == exam_date and placement.time_slot == time_slot:
                if any(_room_identity(r) == target for r in placement.rooms):
                    return True
        return False


class RoomSchedulingDomainProvider:
    """
    Builds the room-scheduling candidate domain used when room_scheduling_enabled=True.

    Candidates are ExamBlock(date, time_slot) objects — pure domain values with no
    room data attached.  Room allocation is intentionally deferred to RoomPlacementFactory
    so that each component has a single, well-defined responsibility:

      RoomSchedulingDomainProvider  →  which (date, slot) options exist
      RoomPlacementFactory          →  which rooms to assign for a given option
    """

    def candidates_for(
        self,
        course: Course,
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        partial_constraint_checker: PartialConstraintChecker | None = None,
    ) -> list[ExamBlock]:
        valid: list[ExamBlock] = []
        for exam_date in period.getAvailableDates():
            # Skip this date entirely if the collision validator rejects it.
            if not constraint_validator.canAssign(course, exam_date, partial):
                continue
            # Partial constraints (AllGap, DailyCap) are date-based, so check
            # once per date before generating individual time-slot blocks.
            if not _passes_partial_constraints(
                course, exam_date, partial, partial_constraint_checker
            ):
                continue
            for time_slot in TimeSlot:
                valid.append(ExamBlock(exam_date, time_slot))
        return valid


class DomainFeasibilityChecker:
    """Shared feasibility checker driven by the selected domain provider."""

    def __init__(self, domain_provider: SchedulingDomainProvider) -> None:
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

    def __init__(self, domain_provider: SchedulingDomainProvider, room_allocator: RoomAllocator) -> None:
        super().__init__(domain_provider)
        self._room_allocator = room_allocator

    def validate_courses(self, courses: list[Course]) -> tuple[bool, str]:
        """Validate room-mode data and capacity before any backtracking search."""
        # Room.capacity > 0 is already enforced by Room.__post_init__, so no
        # explicit room-capacity check is needed here.
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


class SchedulingModeFactory:
    """
    Composes solver components based on room_scheduling_enabled.

    This is the ONLY place in the codebase that reads room_scheduling_enabled.
    All other classes receive pre-wired components and remain mode-agnostic.
    """

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
        domain_provider = RoomSchedulingDomainProvider()
        return SchedulingComponents(
            domain_provider=domain_provider,
            # RoomPlacementFactory owns the room_allocator — it is the one that
            # converts ExamBlock candidates into ExamPlacement objects with rooms.
            placement_factory=RoomPlacementFactory(room_allocator),
            feasibility_checker=RoomSchedulingFeasibilityChecker(domain_provider, room_allocator),
            room_allocator=room_allocator,
        )
