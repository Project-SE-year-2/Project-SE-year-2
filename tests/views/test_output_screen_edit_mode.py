import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import Qt

from src.views.output_screen.output_screen import OutputScreen


class _FakeService:
    """Minimal service stub needed to construct OutputScreen."""

    def get_schedule_count(self, period_id=None):
        return 1

    def get_period_schedule(self, period_id, index):
        return []

    def get_periods(self):
        return [
            {
                "id": "FALL_Aleph",
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            }
        ]

    def get_available_programs(self):
        return []

    def get_sort_order(self):
        return []

    def get_best_score(self, period_id):
        return None

    def is_period_generating(self, period_id):
        return False

    def refresh_ranked_view(self):
        pass

    def export_by_period_indices(self, period_indices, path):
        pass

    def get_constraint_settings(self):
        settings = MagicMock()
        settings.room_scheduling_enabled = False
        return settings

    def validate_manual_move(self, period_id, exam_rows, moving_exam, target_date):
        return []

    def save_manual_edit(self, period_id, index, edited_rows):
        pass


@pytest.fixture
def output_screen(qtbot):
    screen = OutputScreen(_FakeService())
    qtbot.addWidget(screen)
    screen.show()
    qtbot.waitExposed(screen)
    return screen


def test_default_state_is_view_mode(output_screen):
    """OutputScreen starts in normal view mode."""
    assert output_screen.is_editing() is False
    assert output_screen.edit_btn.isVisible() is True
    assert output_screen._edit_mode_banner.isVisible() is False


def test_enter_edit_mode_shows_banner_and_save_cancel(output_screen, qtbot):
    """Clicking EDIT enters edit mode and shows SAVE/CANCEL inside the edit banner."""
    qtbot.mouseClick(output_screen.edit_btn, Qt.LeftButton)

    assert output_screen.is_editing() is True
    assert output_screen.edit_btn.isVisible() is False
    assert output_screen.save_edit_btn.isVisible() is True
    assert output_screen.cancel_edit_btn.isVisible() is True
    assert output_screen._edit_mode_banner.isVisible() is True


def test_cancel_exits_edit_mode(output_screen, qtbot):
    """Clicking CANCEL exits edit mode."""
    output_screen.enter_edit_mode()

    qtbot.mouseClick(output_screen.cancel_edit_btn, Qt.LeftButton)

    assert output_screen.is_editing() is False
    assert output_screen.edit_btn.isVisible() is True
    assert output_screen._edit_mode_banner.isVisible() is False


def test_save_exits_edit_mode(output_screen, qtbot):
    """Clicking SAVE exits edit mode."""
    output_screen.enter_edit_mode()

    qtbot.mouseClick(output_screen.save_edit_btn, Qt.LeftButton)

    assert output_screen.is_editing() is False
    assert output_screen.edit_btn.isVisible() is True
    assert output_screen._edit_mode_banner.isVisible() is False


def test_sort_and_download_are_disabled_in_edit_mode(output_screen):
    """Edit mode disables actions that could replace/export the current schedule."""
    output_screen.enter_edit_mode()

    assert output_screen.sort_settings_btn.isEnabled() is False
    assert output_screen.download_btn.isEnabled() is False


def test_back_is_blocked_in_edit_mode(output_screen, qtbot):
    """Back navigation is blocked while edit mode is active."""
    output_screen.enter_edit_mode()

    with patch("src.views.output_screen.output_screen.QMessageBox.warning") as warning:
        with qtbot.assertNotEmitted(output_screen.switch_to_input):
            output_screen._on_back_clicked()

    warning.assert_called_once()
    assert output_screen.is_editing() is True


def test_period_ready_is_deferred_in_edit_mode(output_screen):
    """Incoming period-ready refresh is deferred while editing."""
    output_screen.enter_edit_mode()

    with patch.object(output_screen, "_refresh_screen_display") as refresh:
        output_screen._on_period_ready("FALL_Aleph")

    refresh.assert_not_called()
    assert output_screen._pending_refresh_while_editing is True


def test_deferred_refresh_runs_after_save(output_screen):
    """A deferred refresh is applied after leaving edit mode with SAVE."""
    output_screen.enter_edit_mode()
    output_screen._pending_refresh_while_editing = True

    with patch.object(output_screen, "_refresh_screen_display") as refresh:
        output_screen._on_save_edit_clicked()

    refresh.assert_called_once()
    assert output_screen.is_editing() is False
