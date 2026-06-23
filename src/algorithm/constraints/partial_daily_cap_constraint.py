from datetime import date

from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraints.i_partial_constraint import IPartialConstraint


class PartialDailyCapConstraint(IPartialConstraint):
    """Prunes partial schedules whose daily exam count already exceeds K."""

    def __init__(self, k: int) -> None:
        """Store the maximum allowed number of exams per calendar day."""
        if k <= 0:
            raise ValueError(f"PartialDailyCapConstraint: k must be positive, got {k}")
        self._k = k

    def is_still_valid(self, schedule: ExamSchedule) -> bool:
        """Return False if any assigned date already contains more than K exams."""
        counts_by_date: dict[date, int] = {}

        for exam_date in schedule.assignments.values():
            counts_by_date[exam_date] = counts_by_date.get(exam_date, 0) + 1

        return all(count <= self._k for count in counts_by_date.values())