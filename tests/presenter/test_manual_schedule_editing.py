"""
EP-169 - Manual Schedule Editing Tests.

Covers the full manual editing flow at the presenter layer:

  1. Entering and exiting edit mode.
  2. A valid drag-and-drop move (course reassigned to a new date).
  3. Invalid move to a forbidden date.
  4. Invalid move that violates constraints (same-day obligatory collision).
  5. Save behavior (draft replaces the original in-memory).
  6. Cancel behavior (draft discarded, original untouched).
  7. Original schedule is not overwritten after a failed validation.

DataStore disk I/O is patched out so tests never touch real files.
"""

import pytest
from datetime import date
from copy import deepcopy

from src.presenter.app_service import AppService
from src.presenter.data_store import DataStore
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.exam_placement import ExamPlacement
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture(autouse=True)
def reset_singleton():
    AppService._instance = None
    yield
    AppService._instance = None


def _make_service(monkeypatch) -> AppService:
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)
    return AppService()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _make_course(course_id: str, program_id: str = "83101",
                 req_type: ReqType = ReqType.Obligatory) -> Course:
    course = Course(f"Course {course_id}", course_id, "Prof. X", Evaluation.Exam)
    course.add_requirement(
        ProgramRequirement(program_id, 1, Semester.FALL, req_type)
    )
    return course


def _make_period() -> ExamPeriod:
    """5-day FALL/Aleph period with Feb 3 forbidden."""
    p = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 2, 1), date(2026, 2, 5))
    p.possible_dates = [
        date(2026, 2, 1), date(2026, 2, 2),
        date(2026, 2, 4), date(2026, 2, 5),
    ]
    p.forbidden_days = [date(2026, 2, 3)]
    return p


def _setup_editing_scenario(monkeypatch):
    """Wire a service with a period, three courses, and one schedule.

    Schedule layout:
        CourseA (obligatory 83101) -> Feb 1
        CourseB (obligatory 83101) -> Feb 2
        CourseC (elective   83101) -> Feb 4

    Available dates: Feb 1, 2, 4, 5.  Forbidden: Feb 3.
    """
    svc = _make_service(monkeypatch)
    period = _make_period()
    svc._datastore.set_periods([period])
    svc._selected_programs = ["83101"]

    course_a = _make_course("A1", "83101", ReqType.Obligatory)
    course_b = _make_course("B1", "83101", ReqType.Obligatory)
    course_c = _make_course("C1", "83101", ReqType.Elective)

    schedule = ExamSchedule(period)
    schedule.assign(course_a, date(2026, 2, 1))
    schedule.assign(course_b, date(2026, 2, 2))
    schedule.assign(course_c, date(2026, 2, 4))

    pid = "FALL_Aleph"
    svc._results_by_period[pid] = [schedule]
    svc._current_indices[pid] = 0

    return svc, pid, schedule, course_a, course_b, course_c


# ------------------------------------------------------------------ #
# 1. Entering and exiting edit mode                                    #
# ------------------------------------------------------------------ #

