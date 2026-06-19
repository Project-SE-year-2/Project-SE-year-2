from dataclasses import dataclass


# EP-101 — ScheduleMetrics Data Transfer Object.
# Field names match the approved ScoresDatabase schema (EP-116).
# Higher is better for avg_days_all, min_days_required, span_required.
# Lower is better for elective_conflicts, max_exams_per_day.
@dataclass
class ScheduleMetrics:
    avg_days_all: float = 0.0
    min_days_required: int = 0
    span_required: int = 0
    elective_conflicts: int = 0
    max_exams_per_day: int = 0
