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
        # Bucket the obligatory exam dates per cohort up front, then look for
        # the single tightest pair anywhere. Start at infinity so the first
        # real gap always replaces it.
        cohort_dates = self._group_obligatory_dates_by_cohort(schedule)
        min_gap = inf

        for dates in cohort_dates.values():
            sorted_dates = sorted(dates)

            # Need at least two exams in a cohort to have a gap at all.
            if len(sorted_dates) < 2:
                continue

            # Compare each exam against the one right after it and keep the
            # smallest gap we've seen so far.
            for previous_date, current_date in zip(sorted_dates, sorted_dates[1:]):
                gap = (current_date - previous_date).days
                min_gap = min(min_gap, gap)

        # If no cohort had a pair, min_gap is still inf — the caller treats that
        # as "no constraint to measure".
        return float(min_gap)

    def _group_obligatory_dates_by_cohort(
        self,
        schedule: ExamSchedule,
    ) -> dict[tuple[str, int], list[date]]:
        """Group Obligatory exam dates by their matching (program_id, year) cohort."""
        cohort_dates: dict[tuple[str, int], list[date]] = {}

        # A course can satisfy several programs/years, so check each requirement
        # separately. Only Obligatory ones count toward this metric — electives
        # are skipped entirely.
        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Obligatory:
                    key = (req.program_id, req.year)
                    cohort_dates.setdefault(key, []).append(exam_date)

        return cohort_dates