from src.models.exam_schedule import ExamSchedule
from src.models.schedule_score import ScheduleMetrics
from src.algorithm.i_metric_calculator import IMetricCalculator
from src.algorithm.calculators.avg_days_calculator import AvgDaysCalculator


class ScheduleScorer:
    """
    EP-102 — Centralized scoring orchestrator.
    Holds a list of IMetricCalculator instances and delegates each
    metric computation to the appropriate calculator.

    program_ids defaults to an empty list for backward compatibility —
    callers that do not supply programs will receive a zeroed ScheduleMetrics.

    Flow:
        Schedule → ConstraintChecker → ScheduleScorer → ScheduleMetrics → ScoresDatabase
    """

    def __init__(self, program_ids: list[str] | None = None):
        self._program_ids: list[str] = program_ids if program_ids is not None else []
        self._calculators: list[IMetricCalculator] = [
            AvgDaysCalculator(),  # EP-97
        ]

    def compute_scores(self, schedule: ExamSchedule) -> ScheduleMetrics:
        """Iterates all registered calculators and returns a populated ScheduleMetrics."""
        values = {
            calc.field_name(): calc.compute(schedule, self._program_ids)
            for calc in self._calculators
        }
        return ScheduleMetrics(**values)
