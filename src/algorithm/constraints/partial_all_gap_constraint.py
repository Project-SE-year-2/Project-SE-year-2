from datetime import date

from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraints.i_partial_constraint import IPartialConstraint


class PartialAllGapConstraint(IPartialConstraint):
    """Prunes partial schedules with too-small gaps between any exams in the same cohort.

    Gaps are measured between calendar dates, not between (date, time_slot) pairs.
    If exams were grouped by (date, time_slot), two same-day exams in different slots
    would fall into separate groups with no adjacent pair to compare - allowing a student
    to face two exams on the same day without triggering the K-day gap requirement.
    """

    def __init__(self, k: int) -> None:
        """Store the minimum required gap between exams in the same cohort."""
        if k <= 0:
            raise ValueError(f"PartialAllGapConstraint: k must be positive, got {k}")
        self._k = k

    def is_still_valid(self, schedule: ExamSchedule) -> bool:
        """Return False if any assigned exams in the same cohort are already closer than K days."""
        cohort_dates = self._group_dates_by_cohort(schedule)

        for dates in cohort_dates.values():
            sorted_dates = sorted(dates)
            for previous_date, current_date in zip(sorted_dates, sorted_dates[1:]):
                gap = (current_date - previous_date).days
                if gap < self._k:
                    return False

        return True

    def _group_dates_by_cohort(
        self,
        schedule: ExamSchedule,
    ) -> dict[tuple[str, int], list[date]]:
        """Group all assigned exam dates by (program_id, year), ignoring requirement type."""
        cohort_dates: dict[tuple[str, int], list[date]] = {}

        for course, exam_date in schedule.assignments.items():
            seen_cohorts = set()
            for req in course.requirements:
                key = (req.program_id, req.year)
                if key not in seen_cohorts:
                    seen_cohorts.add(key)
                    cohort_dates.setdefault(key, []).append(exam_date)

        return cohort_dates