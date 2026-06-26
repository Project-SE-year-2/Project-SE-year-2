from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.algorithm.constraints.i_constraint import IConstraint


class DailyCapConstraint(IConstraint):
    """
    Verifies that the total number of concurrent exam sessions across the
    entire institution on any single calendar date does not exceed K.

    Unlike AllGapConstraint (which is scoped per student cohort), this is a
    global capacity check: every active course assignment, regardless of
    program or year, counts toward the cap for its date.

    Exams are counted per calendar day, not per (date, time_slot). If time_slot
    were part of the grouping key, two exams on the same day in different slots
    would each count in a separate cell and bypass the daily cap.
    """

    def __init__(self, k: int) -> None:
        if k <= 0:
            raise ValueError(f"DailyCapConstraint: k must be a positive integer, got {k}")
        self._k = k

    def is_satisfied(self, schedule: ExamSchedule) -> bool:
        """Return False if any single date has more than K exam sessions scheduled."""
        counts_by_date: dict[date, int] = {}

        for exam_date in schedule.assignments.values():
            counts_by_date[exam_date] = counts_by_date.get(exam_date, 0) + 1

        return all(count <= self._k for count in counts_by_date.values())
