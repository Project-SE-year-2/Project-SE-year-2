"""
Tests for EP-165 / "Show Clear Error Messages For Invalid Moves".

Covers:
  - Inline error banner appears on invalid drop (not a blocking dialog).
  - Error message contains the course name and the violated rule's reason.
  - Invalid drop is reverted so the displayed schedule stays correct.
  - Valid drop clears any previous error.
  - Save shows banner (not QMessageBox) when validation fails.
  - Save keeps the user in edit mode after a failed attempt.
  - Cancel clears the error banner and restores the original schedule.
  - Exiting edit mode always clears the error banner.
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.views.output_screen.output_screen import OutputScreen


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exam(course_number="C1", course_name="Calculus 1",
          exam_date=date(2026, 1, 10), etype="Obligatory"):
    """Build a minimal exam row dict matching get_period_schedule() format."""
    return {
        "course_number": course_number,
        "course_name":   course_name,
        "exam_date":     exam_date,
        "type":          etype,
        "programs":      ["CS"],
    }


class _FakeService:
    """Minimal AppService stub for edit-mode tests."""

    def __init__(self, validate_errors=None):
        # validate_errors: list of error dicts to return, or [] for valid move
        self._validate_errors = validate_errors or []
        self.save_called = False
        self.saved_rows  = None

    # ── required stubs ──────────────────────────────────────────────────
    def get_schedule_count(self, period_id=None): return 1
    def get_period_schedule(self, period_id, index): return [_exam()]
    def get_periods(self):
        return [{
            "id": "FALL_Aleph",
            "start_date": date(2026, 1, 1),
            "end_date":   date(2026, 1, 31),
            "forbidden_days": [],
        }]
    def get_available_programs(self): return []
    def get_sort_order(self): return []
    def get_best_score(self, period_id): return None
    def is_period_generating(self, period_id): return False
    def refresh_ranked_view(self): pass
    def export_by_period_indices(self, period_indices, path): pass
    def get_constraint_settings(self):
        s = MagicMock()
        s.room_scheduling_enabled = False
        return s

    def validate_manual_move(self, period_id, exam_rows, moving_exam, target_date):
        return list(self._validate_errors)

    def save_manual_edit(self, period_id, index, edited_rows):
        self.save_called = True
        self.saved_rows  = edited_rows


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_service():
    return _FakeService(validate_errors=[])


@pytest.fixture
def invalid_service():
    return _FakeService(validate_errors=[
        {"rule": "period_bounds", "reason": "Jan 1 is outside the exam period."},
    ])


def _make_screen(qtbot, service):
    screen = OutputScreen(service)
    qtbot.addWidget(screen)
    screen.show()
    qtbot.waitExposed(screen)
    return screen


def _enter_edit(screen):
    """Enter edit mode with a known snapshot."""
    screen._original_edit_rows = [_exam()]
    screen._editable_rows      = [_exam()]
    screen._edit_period_start  = date(2026, 1, 1)
    screen._edit_period_end    = date(2026, 1, 31)
    screen._edit_mode = True
    screen._apply_edit_mode_ui()


# ---------------------------------------------------------------------------
# _format_move_errors unit tests
# ---------------------------------------------------------------------------

def test_format_move_errors_includes_course_name():
    """Each formatted error line must start with the course name."""
    errors = [
        {"rule": "period_bounds", "reason": "date is outside the period."},
        {"rule": "collision",     "reason": "collides with Physics."},
    ]
    result = OutputScreen._format_move_errors("Calculus 1", errors)
    assert "Calculus 1" in result
    assert "date is outside the period." in result
    assert "collides with Physics." in result


def test_format_move_errors_one_line_per_error():
    errors = [
        {"rule": "forbidden_date", "reason": "date is forbidden."},
        {"rule": "daily_cap",      "reason": "daily cap exceeded."},
    ]
    result = OutputScreen._format_move_errors("Math", errors)
    lines = [l for l in result.splitlines() if l.strip()]
    assert len(lines) == 2


# ---------------------------------------------------------------------------
# Invalid drop — banner visible, move reverted
# ---------------------------------------------------------------------------

def test_invalid_drop_shows_error_banner(qtbot, invalid_service):
    """An invalid exam move must display the inline error banner."""
    screen = _make_screen(qtbot, invalid_service)
    _enter_edit(screen)

    exam = _exam()
    screen._on_exam_moved(exam, "2026-01-10", "2026-01-01")

    assert screen._edit_error_banner.isVisible()


def test_invalid_drop_error_contains_course_name(qtbot, invalid_service):
    """Error banner text must identify the course that caused the violation."""
    screen = _make_screen(qtbot, invalid_service)
    _enter_edit(screen)

    exam = _exam(course_name="Calculus 1")
    screen._on_exam_moved(exam, "2026-01-10", "2026-01-01")

    banner_text = screen._edit_error_banner.message_label.text()
    assert "Calculus 1" in banner_text


def test_invalid_drop_reverts_exam_date(qtbot, invalid_service):
    """When a drop is invalid the exam date must stay at its original value."""
    screen = _make_screen(qtbot, invalid_service)
    _enter_edit(screen)

    original_date = date(2026, 1, 10)
    exam = _exam(exam_date=original_date)
    screen._editable_rows = [exam]
    screen._original_edit_rows = [_exam(exam_date=original_date)]

    screen._on_exam_moved(exam, "2026-01-10", "2026-01-01")

    # The row in _editable_rows must still carry the original date.
    row = screen._editable_rows[0]
    assert str(row["exam_date"]) == str(original_date)


# ---------------------------------------------------------------------------
# Valid drop — error banner hidden
# ---------------------------------------------------------------------------

def test_valid_drop_hides_error_banner(qtbot, valid_service):
    """A valid move must clear any previously shown error banner."""
    screen = _make_screen(qtbot, valid_service)
    _enter_edit(screen)

    # Manually show a stale error first.
    screen._edit_error_banner.show_error("stale error")
    assert screen._edit_error_banner.isVisible()

    exam = _exam()
    screen._on_exam_moved(exam, "2026-01-10", "2026-01-15")

    assert not screen._edit_error_banner.isVisible()


# ---------------------------------------------------------------------------
# Save with validation failure
# ---------------------------------------------------------------------------

def test_save_with_errors_shows_banner_not_dialog(qtbot, invalid_service, monkeypatch):
    """Failed save must show the inline banner, not a QMessageBox."""
    screen = _make_screen(qtbot, invalid_service)
    _enter_edit(screen)

    # Move exam so _find_moved_exams() returns it.
    screen._editable_rows = [_exam(exam_date=date(2026, 1, 20))]

    dialog_called = {"value": False}
    monkeypatch.setattr(
        "src.views.output_screen.output_screen.QMessageBox.warning",
        lambda *a, **kw: dialog_called.__setitem__("value", True),
    )

    screen._on_save_edit_clicked()

    assert not dialog_called["value"], "QMessageBox.warning must NOT be called"
    assert screen._edit_error_banner.isVisible()


def test_save_failure_keeps_edit_mode_active(qtbot, invalid_service):
    """A failed save must keep the user in edit mode so they can correct the move."""
    screen = _make_screen(qtbot, invalid_service)
    _enter_edit(screen)

    screen._editable_rows = [_exam(exam_date=date(2026, 1, 20))]
    screen._on_save_edit_clicked()

    assert screen.is_editing()


def test_save_failure_does_not_call_backend(qtbot, invalid_service):
    """When validation fails, save_manual_edit must not be called."""
    screen = _make_screen(qtbot, invalid_service)
    _enter_edit(screen)

    screen._editable_rows = [_exam(exam_date=date(2026, 1, 20))]
    screen._on_save_edit_clicked()

    assert not invalid_service.save_called


# ---------------------------------------------------------------------------
# Cancel clears error
# ---------------------------------------------------------------------------

def test_cancel_clears_error_banner(qtbot, invalid_service):
    """Cancelling edit mode must hide the error banner."""
    screen = _make_screen(qtbot, invalid_service)
    _enter_edit(screen)

    screen._edit_error_banner.show_error("some error")
    screen._on_cancel_edit_clicked()

    assert not screen._edit_error_banner.isVisible()


# ---------------------------------------------------------------------------
# Exit edit mode clears error
# ---------------------------------------------------------------------------

def test_exit_edit_mode_clears_error_banner(qtbot, valid_service):
    """Exiting edit mode (via save success path) must clear the error banner."""
    screen = _make_screen(qtbot, valid_service)
    _enter_edit(screen)

    screen._edit_error_banner.show_error("lingering error")
    screen.exit_edit_mode()

    assert not screen._edit_error_banner.isVisible()
