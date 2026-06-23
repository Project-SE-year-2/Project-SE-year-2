from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.algorithm.scoring.i_metric_calculator import IMetricCalculator


class SpreadCalculator(IMetricCalculator):
    """
    Measures the average calendar span of obligatory exam blocks across all
    (program_id, year) cohorts.

    For each cohort, the span is (max(dates) - min(dates)).days. 
    Cohorts with fewer than two obligatory exams are skipped - a single date 
    produces a span of zero and carries no meaningful information.

    Higher values are better: a larger average spread means obligatory exams
    are distributed over a wider window, giving students more preparation time.

    Mirror of SpreadConstraint: the constraint asks "does every cohort span at
    least K days?"; this calculator asks "how wide is the average span?"
    """

    def field_name(self) -> str:
        return 'span_required'

    def compute(self, schedule: ExamSchedule) -> float:
        # Key: (program_id, year), Value: list of exam dates for that cohort
        cohort_dates: dict[tuple, list[date]] = {}
        
        # Gather exam dates for each (program_id, year) cohort based on obligatory requirements
        for course, exam_date in schedule.assignments.items():
            for req in course.requirements:
                if req.req_type == ReqType.Obligatory:
                    key = (req.program_id, req.year)
                    cohort_dates.setdefault(key, []).append(exam_date)

        # Calculate the span for each cohort
        spans = [
            (max(dates) - min(dates)).days
            for dates in cohort_dates.values()
            if len(dates) >= 2
        ]
        
        # If no cohort has at least two exams, the span is undefined; return 0.0
        if not spans:
            return 0.0

        # Calculate and return the average span across all valid cohorts
        return round(sum(spans) / len(spans), 2)