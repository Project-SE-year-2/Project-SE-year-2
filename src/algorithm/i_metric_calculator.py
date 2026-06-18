from abc import ABC, abstractmethod

from src.models.exam_schedule import ExamSchedule


class IMetricCalculator(ABC):
    """
    EP-95 — Contract for all schedule quality metric calculators.
    Each subclass computes one metric and declares the ScheduleScore
    field it populates via field_name().
    """

    @abstractmethod
    def field_name(self) -> str:
        """Returns the ScheduleScore attribute name this calculator fills."""

    @abstractmethod
    def compute(self, schedule: ExamSchedule, program_ids: list[str]) -> float | int:
        """Computes and returns the metric value for the given schedule."""
