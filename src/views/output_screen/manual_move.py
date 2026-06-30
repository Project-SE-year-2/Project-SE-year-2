from dataclasses import dataclass


@dataclass(frozen=True)
class PendingManualMove:
    course_number: str
    source_date: str
    target_date: str