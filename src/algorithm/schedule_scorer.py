from datetime import date
from src.models.exam_schedule import ExamSchedule
from src.models.schedule_score import ScheduleScore


class ScheduleScorer:
    """
    Computes ScheduleScore metrics for a combined (cross-period) ExamSchedule.
    Called once per schedule after generation and filtering.
    Results are stored alongside the schedule index for sorting by ScheduleRanker.
    """

    def compute_avg_gap(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> float:
        """
        Returns the average gap in days between consecutive exams
        within the same program and year.

        Example:
            Year 1, program 83101:
                Physics  → Feb 3
                Calculus → Feb 10  (gap: 7)
                CS Intro → Feb 24  (gap: 14)
            avg_gap = (7 + 14) / 2 = 10.5
        """
        gaps: list[int] = []

        for program_id in program_ids:

            # Step 1 — collect exam dates grouped by year for this program
            year_dates: dict[int, list[date]] = {}

            for (period, course), exam_date in schedule._store.items():
                for req in course.requirements:
                    # Only include courses that belong to this program
                    if req.program_id == program_id:
                        year_dates.setdefault(req.year, []).append(exam_date)

            # Step 2 — for each year, compute gaps between sorted unique dates
            for dates in year_dates.values():
                # deduplicate: two courses on the same day count as one date
                sorted_dates = sorted(set(dates))

                for i in range(1, len(sorted_dates)):
                    gap = (sorted_dates[i] - sorted_dates[i - 1]).days
                    gaps.append(gap)

        # Step 3 — return the mean; 0.0 when there are fewer than two exams
        return round(sum(gaps) / len(gaps), 2) if gaps else 0.0

    def score(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> ScheduleScore:
        """
        Builds a full ScheduleScore for the given schedule.
        Only avg_gap is computed now; the remaining fields (min_gap, spread,
        collisions, max_per_day) are filled as the other EPIC-2 tasks land.
        """
        return ScheduleScore(
            avg_gap=self.compute_avg_gap(schedule, program_ids),
        )
