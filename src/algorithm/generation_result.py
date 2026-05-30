from dataclasses import dataclass

from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule


@dataclass(slots=True)
class PeriodGenerationResult:
    period: ExamPeriod
    schedules: list[ExamSchedule]
    metadata: dict