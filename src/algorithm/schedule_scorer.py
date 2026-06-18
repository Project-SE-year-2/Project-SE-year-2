from src.models.exam_schedule import ExamSchedule
from src.models.schedule_score import ScheduleScore
from src.algorithm.i_metric_calculator import IMetricCalculator
from src.algorithm.calculators.avg_days_calculator import AvgDaysCalculator


class ScheduleScorer:
    """
    EP-102 — Centralized scoring orchestrator.
    Holds a list of IMetricCalculator instances and delegates each
    metric computation to the appropriate calculator.

    Flow:
        Schedule → ConstraintChecker → ScheduleScorer → ScheduleScore → ScoreRepository
    """

    def __init__(self, program_ids: list[str]):
        self._program_ids = program_ids
        self._calculators: list[IMetricCalculator] = [
            AvgDaysCalculator(),  # EP-97
        ]

    def compute_scores(self, schedule: ExamSchedule) -> ScheduleScore:
        """Iterates all registered calculators and returns a populated ScheduleScore."""
        values = {
            calc.field_name(): calc.compute(schedule, self._program_ids)
            for calc in self._calculators
        }
        return ScheduleScore(**values)
