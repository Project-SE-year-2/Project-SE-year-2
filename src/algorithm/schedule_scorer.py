from src.models.exam_schedule import ExamSchedule
from src.models.schedule_score import ScheduleScore
from src.algorithm.i_metric_calculator import IMetricCalculator
from src.algorithm.calculators.avg_days_calculator import AvgDaysCalculator
from src.algorithm.calculators.min_days_calculator import MinDaysCalculator
from src.algorithm.calculators.collision_calculator import CollisionCalculator
from src.algorithm.calculators.spread_calculator import SpreadCalculator
from src.algorithm.calculators.daily_cap_calculator import DailyCapCalculator


class ScheduleScorer:
    """
    EP-102 — Centralized scoring orchestrator.
    Maintains a list of IMetricCalculator instances and delegates each
    metric computation to the appropriate calculator.

    Flow:
        Schedule → ConstraintChecker → ScheduleScorer → ScheduleScore → ScoreRepository
    """

    def __init__(self, program_ids: list[str]):
        self._program_ids = program_ids
        self._calculators: list[IMetricCalculator] = [
            AvgDaysCalculator(),
            MinDaysCalculator(),
            CollisionCalculator(),
            SpreadCalculator(),
            DailyCapCalculator(),
        ]

    def compute_scores(self, schedule: ExamSchedule) -> ScheduleScore:
        """Iterates all registered calculators and returns a fully populated ScheduleScore."""
        values = {
            calc.field_name(): calc.compute(schedule, self._program_ids)
            for calc in self._calculators
        }
        return ScheduleScore(**values)
