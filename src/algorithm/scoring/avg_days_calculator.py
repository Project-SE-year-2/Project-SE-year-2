"""EP-97 — AvgDaysCalculator.

Groups every exam assignment by (program_id, year) cohort, treating Obligatory
and Elective courses uniformly.  Within each cohort, duplicate dates are removed
before consecutive gaps are measured.  The return value is the mean gap in days
across all cohort pairs, or 0.0 when there are fewer than two distinct dates in
every cohort.
"""

from datetime import date

from src.algorithm.scoring.i_metric_calculator import IMetricCalculator
from src.models.exam_schedule import ExamSchedule


class AvgDaysCalculator(IMetricCalculator):
    """Computes the average gap (days) between consecutive exams across all cohorts."""

    def field_name(self) -> str:
        return "avg_days_all"

    def compute(self, schedule: ExamSchedule) -> float:
        # Collect exam dates per (program_id, year) cohort — all course types.
        cohort_dates: dict[tuple, list[date]] = {}
        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                key = (req.program_id, req.year)
                cohort_dates.setdefault(key, []).append(exam_date)

        # For each cohort, sort unique dates and accumulate consecutive gaps.
        gaps: list[int] = []
        for dates in cohort_dates.values():
            sorted_dates = sorted(set(dates))
            for i in range(1, len(sorted_dates)):
                gaps.append((sorted_dates[i] - sorted_dates[i - 1]).days)

        return round(sum(gaps) / len(gaps), 2) if gaps else 0.0