class TestEnterExitEditMode:

    def test_enter_edit_mode_returns_formatted_rows(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        rows = svc.enter_edit_mode(pid, 0)
        assert isinstance(rows, list)
        assert len(rows) == 3
        course_ids = {r["course_number"] for r in rows}
        assert course_ids == {"A1", "B1", "C1"}

    def test_is_in_edit_mode_true_after_enter(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        assert svc.is_in_edit_mode() is False
        svc.enter_edit_mode(pid, 0)
        assert svc.is_in_edit_mode() is True

    def test_exit_edit_mode_clears_state(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.exit_edit_mode()
        assert svc.is_in_edit_mode() is False

    def test_cannot_enter_edit_mode_twice(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        with pytest.raises(ValueError, match="Already in edit mode"):
            svc.enter_edit_mode(pid, 0)

    def test_enter_edit_mode_invalid_index_raises(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        with pytest.raises(ValueError, match="No schedule found"):
            svc.enter_edit_mode(pid, 999)

    def test_get_edit_schedule_raises_when_not_editing(self, monkeypatch):
        svc, *_ = _setup_editing_scenario(monkeypatch)
        with pytest.raises(ValueError, match="Not in edit mode"):
            svc.get_edit_schedule()


# ------------------------------------------------------------------ #
# 2. Valid drag-and-drop move                                          #
# ------------------------------------------------------------------ #

class TestValidMove:

    def test_move_exam_to_available_date_succeeds(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        result = svc.move_exam("A1", date(2026, 2, 5))
        assert result["ok"] is True
        # Verify the draft reflects the move.
        rows = svc.get_edit_schedule()
        a1_row = [r for r in rows if r["course_number"] == "A1"][0]
        assert a1_row["exam_date"] == date(2026, 2, 5)

    def test_move_elective_to_same_day_as_obligatory_succeeds(self, monkeypatch):
        """An elective can share a day with an obligatory from the same program."""
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        # Move elective C1 to Feb 1 (where obligatory A1 is).
        result = svc.move_exam("C1", date(2026, 2, 1))
        assert result["ok"] is True

    def test_move_returns_updated_rows(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        result = svc.move_exam("A1", date(2026, 2, 5))
        assert "rows" in result
        assert len(result["rows"]) == 3


# ------------------------------------------------------------------ #
# 3. Invalid move to forbidden date                                    #
# ------------------------------------------------------------------ #

class TestForbiddenDateMove:

    def test_move_to_forbidden_date_fails(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        result = svc.move_exam("A1", date(2026, 2, 3))  # Feb 3 is forbidden
        assert result["ok"] is False
        assert "forbidden" in result["reason"].lower()

    def test_validate_move_to_forbidden_returns_false(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        ok, reason = svc.validate_move("A1", date(2026, 2, 3))
        assert ok is False
        assert "forbidden" in reason.lower()

    def test_move_outside_period_range_fails(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        result = svc.move_exam("A1", date(2026, 3, 1))  # outside Feb 1-5
        assert result["ok"] is False

    def test_draft_unchanged_after_forbidden_move(self, monkeypatch):
        """The draft must not be modified by a rejected move."""
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        rows_before = svc.get_edit_schedule()
        svc.move_exam("A1", date(2026, 2, 3))  # rejected
        rows_after = svc.get_edit_schedule()
        assert rows_before == rows_after


# ------------------------------------------------------------------ #
# 4. Invalid move that violates constraints                            #
# ------------------------------------------------------------------ #

class TestConstraintViolationMove:

    def test_same_day_obligatory_collision_rejected(self, monkeypatch):
        """Two obligatory courses in the same program cannot share a day."""
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        # A1 (obligatory 83101) is on Feb 1, B1 (obligatory 83101) is on Feb 2.
        # Moving B1 to Feb 1 would create a same-day collision.
        result = svc.move_exam("B1", date(2026, 2, 1))
        assert result["ok"] is False
        assert "collision" in result["reason"].lower()

    def test_validate_collision_returns_involved_course(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        ok, reason = svc.validate_move("B1", date(2026, 2, 1))
        assert ok is False
        assert "A1" in reason  # names the conflicting course

    def test_different_program_obligatories_can_share_day(self, monkeypatch):
        """Obligatory courses from DIFFERENT programs may share a day."""
        svc = _make_service(monkeypatch)
        period = _make_period()
        svc._datastore.set_periods([period])

        course_x = _make_course("X1", "83101", ReqType.Obligatory)
        course_y = _make_course("Y1", "83102", ReqType.Obligatory)  # different program

        schedule = ExamSchedule(period)
        schedule.assign(course_x, date(2026, 2, 1))
        schedule.assign(course_y, date(2026, 2, 2))

        pid = "FALL_Aleph"
        svc._results_by_period[pid] = [schedule]
        svc._current_indices[pid] = 0
        svc._selected_programs = ["83101", "83102"]

        svc.enter_edit_mode(pid, 0)
        result = svc.move_exam("Y1", date(2026, 2, 1))
        assert result["ok"] is True

    def test_draft_unchanged_after_constraint_violation(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        rows_before = svc.get_edit_schedule()
        svc.move_exam("B1", date(2026, 2, 1))  # collision - rejected
        rows_after = svc.get_edit_schedule()
        assert rows_before == rows_after


# ------------------------------------------------------------------ #
# 5. Save behavior                                                    #
# ------------------------------------------------------------------ #

class TestSaveEdit:

    def test_save_commits_draft_to_results(self, monkeypatch):
        svc, pid, original, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.move_exam("A1", date(2026, 2, 5))
        assert svc.save_edit() is True

        # After save, the in-memory schedule should reflect the move.
        saved = svc._results_by_period[pid][0]
        a1_date = None
        for course, placement in saved.placements.items():
            if course.course_id == "A1":
                a1_date = placement.date
        assert a1_date == date(2026, 2, 5)

    def test_save_exits_edit_mode(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.save_edit()
        assert svc.is_in_edit_mode() is False

    def test_save_without_edit_mode_returns_false(self, monkeypatch):
        svc, *_ = _setup_editing_scenario(monkeypatch)
        assert svc.save_edit() is False

    def test_save_without_changes_preserves_original(self, monkeypatch):
        """Saving immediately (no moves) should leave the schedule intact."""
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        rows_before = svc.get_period_schedule(pid, 0)
        svc.enter_edit_mode(pid, 0)
        svc.save_edit()
        rows_after = svc.get_period_schedule(pid, 0)
        assert rows_before == rows_after


# ------------------------------------------------------------------ #
# 6. Cancel behavior                                                  #
# ------------------------------------------------------------------ #

class TestCancelEdit:

    def test_cancel_discards_draft(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.move_exam("A1", date(2026, 2, 5))  # valid move
        svc.cancel_edit()
        assert svc.is_in_edit_mode() is False

        # The original schedule must still have A1 on Feb 1.
        original = svc._results_by_period[pid][0]
        a1_date = None
        for course, placement in original.placements.items():
            if course.course_id == "A1":
                a1_date = placement.date
        assert a1_date == date(2026, 2, 1)

    def test_cancel_after_multiple_moves_reverts_all(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.move_exam("A1", date(2026, 2, 5))
        svc.move_exam("C1", date(2026, 2, 2))
        svc.cancel_edit()

        original = svc._results_by_period[pid][0]
        dates = {c.course_id: pl.date for c, pl in original.placements.items()}
        assert dates["A1"] == date(2026, 2, 1)
        assert dates["C1"] == date(2026, 2, 4)

    def test_exit_edit_mode_is_alias_for_cancel(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.move_exam("A1", date(2026, 2, 5))
        svc.exit_edit_mode()
        assert svc.is_in_edit_mode() is False
        original = svc._results_by_period[pid][0]
        a1_date = None
        for course, placement in original.placements.items():
            if course.course_id == "A1":
                a1_date = placement.date
        assert a1_date == date(2026, 2, 1)


# ------------------------------------------------------------------ #
# 7. Original schedule not overwritten after failed validation         #
# ------------------------------------------------------------------ #

class TestOriginalPreservedOnFailure:

    def test_failed_move_does_not_touch_original(self, monkeypatch):
        """The original (stored) schedule must NEVER be modified by move_exam,
        whether the move succeeds or fails. Only save_edit() commits."""
        svc, pid, original, *_ = _setup_editing_scenario(monkeypatch)
        original_dates = {
            c.course_id: pl.date for c, pl in original.placements.items()
        }

        svc.enter_edit_mode(pid, 0)

        # Failed move (collision)
        svc.move_exam("B1", date(2026, 2, 1))
        # Failed move (forbidden)
        svc.move_exam("A1", date(2026, 2, 3))
        # Successful move (but not saved yet)
        svc.move_exam("A1", date(2026, 2, 5))

        # The stored schedule in _results_by_period must be unchanged.
        stored = svc._results_by_period[pid][0]
        stored_dates = {
            c.course_id: pl.date for c, pl in stored.placements.items()
        }
        assert stored_dates == original_dates

        # Cancel to confirm the original is truly untouched.
        svc.cancel_edit()
        final = svc._results_by_period[pid][0]
        final_dates = {
            c.course_id: pl.date for c, pl in final.placements.items()
        }
        assert final_dates == original_dates

    def test_sequence_of_valid_then_invalid_keeps_valid_in_draft(self, monkeypatch):
        """A valid move followed by a rejected one: the valid move persists in
        the draft, but the rejected one does not."""
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)

        # Valid: A1 Feb 1 -> Feb 5
        r1 = svc.move_exam("A1", date(2026, 2, 5))
        assert r1["ok"] is True

        # Invalid: B1 Feb 2 -> Feb 5 (collision with A1 now on Feb 5)
        r2 = svc.move_exam("B1", date(2026, 2, 5))
        assert r2["ok"] is False

        # Draft should show A1 on Feb 5, B1 still on Feb 2.
        rows = svc.get_edit_schedule()
        row_map = {r["course_number"]: r["exam_date"] for r in rows}
        assert row_map["A1"] == date(2026, 2, 5)
        assert row_map["B1"] == date(2026, 2, 2)


# ------------------------------------------------------------------ #
# Edge cases                                                           #
# ------------------------------------------------------------------ #

class TestEdgeCases:

    def test_validate_move_not_in_edit_mode(self, monkeypatch):
        svc, *_ = _setup_editing_scenario(monkeypatch)
        ok, reason = svc.validate_move("A1", date(2026, 2, 5))
        assert ok is False
        assert "not in edit mode" in reason.lower()

    def test_move_nonexistent_course_fails(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        result = svc.move_exam("NOPE", date(2026, 2, 5))
        assert result["ok"] is False
        assert "not found" in result["reason"].lower()

    def test_move_to_same_date_is_valid(self, monkeypatch):
        """Moving a course to its current date is a no-op but should succeed."""
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        result = svc.move_exam("A1", date(2026, 2, 1))  # already on Feb 1
        assert result["ok"] is True

    def test_can_reenter_edit_mode_after_cancel(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.cancel_edit()
        # Should be able to enter again without error.
        rows = svc.enter_edit_mode(pid, 0)
        assert len(rows) == 3

    def test_can_reenter_edit_mode_after_save(self, monkeypatch):
        svc, pid, *_ = _setup_editing_scenario(monkeypatch)
        svc.enter_edit_mode(pid, 0)
        svc.save_edit()
        rows = svc.enter_edit_mode(pid, 0)
        assert len(rows) == 3