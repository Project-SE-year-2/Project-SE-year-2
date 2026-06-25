from datetime import date as DateType
from src.models.course import Course
from src.models.exam_placement import ExamPlacement
from src.models.exam_period import ExamPeriod
from src.models.enums import Semester, Moed, TimeSlot

# By giving each Enum a number (0/1/2), we sorting the schedules in the correct chronological order.
_SEM_ORDER = {Semester.FALL: 0, Semester.SPRI: 1, Semester.SUMM: 2}
_MOED_ORDER = {Moed.Aleph: 0, Moed.Bet: 1, Moed.Gimel: 2}
_TIME_SLOT_ORDER = {TimeSlot.MORNING: 0, TimeSlot.AFTERNOON: 1, TimeSlot.EVENING: 2, None: -1}

class ExamSchedule:
    """
    Represents one valid exam assignment.
    When used inside BacktrackingSolver it covers a single ExamPeriod.
    After ScheduleCombiner.merge() it spans multiple periods.

    Placements are stored as (ExamPeriod, Course) -> ExamPlacement so the same
    Course can appear in more than one period without key collision.
    """

    def __init__(self, period: ExamPeriod | None = None):
        self.period: ExamPeriod | None = period
        # Backward-compat display fields (taken from primary period)
        self.semester: str = period.semester if period else ""
        self.moed: str = period.moed if period else ""
        # Core storage keeps rich placement data. The public assignments
        # property below preserves the old Course -> date API.
        self._store: dict[tuple, ExamPlacement] = {}

    # ------------------------------------------------------------------
    # Per-period interface used by BacktrackingSolver
    # ------------------------------------------------------------------

    @property
    def assignments(self) -> dict[Course, DateType]:
        """Returns only the primary-period assignments (backward compatible)."""
        return {course: placement.date for course, placement in self.placements.items()}

    @property
    def placements(self) -> dict[Course, ExamPlacement]:
        """Returns only the primary-period placements with full scheduling data."""
        if self.period is None:
            return self._flat_cross_period_placements()
        return {c: placement for (p, c), placement in self._store.items() if p is self.period}

    def iter_placements(self):
        """Yield (period, course, placement) for every stored placement."""
        for period, course, placement in self._all_store_items():
            yield period, course, placement

    def assign(self, course: Course, exam_date: DateType | ExamPlacement) -> None:
        """Assign a course to either a legacy date or a full ExamPlacement."""
        placement = self._as_placement(exam_date)
        self._store[(self.period, course)] = placement

    def unassign(self, course: Course) -> None:
        """Remove a course placement from this schedule if it exists."""
        self._store.pop((self.period, course), None)

    def copy(self) -> "ExamSchedule":
        """Return an independent schedule copy with the same placements."""
        clone = ExamSchedule(self.period)
        clone.semester = self.semester
        clone.moed = self.moed
        clone._store = dict(self._store)
        return clone

    # ------------------------------------------------------------------
    # Cross-period interface used by ScheduleCombiner
    # ------------------------------------------------------------------

    def merge(self, other: "ExamSchedule") -> "ExamSchedule":
        """Combine two per-period schedules into one cross-period schedule."""
        merged = ExamSchedule(None)
        merged.semester = self.semester
        merged.moed = self.moed
        merged._store = {**self._store, **other._store}
        return merged

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def sortByDate(self) -> list:
        """
        Returns all assignments as tuples sorted chronologically.
        - Per-period: list of (Course, date)
        - Cross-period: list of (ExamPeriod, Course, date) sorted by
          semester order -> moed order -> date -> time slot
        """
        if self.period is not None:
            items = [
                (c, placement)
                for (p, c), placement in self._store.items()
                if p is self.period
            ]
            return [
                (course, placement.date)
                for course, placement in sorted(items, key=lambda x: self._placement_sort_key(x[1]))
            ]

        items = list(self.iter_placements())
        sorted_items = sorted(
            items,
            key=lambda x: (
                _SEM_ORDER.get(x[0].semester, 99),
                _MOED_ORDER.get(x[0].moed, 99),
                *self._placement_sort_key(x[2]),
            ),
        )
        return [(period, course, placement.date) for period, course, placement in sorted_items]

    def groupBySemesterAndMoed(self) -> dict:
        groups: dict[tuple, dict] = {}
        for (p, c), placement in self._store.items():
            key = (p.semester, p.moed)
            groups.setdefault(key, {})[c] = placement.date
        return groups

    def groupBySemesterAndMoedWithPlacements(self) -> dict[tuple, dict]:
        """Return all placements grouped by (semester, moed), preserving full ExamPlacement data.

        Like groupBySemesterAndMoed() but returns ExamPlacement objects instead of
        plain dates, so callers can access time_slot, rooms, and total_capacity for
        room-scheduling results.

        Returns:
            {(Semester, Moed): {Course: ExamPlacement}}

        Note:
            Date-only placements are included with time_slot=None and rooms=().
            Callers should use placement.is_room_based to distinguish the two modes.
        """
        groups: dict[tuple, dict] = {}
        for (p, c), placement in self._store.items():
            key = (p.semester, p.moed)
            groups.setdefault(key, {})[c] = placement
        return groups

    @property
    def is_cross_period(self) -> bool:
        return self.period is None

    @property
    def sort_key(self) -> tuple:
        sorted_items = self._sorted_store_items()
        if self.period is not None:
            placement_keys = tuple(self._placement_sort_key(placement) for _, placement in sorted_items)
            placements = [placement for _, placement in sorted_items]
        else:
            placement_keys = tuple(
                (
                    _SEM_ORDER.get(period.semester, 99),
                    _MOED_ORDER.get(period.moed, 99),
                    *self._placement_sort_key(placement),
                )
                for period, _, placement in sorted_items
            )
            placements = [placement for _, _, placement in sorted_items]

        # Keep the legacy exact shape for date-only schedules so existing tests
        # and callers that compare sort_key to a tuple of dates remain valid.
        if all(placement.time_slot is None for placement in placements):
            return tuple(placement.date for placement in placements)
        return placement_keys

    @staticmethod
    def _as_placement(value: DateType | ExamPlacement) -> ExamPlacement:
        """Normalize legacy date inputs into ExamPlacement objects."""
        if isinstance(value, ExamPlacement):
            return value
        return ExamPlacement(date=value)

    @staticmethod
    def _placement_sort_key(placement: ExamPlacement) -> tuple:
        """Sort by date first and by time slot when room scheduling data exists."""
        return (placement.date, _TIME_SLOT_ORDER.get(placement.time_slot, 99))

    def _sorted_store_items(self) -> list:
        """Return raw store items sorted by the placement-aware chronological order."""
        if self.period is not None:
            items = [
                (course, placement)
                for (period, course), placement in self._store.items()
                if period is self.period
            ]
            return sorted(items, key=lambda x: self._placement_sort_key(x[1]))

        items = self._all_store_items()
        return sorted(
            items,
            key=lambda x: (
                _SEM_ORDER.get(x[0].semester, 99),
                _MOED_ORDER.get(x[0].moed, 99),
                *self._placement_sort_key(x[2]),
            ),
        )

    def _all_store_items(self) -> list:
        """Return raw store items as (period, course, placement) tuples."""
        return [(period, course, placement) for (period, course), placement in self._store.items()]

    def _flat_cross_period_placements(self) -> dict[Course, ExamPlacement]:
        """Return legacy Course -> placement view, refusing lossy duplicates."""
        result: dict[Course, ExamPlacement] = {}
        for period, course, placement in self._all_store_items():
            if course in result:
                raise ValueError(
                    "Cross-period schedule contains the same course in multiple periods. "
                    "Use iter_placements() to access period-specific placements."
                )
            result[course] = placement
        return result
