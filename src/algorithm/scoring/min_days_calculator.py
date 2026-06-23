"""MinDaysCalculator — dependency for EP-102.

Computes the minimum gap (days) between consecutive mandatory (Obligatory) exams
within each (program_id, year) cohort.  Required because ScheduleMetrics has no
default values and all five fields must be populated by ScheduleScorer.
"""

from datetime import date

from src.algorithm.scoring.i_metric_calculator import IMetricCalculator
from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType


class MinDaysCalculator(IMetricCalculator):
    """Computes the minimum gap (days) between mandatory exams across all cohorts."""

    def field_name(self) -> str:
        return "min_days_required"

    def compute(self, schedule: ExamSchedule) -> float:
        # Collect exam dates per cohort — Obligatory courses only.
        cohort_dates: dict[tuple, list[date]] = {}
        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Obligatory:
                    key = (req.program_id, req.year)
                    cohort_dates.setdefault(key, []).append(exam_date)

        # Find the smallest consecutive gap across all cohorts.
        global_min: int | None = None
        for dates in cohort_dates.values():
            sorted_dates = sorted(set(dates))
            for i in range(1, len(sorted_dates)):
                gap = (sorted_dates[i] - sorted_dates[i - 1]).days
                if global_min is None or gap < global_min:
                    global_min = gap

        return float(global_min) if global_min is not None else 0.0
