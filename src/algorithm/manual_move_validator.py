from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class MoveValidationError:
    # machine-readable key, e.g. "forbidden_date", "collision"
    rule: str   
    # human-readable explanation
    reason: str  

class ManualMoveValidator:
    """
    Validates whether a manual exam move is legal before it is saved.

    Checks are split into two layers:

    Always-on (regardless of ConstraintSettings):
        - period_bounds   - target date must lie within the period's date range
        - forbidden_date  - target date must not be explicitly forbidden
        - collision       - v1.0 baseline: two obligatory courses from the same
                            (program_id, year, semester) cannot share a date

    Settings-gated (only run when the corresponding flag is enabled):
        - daily_cap          - total exams on target date ≤ daily_cap_k
        - mandatory_gap      - obligatory courses sharing (program_id, year) must be
                               ≥ k days apart (mirrors MandatoryGapConstraint exactly)
        - all_gap            - all courses sharing (program_id, year) must be
                               ≥ k days apart (mirrors AllGapConstraint exactly)
        - elective_collision - per-program daily elective exam count must not exceed k+1
        - room_scheduling    - flags that room/time-slot re-assignment must be verified

    Gap checks require a ConstraintIndex (built during generation) to use the exact
    (program_id, year) groupings the solver uses. When no index is provided, the gap
    checks are skipped to avoid false positives on valid moves.
    """

    def validate(
        self,
        exam_rows: list[dict],
        moving_exam: dict,
        target_date: date,
        period: dict,
        settings,
        constraint_index=None,
    ) -> list[MoveValidationError]:
        """
        Return every validation error for moving `moving_exam` to `target_date`.
        An empty list means the move is valid.

        Args:
            exam_rows:        All exam rows for the period (from get_period_schedule).
            moving_exam:      The exam being moved (same dict format as exam_rows entries).
            target_date:      The proposed new date.
            period:           Period dict from get_periods() — must contain start_date,
                              end_date, forbidden_days, and optionally allowed_days.
            settings:         ConstraintSettings with enabled flags and k values.
            constraint_index: ConstraintIndex from the last generation run (may be None).
        """
        errors: list[MoveValidationError] = []

        moving_id = moving_exam["course_number"]
        other_rows = [r for r in exam_rows if r["course_number"] != moving_id]

        # ── Always-on ────────────────────────────────────────────────────────

        out_of_range = self._check_period_bounds(target_date, period)
        if out_of_range:
            # remaining checks are meaningless outside valid range
            return out_of_range  

        errors.extend(self._check_forbidden_date(target_date, period))
        errors.extend(self._check_basic_collision(moving_id, moving_exam["course_name"], target_date, other_rows, constraint_index))

        # ── Settings-gated ───────────────────────────────────────────────────

        if settings.daily_cap_enabled:
            errors.extend(self._check_daily_cap(target_date, other_rows, settings.daily_cap_k))

        if settings.mandatory_gap_enabled and constraint_index is not None:
            errors.extend(self._check_mandatory_gap(moving_id, moving_exam["course_name"], target_date, other_rows, settings.mandatory_gap_k, constraint_index))

        if settings.all_gap_enabled and constraint_index is not None:
            errors.extend(self._check_all_gap(moving_id, moving_exam["course_name"], target_date, other_rows, settings.all_gap_k, constraint_index))

        if settings.elective_conflicts_enabled:
            errors.extend(self._check_elective_collision(moving_exam, target_date, other_rows, settings.elective_conflicts_k))

        if settings.room_scheduling_enabled:
            errors.extend(self._check_room_scheduling(moving_exam["course_name"], target_date))

        return errors

    # ── Always-on checks ─────────────────────────────────────────────────────

    def _check_period_bounds(self, target_date: date, period: dict) -> list[MoveValidationError]:
        allowed_days: list[date] = period.get("allowed_days") or []
        if allowed_days:
            if target_date not in set(allowed_days):
                return [MoveValidationError(
                    rule="period_bounds",
                    reason=f"{target_date} is not an available date in this exam period.",
                )]
        else:
            start: date = period["start_date"]
            end: date   = period["end_date"]
            if not (start <= target_date <= end):
                return [MoveValidationError(
                    rule="period_bounds",
                    reason=f"{target_date} is outside the exam period ({start} – {end}).",
                )]
        return []

    def _check_forbidden_date(self, target_date: date, period: dict) -> list[MoveValidationError]:
        forbidden: set[date] = set(period.get("forbidden_days", []))
        if target_date in forbidden:
            return [MoveValidationError(
                rule="forbidden_date",
                reason=f"{target_date} is a forbidden date in this exam period.",
            )]
        return []

    def _check_basic_collision(
        self,
        moving_id: str,
        moving_name: str,
        target_date: date,
        other_rows: list[dict],
        constraint_index,
    ) -> list[MoveValidationError]:
        errors = []
        same_day = [r for r in other_rows if r["exam_date"] == target_date]
        for other in same_day:
            if self._do_collide(moving_id, other["course_number"], constraint_index, other):
                errors.append(MoveValidationError(
                    rule="collision",
                    reason=(
                        f"'{moving_name}' and '{other['course_name']}' are obligatory "
                        f"courses in the same program and cannot share the same date."
                    ),
                ))
        return errors

    def _do_collide(self, id_a: str, id_b: str, constraint_index, other_row: dict) -> bool:
        if constraint_index is not None:
            return constraint_index.do_collide_by_id(id_a, id_b)
        # Fallback when no index is available: both obligatory + share a program.
        # Conservative — may produce false positives across year boundaries.
        if other_row.get("type") != "Obligatory":
            return False
        return False  # cannot determine without index; skip rather than over-block

    # ── Settings-gated checks ─────────────────────────────────────────────────

    def _check_daily_cap(
        self,
        target_date: date,
        other_rows: list[dict],
        k: int,
    ) -> list[MoveValidationError]:
        count = sum(1 for r in other_rows if r["exam_date"] == target_date) + 1
        if count > k:
            return [MoveValidationError(
                rule="daily_cap",
                reason=(
                    f"Moving this exam to {target_date} would result in {count} exams "
                    f"on that day, exceeding the daily cap of {k}."
                ),
            )]
        return []

    def _check_mandatory_gap(
        self,
        moving_id: str,
        moving_name: str,
        target_date: date,
        other_rows: list[dict],
        k: int,
        constraint_index,
    ) -> list[MoveValidationError]:
        errors = []
        for other in other_rows:
            if not constraint_index.need_mandatory_gap(moving_id, other["course_number"]):
                continue
            gap = abs((other["exam_date"] - target_date).days)
            if gap < k:
                errors.append(MoveValidationError(
                    rule="mandatory_gap",
                    reason=(
                        f"'{moving_name}' would be {gap} day(s) from "
                        f"'{other['course_name']}' ({other['exam_date']}), "
                        f"below the mandatory gap of {k} days."
                    ),
                ))
        return errors

    def _check_all_gap(
        self,
        moving_id: str,
        moving_name: str,
        target_date: date,
        other_rows: list[dict],
        k: int,
        constraint_index,
    ) -> list[MoveValidationError]:
        errors = []
        for other in other_rows:
            if not constraint_index.need_all_gap(moving_id, other["course_number"]):
                continue
            gap = abs((other["exam_date"] - target_date).days)
            if gap < k:
                errors.append(MoveValidationError(
                    rule="all_gap",
                    reason=(
                        f"'{moving_name}' would be {gap} day(s) from "
                        f"'{other['course_name']}' ({other['exam_date']}), "
                        f"below the all-gap requirement of {k} days."
                    ),
                ))
        return errors

    def _check_elective_collision(
        self,
        moving_exam: dict,
        target_date: date,
        other_rows: list[dict],
        k: int,
    ) -> list[MoveValidationError]:
        """k=0 means at most 1 elective per program per day; k=1 means at most 2, etc."""
        if moving_exam.get("type") != "Elective":
            return []
        errors = []
        moved_programs = set(moving_exam.get("programs", []))
        for pid in moved_programs:
            elective_count = 1  # the moved exam itself
            for other in other_rows:
                if (
                    other["exam_date"] == target_date
                    and other.get("type") == "Elective"
                    and pid in other.get("programs", [])
                ):
                    elective_count += 1
            if max(0, elective_count - 1) > k:
                errors.append(MoveValidationError(
                    rule="elective_collision",
                    reason=(
                        f"Program {pid} would have {elective_count} elective exams "
                        f"on {target_date}, exceeding the allowed limit."
                    ),
                ))
        return errors

    def _check_room_scheduling(
        self,
        moving_name: str,
        target_date: date,
    ) -> list[MoveValidationError]:
        return [MoveValidationError(
            rule="room_scheduling",
            reason=(
                f"Room scheduling is enabled. Moving '{moving_name}' to {target_date} "
                f"requires verifying room and time-slot availability."
            ),
        )]