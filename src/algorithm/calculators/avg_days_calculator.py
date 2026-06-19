from datetime import date

from src.models.exam_schedule import ExamSchedule
from src.algorithm.i_metric_calculator import IMetricCalculator


class AvgDaysCalculator(IMetricCalculator):
    """
    EP-97 — Average gap between consecutive exams, all course types.
    Groups by (program_id, year), deduplicates same-day entries,
    then computes the mean consecutive gap in days.
    """

    def field_name(self) -> str:
        return "avg_days_all"

    def compute(self, schedule: ExamSchedule, program_ids: list[str]) -> float:
        gaps: list[int] = []
        for program_id in program_ids:
            year_dates: dict[int, list[date]] = {}
            for (_, course), exam_date in schedule._store.items():
                for req in course.requirements:
                    if req.program_id == program_id:
                        year_dates.setdefault(req.year, []).append(exam_date)
            for dates in year_dates.values():
                sorted_dates = sorted(set(dates))
                for i in range(1, len(sorted_dates)):
                    gaps.append((sorted_dates[i] - sorted_dates[i - 1]).days)
        return round(sum(gaps) / len(gaps), 2) if gaps else 0.0
