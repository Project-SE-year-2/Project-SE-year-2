from datetime import date as DateType
from src.models.course import Course
from src.models.exam_period import ExamPeriod

_SEM_ORDER = {"FALL": 0, "SPRI": 1, "SUMM": 2}
_MOED_ORDER = {"Aleph": 0, "Bet": 1, "Gimel": 2}


class ExamSchedule:
    """
    Represents one valid exam assignment.
    When used inside BacktrackingSolver it covers a single ExamPeriod.
    After ScheduleCombiner.merge() it spans multiple periods.

    All assignments are stored as (ExamPeriod, Course) -> date so the same
    Course can appear in more than one period without key collision.
    """

    def __init__(self, period: ExamPeriod | None = None):
        self.period: ExamPeriod | None = period
        # Backward-compat display fields (taken from primary period)
        self.semester: str = period.semester if period else ""
        self.moed: str = period.moed if period else ""
        # Core storage: (ExamPeriod, Course) -> date
        self._store: dict[tuple, DateType] = {}

    # ------------------------------------------------------------------
    # Per-period interface used by BacktrackingSolver
    # ------------------------------------------------------------------

    @property
    def assignments(self) -> dict[Course, DateType]:
        """Returns only the primary-period assignments (backward compatible)."""
        if self.period is None:
            # Cross-period schedule: return flat course->date (last period wins,
            # safe because the same course key is unique within a period)
            return {c: d for (_, c), d in self._store.items()}
        return {c: d for (p, c), d in self._store.items() if p is self.period}

    def assign(self, course: Course, exam_date: DateType) -> None:
        self._store[(self.period, course)] = exam_date

    def unassign(self, course: Course) -> None:
        self._store.pop((self.period, course), None)

    def copy(self) -> "ExamSchedule":
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
          semester order -> moed order -> date
        """
        if self.period is not None:
            items = [(c, d) for (p, c), d in self._store.items() if p is self.period]
            return sorted(items, key=lambda x: x[1])

        items = [(p, c, d) for (p, c), d in self._store.items()]
        return sorted(
            items,
            key=lambda x: (
                _SEM_ORDER.get(x[0].semester, 99),
                _MOED_ORDER.get(x[0].moed, 99),
                x[2],
            ),
        )

    def groupBySemesterAndMoed(self) -> dict:
        groups: dict[tuple, dict] = {}
        for (p, c), d in self._store.items():
            key = (p.semester, p.moed)
            groups.setdefault(key, {})[c] = d
        return groups

    @property
    def is_cross_period(self) -> bool:
        return self.period is None

    @property
    def sort_key(self) -> tuple:
        sorted_items = self.sortByDate()
        if self.period is not None:
            return tuple(d for _, d in sorted_items)
        return tuple(d for _, _, d in sorted_items)
