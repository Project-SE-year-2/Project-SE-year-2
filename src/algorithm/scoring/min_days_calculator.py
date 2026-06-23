from datetime import date
from math import inf

from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.algorithm.scoring.i_metric_calculator import IMetricCalculator


class MinDaysCalculator(IMetricCalculator):
    """
    Computes the smallest gap in days between consecutive Obligatory exams
    inside the same (program_id, year) cohort.
    """

    def field_name(self) -> str:
        """Return the database field name populated by this calculator."""
        return "min_days_required"

    def compute(self, schedule: ExamSchedule) -> float:
        """Return the global minimum obligatory-exam gap across all cohorts."""
        cohort_dates = self._group_obligatory_dates_by_cohort(schedule)
        min_gap = inf

        for dates in cohort_dates.values():
            sorted_dates = sorted(dates)

            if len(sorted_dates) < 2:
                continue

            for previous_date, current_date in zip(sorted_dates, sorted_dates[1:]):
                gap = (current_date - previous_date).days
                min_gap = min(min_gap, gap)

        return float(min_gap)

    def _group_obligatory_dates_by_cohort(
        self,
        schedule: ExamSchedule,
    ) -> dict[tuple[str, int], list[date]]:
        """Group Obligatory exam dates by their matching (program_id, year) cohort."""
        cohort_dates: dict[tuple[str, int], list[date]] = {}

        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Obligatory:
                    key = (req.program_id, req.year)
                    cohort_dates.setdefault(key, []).append(exam_date)

        return cohort_dates