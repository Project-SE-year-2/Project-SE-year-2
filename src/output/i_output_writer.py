from abc import ABC, abstractmethod
from src.models.exam_schedule import ExamSchedule
from src.models.exam_period import ExamPeriod


class IOutputWriter(ABC):
    """
    Interface for all output writers.
    Any class that writes scheduling results to a destination must implement this.
    """

    @abstractmethod
    def write(
        self,
        schedules: list[ExamSchedule],
        metadata: dict[ExamPeriod, dict],
        programs: list[str],
        output_path: str,
    ) -> None:
        """Write the scheduling results to the given output path."""
