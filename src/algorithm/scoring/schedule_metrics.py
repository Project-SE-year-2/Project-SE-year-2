from dataclasses import dataclass


@dataclass
class ScheduleMetrics:
    """Five quality indicators computed once per schedule by ScheduleScorer."""
    min_days_required: float   # minimum gap (days) between mandatory exams in the same program+year
    avg_days_all: float        # average gap (days) between all consecutive exams in the same program+year
    elective_conflicts: int    # number of elective-course date collisions in the same program+year
    span_required: int         # calendar spread (days) from first to last mandatory exam
    max_exams_per_day: int     # peak number of exams scheduled on a single calendar day
