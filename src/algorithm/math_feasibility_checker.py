from typing import Iterable
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.constraint_settings import ConstraintSettings
from src.models.enums import ReqType


class MathFeasibilityChecker:
    """
    Performs lightning-fast mathematical pre-checks to determine if a schedule
    is fundamentally impossible given the period's date boundaries and the enabled constraints.
    """

    @staticmethod
    def check_feasibility(courses: Iterable[Course], period: ExamPeriod, settings: ConstraintSettings | None) -> tuple[bool, str]:
        """
        Returns (True, "") if the schedule passes the math pre-checks,
        or (False, reason) if it is mathematically impossible.
        """
        course_list = list(courses)
        num_courses = len(course_list)
        available_days = (period.end_date - period.start_date).days + 1

        if settings is None or num_courses <= 1:
            return True, ""

        # 1. All Gap Constraint
        if settings.all_gap_enabled:
            gap_all = settings.all_gap_k
            
            # Find the max cohort size (both Obligatory and Elective)
            cohort_counts_all = {}
            for course in course_list:
                seen_cohorts = set()
                for req in course.requirements:
                    key = (req.program_id, req.year)
                    if key not in seen_cohorts:
                        seen_cohorts.add(key)
                        cohort_counts_all[key] = cohort_counts_all.get(key, 0) + 1
            max_in_cohort = max(cohort_counts_all.values()) if cohort_counts_all else 0
            
            if max_in_cohort >= 2:
                min_days = (max_in_cohort - 1) * gap_all + 1
                if min_days > available_days:
                    return False, f"A cohort has {max_in_cohort} exams requiring {min_days} days (gap {gap_all}), but only {available_days} available."

        # 2. Daily Cap Constraint
        if settings.daily_cap_enabled:
            max_capacity = settings.daily_cap_k * available_days
            if num_courses > max_capacity:
                return False, f"Daily cap of {settings.daily_cap_k} over {available_days} days allows max {max_capacity} exams, but {num_courses} are required."

        # 3. Mandatory Constraints (Spread and Mandatory Gap)
        if settings.mandatory_gap_enabled or settings.spread_enabled:
            cohort_counts = {}
            for course in course_list:
                for req in course.requirements:
                    if req.req_type == ReqType.Obligatory:
                        key = (req.program_id, req.year)
                        cohort_counts[key] = cohort_counts.get(key, 0) + 1

            max_obligatory_in_cohort = max(cohort_counts.values()) if cohort_counts else 0

            if max_obligatory_in_cohort >= 2:
                # Mandatory Gap
                if settings.mandatory_gap_enabled:
                    gap_mand = settings.mandatory_gap_k
                    min_days = (max_obligatory_in_cohort - 1) * gap_mand + 1
                    if min_days > available_days:
                        return False, f"A cohort has {max_obligatory_in_cohort} mandatory exams requiring {min_days} days (gap {gap_mand}), but only {available_days} available."

                # Spread
                if settings.spread_enabled:
                    max_possible_span = available_days - 1
                    if settings.spread_k > max_possible_span:
                        return False, f"Spread of {settings.spread_k} requested, but period span is only {max_possible_span}."

        return True, ""
