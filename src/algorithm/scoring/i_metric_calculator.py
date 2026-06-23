from abc import ABC, abstractmethod
from src.models.exam_schedule import ExamSchedule


class IMetricCalculator(ABC):
    """
    Interface for schedule quality metric calculators.

    Each concrete implementation computes one numeric quality indicator from a
    fully-built ExamSchedule.  The result is stored in scores.db under the
    column identified by field_name(), where the ranking layer uses it to sort
    competing schedules.

    Contrast with IConstraint: constraints give a binary pass/ fail against a
    threshold; calculators give the exact value so schedules can be ordered.
    """

    @abstractmethod
    def field_name(self) -> str:
        """Return the scores table column this calculator populates."""

    @abstractmethod
    def compute(self, schedule: "ExamSchedule") -> float:
        """Compute and return the metric value for the given schedule."""