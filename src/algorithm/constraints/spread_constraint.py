from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.algorithm.constraints.i_constraint import IConstraint


class SpreadConstraint(IConstraint):
    """
    Verifies that each (program_id, year) cohort's obligatory exam block spans
    at least K calendar days from the earliest to the latest mandatory exam.

    Only Obligatory requirements are included; Elective courses are excluded
    so the constraint measures the fixed core exam period, not the full student
    workload which varies by individual course selection.

    Cohorts with fewer than two Obligatory exams are skipped: a single date
    produces a span of zero and there is nothing meaningful to enforce.
    """

    def __init__(self, k: int) -> None:
        if k <= 0:
            raise ValueError(f"SpreadConstraint: k must be a positive integer, got {k}")
        self._k = k

    # ------------------------------------------------------------------
    # IConstraint implementation
    # ------------------------------------------------------------------

    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        """Return False if any cohort's obligatory exam window is smaller than K days."""
        cohort_dates = self._group_obligatory_by_cohort(schedule)

        for dates in cohort_dates.values():
            if len(dates) < 2:
                continue
            span = (max(dates) - min(dates)).days
            if span < self._k:
                return False

        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _group_obligatory_by_cohort(self, schedule: ExamSchedule) -> dict[tuple, list[date]]:
        """
        Build a mapping from (program_id, year) to a list of obligatory exam dates.
        Elective requirements are intentionally excluded.
        """
        cohort_dates: dict[tuple, list[date]] = {}

        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Obligatory:
                    key = (req.program_id, req.year)
                    cohort_dates.setdefault(key, []).append(exam_date)

        return cohort_dates
