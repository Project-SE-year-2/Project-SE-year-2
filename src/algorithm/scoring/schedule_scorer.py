"""EP-102 — ScheduleScorer orchestrator.

One place that turns a finished schedule into its five quality numbers. It owns
the list of calculators and runs them; each calculator knows one metric and
nothing about the others. Adding a sixth metric later is a new calculator class
plus one line in the list below — nothing here needs to change otherwise.
"""

from src.algorithm.scoring.i_metric_calculator import IMetricCalculator
from src.algorithm.scoring.schedule_metrics import ScheduleMetrics
from src.algorithm.scoring.avg_days_calculator import AvgDaysCalculator
from src.algorithm.scoring.collision_calculator import CollisionCalculator
from src.algorithm.scoring.spread_calculator import SpreadCalculator
from src.algorithm.scoring.daily_cap_calculator import DailyCapCalculator
from src.models.exam_schedule import ExamSchedule


class ScheduleScorer:
    """Runs every registered calculator and packs the results into ScheduleMetrics."""

    def __init__(self) -> None:
        # The active metric set. Order here doesn't affect the result (each
        # calculator writes its own named field), it's just the run order.
        # MinDaysCalculator lives in a separate PR, so min_days_required is
        # filled in by compute_scores() until it's added here.
        self._calculators: list[IMetricCalculator] = [
            AvgDaysCalculator(),
            CollisionCalculator(),
            SpreadCalculator(),
            DailyCapCalculator(),
        ]

    @classmethod
    def default(cls) -> "ScheduleScorer":
        # The way callers are expected to build a scorer — keeps construction
        # in one spot so we can wire in dependencies here later without touching
        # call sites.
        return cls()

    def compute_scores(self, schedule: ExamSchedule) -> ScheduleMetrics:
        # Ask each calculator for its single value and key it by the field name
        # it owns. field_name() is exactly the ScheduleMetrics attribute name,
        # so the dict below unpacks straight into the dataclass.
        values = {
            calc.field_name(): calc.compute(schedule)
            for calc in self._calculators
        }

        # min_days_required has no calculator registered yet — supply a neutral
        # value so the dataclass can still be built. Drop this line the moment
        # MinDaysCalculator joins the list above.
        values.setdefault("min_days_required", 0.0)

        return ScheduleMetrics(**values)
