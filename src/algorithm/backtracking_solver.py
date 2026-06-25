import random

from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.algorithm.i_collision_validator import ICollisionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.course_ordering_heuristic import CourseOrderingHeuristic
from src.algorithm.forward_checker import ForwardChecker
from src.algorithm.constraints.partial_constraint_checker import PartialConstraintChecker
from src.algorithm.scheduling_mode_factory import (
    DateOnlyDomainProvider,
    DateOnlyFeasibilityChecker,
    DateOnlyPlacementFactory,
    SchedulingComponents,
)


class BacktrackingSolver:
    """
    Enumerates ALL valid exam schedules for a single ExamPeriod via backtracking.

    Pruning strategy (three layers, applied in order):
      1. Static MCV ordering  — courses with most obligatory-group conflicts come first.
      2. Dynamic MRV          — at each node, pick the unassigned course with the
                                fewest remaining valid dates (Minimum Remaining Values).
      3. Forward-checking     — after each assignment verify every remaining course
                                still has at least one valid date; prune immediately
                                if any course has zero options.

    First-solution strategy:
      Before systematic backtracking, run randomized DFS restarts (Las Vegas).
      Each restart shuffles date order at every node, exploring a different subtree.
      The first solution found is yielded immediately; systematic backtracking then
      continues from scratch to enumerate all remaining solutions.
    """

    def __init__(
        self,
        validator: ICollisionValidator,
        heuristic: CourseOrderingHeuristic,
        forward_checker: ForwardChecker,
        partial_constraint_checker: PartialConstraintChecker | None = None,
        scheduling_components: SchedulingComponents | None = None,
    ):
        self._validator = validator
        self._heuristic = heuristic
        self._forward_checker = forward_checker
        self._partial_constraint_checker = partial_constraint_checker
        self._scheduling_components = scheduling_components or self._default_components()
        self._domain_provider = self._scheduling_components.domain_provider
        self._placement_factory = self._scheduling_components.placement_factory
        self._feasibility_checker = self._scheduling_components.feasibility_checker

    @staticmethod
    def _default_components() -> SchedulingComponents:
        """Keep direct BacktrackingSolver construction date-only by default."""
        domain_provider = DateOnlyDomainProvider()
        return SchedulingComponents(
            domain_provider=domain_provider,
            placement_factory=DateOnlyPlacementFactory(),
            feasibility_checker=DateOnlyFeasibilityChecker(domain_provider),
        )

    def solve(
        self,
        courses: list[Course],
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> list[ExamSchedule]:
        results: list[ExamSchedule] = []
        partial = ExamSchedule(period)
        ordered = self._heuristic.orderByMostConstrained(courses, period)
        self._backtrack(ordered, partial, period, constraint_validator, results)
        return results

    def solve_stream(
        self,
        courses: list[Course],
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ):
        """
        Generator that yields valid exam schedules one at a time.

        Phase 1 — randomized backtracking restarts: find the first solution fast
                  by exploring random subtrees.  Yields immediately on success.
        Phase 2 — systematic backtracking: enumerates all remaining solutions,
                  skipping the one already yielded in Phase 1.
        """
        ordered = self._heuristic.orderByMostConstrained(courses, period)

        first = self._find_first_with_restarts(ordered, period, constraint_validator)
        if first is not None:
            yield first

        partial = ExamSchedule(period)
        yield from self._backtrack_stream(
            ordered, partial, period, constraint_validator,
            skip=first,
        )

    # ── Feasibility check ─────────────────────────────────────────────────────

    def check_feasibility(
        self,
        courses: list[Course],
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> tuple[bool, str]:
        """
        Quick pre-check before running the full solver.

        Level 1 — domain check (instant): every course must have at least one
                  valid date on its own, ignoring other courses.
        Level 2 — probe (fast): 30 randomized-backtracking restarts × 2 000 nodes;
                  if no solution is found, the period is reported as infeasible.
        """
        ordered = self._heuristic.orderByMostConstrained(courses, period)
        partial = ExamSchedule(period)
        is_mode_feasible, mode_message = self._feasibility_checker.validate_courses(ordered)
        if not is_mode_feasible:
            return False, mode_message

        for course in ordered:
            candidates = self._valid_candidates_for(course, partial, period, constraint_validator)
            if not candidates:
                return False, (
                f"Course '{course.course_id}' has no valid date in period "
                f"'{period.period_id}' given the selected constraints."
            )

        for _ in range(30):
            node_count = [0]
            result = self._random_backtrack_first(
                ordered, partial, period, constraint_validator, node_count,
                node_limit=2_000,
            )
            if result is not None:
                return True, ""

        return False, (
            f"No feasible schedule was found for period '{period.period_id}' "
            f"with the selected constraints. "
            f"Try relaxing the constraints or expanding the date range."
        )

    # ── Randomized backtracking — find first solution fast ────────────────────

    _RBT_RESTARTS   = 200    # how many random restarts to attempt
    _RBT_NODE_LIMIT = 5_000  # max nodes explored per restart before giving up

    def _find_first_with_restarts(
        self,
        ordered: list[Course],
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> ExamSchedule | None:
        """
        Repeatedly run a randomized DFS until one complete schedule is found.
        Each restart shuffles date order at every node → different subtree explored.
        """
        partial = ExamSchedule(period)
        for _ in range(self._RBT_RESTARTS):
            node_count = [0]
            result = self._random_backtrack_first(
                ordered, partial, period, constraint_validator, node_count
            )
            if result is not None:
                return result
        return None

    def _random_backtrack_first(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        node_count: list,
        node_limit: int | None = None,
    ) -> ExamSchedule | None:
        """
        Single randomized DFS pass.  Returns the first complete schedule found,
        or None if the node limit is hit or the subtree is exhausted.
        """
        limit = node_limit if node_limit is not None else self._RBT_NODE_LIMIT
        if node_count[0] >= limit:
            return None

        if not remaining:
            return partial.copy()

        course, rest = self._select_mrv_course(remaining, partial, period, constraint_validator)
        candidates = self._valid_candidates_for(course, partial, period, constraint_validator)
        random.shuffle(candidates)

        for candidate in candidates:
            node_count[0] += 1
            placement = self._placement_factory.create(candidate)
            partial.assign(course, placement)
            if self._feasibility_checker.has_viable_assignment(
                rest, partial, period, constraint_validator, self._partial_constraint_checker
            ):
                result = self._random_backtrack_first(rest, partial, period, constraint_validator, node_count, limit)
                if result is not None:
                    partial.unassign(course)
                    return result
            partial.unassign(course)

        return None

    # ── Domain filtering ──────────────────────────────────────────────────────

    def _valid_candidates_for(
        self,
        course: Course,
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> list:
        """
        Return only candidates that pass both collision and partial constraints.

        In date-only mode candidates are date objects. In room mode they are
        ExamPlacement objects that already include time slot and room data.
        """
        return self._domain_provider.candidates_for(
            course,
            partial,
            period,
            constraint_validator,
            self._partial_constraint_checker,
        )

    def _valid_dates_for(
        self,
        course: Course,
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> list:
        """Backward-compatible alias for tests that inspect date-only domains."""
        return self._valid_candidates_for(course, partial, period, constraint_validator)

    # ── LCV — Least Constraining Value ───────────────────────────────────────

    def _lcv_sort_dates(
        self,
        candidates: list,
        course: Course,
        rest: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> list:
        """
        Sort dates so the least-constraining date comes first.
        Skipped when rest is empty or there is only one date candidate.
        """
        if not rest or len(candidates) <= 1:
            return candidates

        def lcv_score(candidate) -> int:
            placement = self._placement_factory.create(candidate)
            partial.assign(course, placement)
            total = sum(
                self._count_remaining_values(c, partial, period, constraint_validator)
                for c in rest
            )
            partial.unassign(course)
            return total

        return sorted(candidates, key=lcv_score, reverse=True)

    # ── MRV helpers ───────────────────────────────────────────────────────────

    _MRV_CAP = 8

    def _count_remaining_values(
        self,
        course: Course,
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> int:
        """Count valid dates still available for *course*, capped at _MRV_CAP."""
        count = 0
        for _ in self._valid_candidates_for(course, partial, period, constraint_validator):
            count += 1
            if count >= self._MRV_CAP:
                break
        return count

    def _select_mrv_course(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
    ) -> tuple[Course, list[Course]]:
        """
        Pick the course with the fewest remaining valid dates (MRV).
        Ties broken by static MCV pre-sort order (first in list wins).
        """
        best = min(
            remaining,
            key=lambda c: self._count_remaining_values(c, partial, period, constraint_validator),
        )
        rest = [c for c in remaining if c is not best]
        return best, rest

    # ── Backtracking (collect-all variant) ───────────────────────────────────

    def _backtrack(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        results: list[ExamSchedule],
    ) -> None:
        if not remaining:
            results.append(partial.copy())
            return

        course, rest = self._select_mrv_course(remaining, partial, period, constraint_validator)
        valid_candidates = self._valid_candidates_for(course, partial, period, constraint_validator)
        ordered_candidates = self._lcv_sort_dates(valid_candidates, course, rest, partial, period, constraint_validator)

        for candidate in ordered_candidates:
            placement = self._placement_factory.create(candidate)
            partial.assign(course, placement)
            if self._feasibility_checker.has_viable_assignment(
                rest, partial, period, constraint_validator, self._partial_constraint_checker
            ):
                self._backtrack(rest, partial, period, constraint_validator, results)
            partial.unassign(course)

    # ── Backtracking (streaming / generator variant) ──────────────────────────

    def _backtrack_stream(
        self,
        remaining: list[Course],
        partial: ExamSchedule,
        period: ExamPeriod,
        constraint_validator: ConstraintValidator,
        skip: ExamSchedule | None = None,
    ):
        """
        Recursive generator that yields valid schedules one at a time.

        skip: schedule already yielded by _find_first_with_restarts that must
              not be yielded again (compared only at leaf nodes).
        """
        if not remaining:
            result = partial.copy()
            if skip is None or not self._same_schedule(result, skip):
                yield result
            return

        course, rest = self._select_mrv_course(remaining, partial, period, constraint_validator)
        valid_candidates = self._valid_candidates_for(course, partial, period, constraint_validator)
        ordered_candidates = self._lcv_sort_dates(valid_candidates, course, rest, partial, period, constraint_validator)

        for candidate in ordered_candidates:
            placement = self._placement_factory.create(candidate)
            partial.assign(course, placement)
            if self._feasibility_checker.has_viable_assignment(
                rest, partial, period, constraint_validator, self._partial_constraint_checker
            ):
                yield from self._backtrack_stream(
                    rest, partial, period, constraint_validator, skip,
                )
            partial.unassign(course)

    @staticmethod
    def _same_schedule(left: ExamSchedule, right: ExamSchedule) -> bool:
        """Compare full placements so room-mode schedules are not collapsed by date."""
        left_items = {
            (period, course): placement
            for period, course, placement in left.iter_placements()
        }
        right_items = {
            (period, course): placement
            for period, course, placement in right.iter_placements()
        }
        return left_items == right_items
