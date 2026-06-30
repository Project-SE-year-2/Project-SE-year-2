from datetime import date
from unittest.mock import MagicMock, patch

from PyQt5.QtCore import QDate

from src.views.output_screen.output_screen import OutputScreen
from src.views.shared_components.calendar_widgets.month_grid import MonthGrid
from src.views.shared_components.calendar_widgets.output_day_cell import OutputDayCell
from src.models.enums import CalendarMode


class _FakeService:
    def get_period_schedule(self, period_id, index):
        return [
            {
                "course_number": "85001",
                "course_name": "Linear Algebra",
                "type": "Obligatory",
                "programs": ["83101"],
                "exam_date": "2026-01-01",
                "semester": "FALL",
                "moed": "Aleph",
            }
        ]

    def get_periods(self):
        return [
            {
                "id": "FALL_Aleph",
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 1, 31),
            }
        ]

    def get_schedule_count(self, period_id=None):
        return 1

    def get_sort_order(self):
        return []

    def get_constraint_settings(self):
        settings = MagicMock()
        settings.room_scheduling_enabled = False
        return settings

    def is_period_generating(self, period_id):
        return False

    def refresh_ranked_view(self):
        pass

    def get_best_score(self, period_id):
        return None

    def get_available_programs(self):
        return []


def test_month_grid_propagates_edit_mode_to_output_cells(qtbot):
    """MonthGrid should enable drag/drop on all output day cells in edit mode."""
    grid = MonthGrid(CalendarMode.OUTPUT)
    qtbot.addWidget(grid)

    grid.populate_output(
        year=2026,
        month=1,
        exams_by_date={},
        unavail_dates=set(),
        period_start=QDate(2026, 1, 1),
        period_end=QDate(2026, 1, 31),
    )

    grid.set_edit_mode(True)

    cells = grid.findChildren(OutputDayCell)
    assert cells
    assert all(cell._edit_mode is True for cell in cells)

    grid.set_edit_mode(False)

    assert all(cell._edit_mode is False for cell in cells)


def test_output_day_cell_emits_exam_moved_on_drop_logic(qtbot):
    """OutputDayCell should expose exam_moved signal for manual move flow."""
    cell = OutputDayCell(QDate(2026, 1, 2))
    qtbot.addWidget(cell)

    received = []
    cell.exam_moved.connect(lambda exam, source, target: received.append((exam, source, target)))

    exam = {
        "course_number": "85001",
        "course_name": "Linear Algebra",
        "exam_date": "2026-01-01",
    }

    cell.set_edit_mode(True)
    cell.exam_moved.emit(exam, "2026-01-01", "2026-01-02")

    assert received == [(exam, "2026-01-01", "2026-01-02")]


def test_output_screen_enter_edit_mode_captures_edit_snapshot(qtbot):
    """Entering edit mode should copy the currently visible schedule into editable rows."""
    screen = OutputScreen(_FakeService())
    qtbot.addWidget(screen)

    screen.enter_edit_mode()

    assert screen.is_editing() is True
    assert screen._original_edit_rows is not None
    assert screen._editable_rows[0]["course_number"] == "85001"
    assert screen._pending_manual_moves == []


def test_output_screen_exam_move_updates_temporary_rows(qtbot):
    """Dropping an exam should update only the temporary editable rows."""
    screen = OutputScreen(_FakeService())
    qtbot.addWidget(screen)

    screen.enter_edit_mode()

    exam = {
        "course_number": "85001",
        "course_name": "Linear Algebra",
        "exam_date": "2026-01-01",
    }

    with patch.object(screen, "_render_edit_rows") as render:
        screen._on_exam_moved(exam, "2026-01-01", "2026-01-02")

    assert screen._editable_rows[0]["exam_date"] == "2026-01-02"
    assert len(screen._pending_manual_moves) == 1
    assert screen._pending_manual_moves[0].course_number == "85001"
    assert screen._pending_manual_moves[0].source_date == "2026-01-01"
    assert screen._pending_manual_moves[0].target_date == "2026-01-02"
    render.assert_called_once()


def test_cancel_restores_original_edit_rows(qtbot):
    """Cancel should restore the original schedule snapshot and clear pending moves."""
    screen = OutputScreen(_FakeService())
    qtbot.addWidget(screen)

    screen.enter_edit_mode()

    exam = {
        "course_number": "85001",
        "course_name": "Linear Algebra",
        "exam_date": "2026-01-01",
    }

    screen._on_exam_moved(exam, "2026-01-01", "2026-01-02")
    assert screen._editable_rows[0]["exam_date"] == "2026-01-02"

    with patch.object(screen, "_render_edit_rows"):
        screen._on_cancel_edit_clicked()

    assert screen.is_editing() is False
    assert screen._editable_rows[0]["exam_date"] == "2026-01-01"
    assert screen._pending_manual_moves == []
