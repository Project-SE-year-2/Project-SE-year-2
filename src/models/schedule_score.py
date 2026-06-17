from dataclasses import dataclass


# Holds the five quality metrics computed for one combined ExamSchedule.
# Produced by ScheduleScorer and consumed by ISortCriteria / ScheduleRanker.
# Higher is better for avg_gap, min_gap, spread.
# Lower is better for collisions, max_per_day.
@dataclass
class ScheduleScore:
    # Average days between consecutive exams in the same program and year
    avg_gap: float = 0.0

    # Minimum days between any two obligatory exams in the same program and year
    min_gap: int = 0

    # Days between the first and last exam across all periods
    spread: int = 0

    # Number of elective-course date collisions across selected programs
    collisions: int = 0

    # Number of exams on the busiest single day
    max_per_day: int = 0
