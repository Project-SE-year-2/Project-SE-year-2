from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.algorithm.scoring.i_metric_calculator import IMetricCalculator


class DailyCapCalculator(IMetricCalculator):
    """
    Reports the peak number of concurrent exam sessions on any single calendar day.

    All active course assignments are counted globally, regardless of program
    or year - the same scope as DailyCapConstraint.

    Lower values are better: a smaller peak means the logistical load is spread
    more evenly across the calendar.

    Mirror of DailyCapConstraint: the constraint asks "does any day exceed K
    exams?"; this calculator asks "what is the highest single-day count?"
    """

    def field_name(self) -> str:
        return 'max_exams_per_day'

    def compute(self, schedule: ExamSchedule) -> float:
        # KEY: date, VALUE: number of exams scheduled on that date
        counts: dict[date, int] = {}

        # Count the number of exams scheduled for each date
        for exam_date in schedule.assignments.values():
            counts[exam_date] = counts.get(exam_date, 0) + 1

        # Return the maximum count, or 0 if there are no exams scheduled
        return max(counts.values()) if counts else 0