"""EP-97 — AvgDaysCalculator.

Average gap (in days) between consecutive exams, measured per (program_id, year)
cohort and averaged across all of them. Both Obligatory and Elective courses
count here — this is the "how spread out is a student's exam load" indicator,
so every exam a cohort sits matters.
"""

from datetime import date

from src.algorithm.scoring.i_metric_calculator import IMetricCalculator
from src.models.exam_schedule import ExamSchedule


class AvgDaysCalculator(IMetricCalculator):
    """Average spacing between a cohort's exams, averaged over all cohorts."""

    def field_name(self) -> str:
        # Must match the scores.db column the scorer writes this value into.
        return "avg_days_all"

    def compute(self, schedule: ExamSchedule) -> float:
        # First pass: bucket every exam date under the cohort that sits it.
        # One course can belong to several programs/years, so a single exam
        # can land in more than one bucket.
        cohort_dates: dict[tuple, list[date]] = {}
        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                key = (req.program_id, req.year)
                cohort_dates.setdefault(key, []).append(exam_date)

        # Second pass: walk each cohort's dates in order and collect the gap
        # between every pair of neighbours. set() drops two exams that fall on
        # the same day so they don't show up as a misleading 0-day gap.
        gaps: list[int] = []
        for dates in cohort_dates.values():
            sorted_dates = sorted(set(dates))
            for i in range(1, len(sorted_dates)):
                gaps.append((sorted_dates[i] - sorted_dates[i - 1]).days)

        # A cohort with a single exam contributes no gaps, so an empty schedule
        # (or one with no pairs anywhere) has nothing to average — report 0.0.
        return round(sum(gaps) / len(gaps), 2) if gaps else 0.0
