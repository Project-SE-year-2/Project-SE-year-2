from collections import defaultdict
from datetime import date

from src.models.exam_schedule import ExamSchedule
from src.models.enums import ReqType
from src.models.schedule_score import ScheduleScore


class ScheduleScorer:
    """
    Computes all five ScheduleScore metrics for a combined (cross-period) ExamSchedule.
    Called once per schedule after the ConstraintChecker stage.
    Does NOT rank or sort — that is ScheduleRanker's responsibility.

    Flow:
        Schedule → ConstraintChecker → ScheduleScorer → ScheduleScore → ScoreRepository
    """

    # ------------------------------------------------------------------
    # 1. Average Exam Gap
    # ------------------------------------------------------------------

    def compute_avg_gap(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> float:
        """
        Average days between consecutive exams in the same program and year.
        Dates are deduplicated so two courses on the same day count once.
        Returns 0.0 when fewer than two distinct exam dates exist.
        """
        gaps: list[int] = []

        for program_id in program_ids:
            # Collect dates grouped by year for this program
            year_dates: dict[int, list[date]] = {}
            for (_, course), exam_date in schedule._store.items():
                for req in course.requirements:
                    if req.program_id == program_id:
                        year_dates.setdefault(req.year, []).append(exam_date)

            for dates in year_dates.values():
                sorted_dates = sorted(set(dates))
                for i in range(1, len(sorted_dates)):
                    gaps.append((sorted_dates[i] - sorted_dates[i - 1]).days)

        return round(sum(gaps) / len(gaps), 2) if gaps else 0.0

    # ------------------------------------------------------------------
    # 2. Minimum Mandatory Gap
    # ------------------------------------------------------------------

    def compute_min_gap(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> int:
        """
        Minimum days between any two consecutive obligatory exams
        within the same program and year.
        Returns 0 when fewer than two obligatory exams exist.
        """
        min_gap = None

        for program_id in program_ids:
            # Collect obligatory exam dates grouped by year
            year_dates: dict[int, list[date]] = {}
            for (_, course), exam_date in schedule._store.items():
                for req in course.requirements:
                    if (
                        req.program_id == program_id
                        and req.req_type == ReqType.Obligatory
                    ):
                        year_dates.setdefault(req.year, []).append(exam_date)

            for dates in year_dates.values():
                sorted_dates = sorted(set(dates))
                for i in range(1, len(sorted_dates)):
                    gap = (sorted_dates[i] - sorted_dates[i - 1]).days
                    if min_gap is None or gap < min_gap:
                        min_gap = gap

        return min_gap if min_gap is not None else 0

    # ------------------------------------------------------------------
    # 3. Elective Collisions
    # ------------------------------------------------------------------

    def compute_elective_collisions(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> int:
        """
        Number of elective exam dates that coincide with at least one
        other exam (obligatory or elective) on the same day across
        all selected programs.
        Each colliding elective date counts as one collision.
        """
        program_set = set(program_ids)

        # Collect all exam dates across selected programs
        all_dates: list[date] = []
        elective_dates: list[date] = []

        for (_, course), exam_date in schedule._store.items():
            for req in course.requirements:
                if req.program_id in program_set:
                    all_dates.append(exam_date)
                    if req.req_type == ReqType.Elective:
                        elective_dates.append(exam_date)

        # Count dates that appear more than once (collision = shared day)
        date_counts: dict[date, int] = defaultdict(int)
        for d in all_dates:
            date_counts[d] += 1

        collisions = sum(
            1 for d in set(elective_dates) if date_counts[d] > 1
        )
        return collisions

    # ------------------------------------------------------------------
    # 4. Mandatory Exam Spread
    # ------------------------------------------------------------------

    def compute_spread(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> int:
        """
        Days between the earliest and latest obligatory exam
        across all selected programs and periods.
        Returns 0 when fewer than two obligatory exams exist.
        """
        program_set = set(program_ids)
        obligatory_dates: list[date] = []

        for (_, course), exam_date in schedule._store.items():
            for req in course.requirements:
                if (
                    req.program_id in program_set
                    and req.req_type == ReqType.Obligatory
                ):
                    obligatory_dates.append(exam_date)

        if len(obligatory_dates) < 2:
            return 0

        return (max(obligatory_dates) - min(obligatory_dates)).days

    # ------------------------------------------------------------------
    # 5. Maximum Exams Per Day
    # ------------------------------------------------------------------

    def compute_max_per_day(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> int:
        """
        Maximum number of distinct exams scheduled on any single day
        across all selected programs.
        Returns 0 for an empty schedule.
        """
        program_set = set(program_ids)
        date_counts: dict[date, set] = defaultdict(set)

        for (_, course), exam_date in schedule._store.items():
            for req in course.requirements:
                if req.program_id in program_set:
                    # Use course_id to avoid double-counting the same course
                    date_counts[exam_date].add(course.course_id)

        if not date_counts:
            return 0

        return max(len(courses) for courses in date_counts.values())

    # ------------------------------------------------------------------
    # Full score
    # ------------------------------------------------------------------

    def score(
        self,
        schedule: ExamSchedule,
        program_ids: list[str],
    ) -> ScheduleScore:
        """
        Computes all five metrics and returns a populated ScheduleScore.
        This is the single entry point used by the generation pipeline.
        """
        return ScheduleScore(
            avg_gap=self.compute_avg_gap(schedule, program_ids),
            min_gap=self.compute_min_gap(schedule, program_ids),
            spread=self.compute_spread(schedule, program_ids),
            collisions=self.compute_elective_collisions(schedule, program_ids),
            max_per_day=self.compute_max_per_day(schedule, program_ids),
        )
