"""EP-102 — ScheduleScorer orchestrator.

Holds the registered IMetricCalculator instances and delegates to each in turn.
compute_scores() collects { field_name: value } from every calculator and
constructs a ScheduleMetrics in a single call, so adding a future metric
requires only a new subclass and one line in _calculators.

All five calculators are registered: MinDaysCalculator, AvgDaysCalculator,
CollisionCalculator, SpreadCalculator, DailyCapCalculator.

Use the default() factory to obtain a production-ready instance.
"""

from src.algorithm.scoring.i_metric_calculator import IMetricCalculator
from src.algorithm.scoring.schedule_metrics import ScheduleMetrics
from src.algorithm.scoring.avg_days_calculator import AvgDaysCalculator
from src.algorithm.scoring.collision_calculator import CollisionCalculator
from src.algorithm.scoring.spread_calculator import SpreadCalculator
from src.algorithm.scoring.daily_cap_calculator import DailyCapCalculator
from src.algorithm.scoring.min_days_calculator import MinDaysCalculator
from src.algorithm.scoring.room_distance_calculator import RoomDistanceCalculator
from src.models.exam_schedule import ExamSchedule


class ScheduleScorer:
    """Orchestrates the metric calculators and produces a ScheduleMetrics snapshot."""

    def __init__(self) -> None:
        # Calculators owned by this PR. MinDaysCalculator is added by a separate PR.
        self._calculators: list[IMetricCalculator] = [
            MinDaysCalculator(),
            AvgDaysCalculator(),
            CollisionCalculator(),
            SpreadCalculator(),
            DailyCapCalculator(),
            RoomDistanceCalculator(),
        ]

    @classmethod
    def default(cls) -> "ScheduleScorer":
        """Factory that returns a fully-configured ScheduleScorer."""
        return cls()

    def compute_scores(self, schedule: ExamSchedule) -> ScheduleMetrics:
        """Delegate to each calculator and assemble the result dataclass."""
        values = {
            calc.field_name(): calc.compute(schedule)
            for calc in self._calculators
        }
        return ScheduleMetrics(**values)
