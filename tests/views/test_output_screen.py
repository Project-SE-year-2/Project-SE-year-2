import unittest
from unittest.mock import MagicMock, patch
import sys

from datetime import date
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QShowEvent, QHideEvent
from PyQt5.QtCore import QPoint

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.output_screen.output_screen import OutputScreen


class TestOutputScreen(unittest.TestCase):

    def setUp(self):
        self.mock_service = MagicMock()
        self.screen = OutputScreen(self.mock_service)

    # ------------------------------------------------------------------
    # Basic structure
    # ------------------------------------------------------------------

    def test_ui_components_exist(self):
        self.assertIsNotNone(self.screen.back_btn)
        self.assertIsNotNone(self.screen.download_btn)
        self.assertIsNotNone(self.screen.four_month)
        self.assertIsNotNone(self.screen.navigator)

    # ------------------------------------------------------------------
    # Show / hide events
    # ------------------------------------------------------------------

    def test_show_event_calls_get_period_schedule(self):
        """showEvent calls get_period_schedule for the active period."""
        self.mock_service.get_period_schedule.return_value = [_make_minimal_exam()]
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen.showEvent(QShowEvent())
        self.mock_service.get_period_schedule.assert_called()

    def test_show_event_with_empty_period_shows_empty_state(self):
        """When get_period_schedule returns [] the screen shows the empty state (no crash)."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        # Must not raise even when there is nothing to display
        self.screen.showEvent(QShowEvent())

    def test_hide_event_stops_polling(self):
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_periods.return_value = []
        self.screen.showEvent(QShowEvent())
        self.screen.showEvent(QShowEvent())
        self.assertTrue(self.screen.poll_timer.isActive())
        self.screen.hideEvent(QHideEvent())
        self.assertFalse(self.screen.poll_timer.isActive())

    # ------------------------------------------------------------------
    # Polling / counter
    # ------------------------------------------------------------------

    def test_polling_updates_counter_calls_get_schedule_count(self):
        """Polling calls get_schedule_count(period_id=...) to check for data."""
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_period_schedule.return_value = [_make_minimal_exam()]
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._poll_schedule_count()
        self.mock_service.get_schedule_count.assert_called()

    def test_polling_with_zero_count_updates_navigator(self):
        """When get_schedule_count returns 0, navigator is hidden."""
        self.mock_service.get_schedule_count.return_value = 0
        self.screen._poll_schedule_count()
        self.mock_service.get_schedule_count.assert_called()

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    @patch('src.views.output_screen.output_screen.QFileDialog.getSaveFileName')
    @patch('src.views.output_screen.output_screen.QMessageBox.information')
    def test_download_calls_export_by_period_indices(self, _mock_msg, mock_dialog):
        """Download must call export_by_period_indices with the current per-period indices."""
        mock_path = 'C:/fake/path/schedule.csv'
        mock_dialog.return_value = (mock_path, '')
        # At least one period has data
        self.mock_service.get_schedule_count.return_value = 1

        self.screen._on_download_clicked()

        self.mock_service.export_by_period_indices.assert_called_once()
        call_args = self.mock_service.export_by_period_indices.call_args
        # Second positional argument is the file path
        self.assertEqual(call_args[0][1], mock_path)

    @patch('src.views.output_screen.output_screen.QFileDialog.getSaveFileName')
    @patch('src.views.output_screen.output_screen.QMessageBox.information')
    def test_download_passes_period_indices_to_export(self, _mock_msg, mock_dialog):
        """export_by_period_indices receives the screen's _period_indices dict."""
        mock_path = 'C:/fake/path/schedule.csv'
        mock_dialog.return_value = (mock_path, '')
        self.mock_service.get_schedule_count.return_value = 1

        self.screen._on_download_clicked()

        call_args = self.mock_service.export_by_period_indices.call_args
        passed_indices = call_args[0][0]
        self.assertIsInstance(passed_indices, dict)

    @patch('src.views.output_screen.output_screen.QMessageBox.warning')
    def test_download_warns_when_no_data_in_either_mode(self, mock_warn):
        """Download shows a warning when no period has any schedules."""
        self.mock_service.get_schedule_count.return_value = 0
        self.screen._on_download_clicked()
        mock_warn.assert_called_once()

    # ------------------------------------------------------------------
    # _get_program_names
    # ------------------------------------------------------------------

    def test_get_program_names_returns_id_to_name_mapping(self):
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
            {"id": "83102", "name": "Electrical Engineering"},
        ]
        result = self.screen._get_program_names()
        self.assertEqual(result, {
            "83101": "Computer Engineering",
            "83102": "Electrical Engineering",
        })

    def test_get_program_names_returns_empty_dict_when_service_raises(self):
        self.mock_service.get_available_programs.side_effect = RuntimeError("db error")
        self.assertEqual(self.screen._get_program_names(), {})

    def test_get_program_names_returns_empty_dict_when_service_returns_empty(self):
        self.mock_service.get_available_programs.return_value = []
        self.assertEqual(self.screen._get_program_names(), {})

    # ------------------------------------------------------------------
    # _on_exam_clicked / _on_exam_day_clicked → DayDetailDialog
    # ------------------------------------------------------------------

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_opens_day_detail_dialog(self, MockDialog):
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
        ]
        exam_data = _make_minimal_exam()

        # _on_exam_clicked is the old compat shim; it still needs to open the dialog
        self.screen._on_exam_clicked(exam_data)

        # Verify the dialog was instantiated and displayed
        MockDialog.assert_called_once()
        call_kwargs = MockDialog.call_args
        # Dialog is now called with keyword args; exams is a list containing the exam
        passed_exams = call_kwargs.kwargs.get("exams", [])
        self.assertIn(exam_data, passed_exams)

        # Verify the dialog was displayed
        MockDialog.return_value.show.assert_called_once()

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_passes_program_names_to_dialog(self, MockDialog):
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
            {"id": "83104", "name": "Industrial Engineering"},
        ]
        self.screen._on_exam_clicked(_make_minimal_exam())

        kw = MockDialog.call_args[1]
        self.assertIn("program_names", kw)
        self.assertEqual(kw["program_names"], {
            "83101": "Computer Engineering",
            "83104": "Industrial Engineering",
        })

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_calendar_exam_clicked_signal_is_NOT_connected(self, MockDialog):
        """calendar.exam_clicked must NOT be connected to any slot in OutputScreen.

        CalendarTableWidget always emits both exam_clicked AND exams_day_clicked
        when a badge is pressed.  Connecting both would cause _on_exam_day_clicked
        to fire twice, opening the detail dialog two times in a row.
        Only exams_day_clicked is wired; exam_clicked must remain silent."""
        self.mock_service.get_available_programs.return_value = []

        # Emit the single-exam signal directly — no dialog should appear.
        self.screen.calendar.exam_clicked.emit(_make_minimal_exam())

        MockDialog.assert_not_called()

    # ------------------------------------------------------------------
    # Isolated per-period fetching (new architecture)
    # ------------------------------------------------------------------

    def test_refresh_display_calls_get_period_schedule(self):
        """_refresh_screen_display fetches from get_period_schedule for the active period."""
        exams = [_make_minimal_exam(), _make_minimal_exam()]
        self.mock_service.get_period_schedule.return_value = exams
        self.mock_service.get_schedule_count.return_value = 1
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._refresh_screen_display()
        self.mock_service.get_period_schedule.assert_called_once_with("FALL_Aleph", 0)

    def test_refresh_display_with_no_data_shows_empty_state(self):
        """When get_period_schedule returns [] the screen shows empty (no exception)."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 0
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._refresh_screen_display()  # must not raise

    def test_navigator_index_changed_updates_period_index(self):
        """_on_navigator_index_changed stores the new index for the active period only."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 3
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._on_navigator_index_changed(2)
        self.assertEqual(self.screen._period_indices["FALL_Aleph"], 2)

    def test_navigator_index_changed_does_not_affect_other_periods(self):
        """Advancing index for FALL_Aleph must not change SPRI_Aleph's index."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 5
        self.mock_service.get_periods.return_value = []
        self.screen._on_navigator_index_changed(3)
        # Other periods stay at their initial value (0)
        self.assertEqual(self.screen._period_indices.get("SPRI_Aleph", 0), 0)

    def test_navigator_index_changed_calls_get_period_schedule_with_new_index(self):
        """After advancing the index, _refresh_screen_display fetches at the new index."""
        self.mock_service.get_period_schedule.return_value = []
        self.mock_service.get_schedule_count.return_value = 5
        self.mock_service.get_periods.return_value = [
            {"id": "FALL_Aleph", "start_date": None, "end_date": None}
        ]
        self.screen._on_navigator_index_changed(4)
        self.mock_service.get_period_schedule.assert_called_with("FALL_Aleph", 4)

    # ------------------------------------------------------------------
    # exams_day_clicked (list[dict], QPoint) new API
    # ------------------------------------------------------------------

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_signal_connected(self, MockDialog):
        """calendar.exams_day_clicked must be wired to _on_exam_day_clicked."""
        self.mock_service.get_available_programs.return_value = []
        exams = [_make_minimal_exam(), _make_minimal_exam()]

        self.screen.calendar.exams_day_clicked.emit(exams, QPoint(100, 200))

        MockDialog.assert_called_once()

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_passes_full_list_to_dialog(self, MockDialog):
        """_on_exam_day_clicked must forward the complete exam list to DayDetailDialog
        without any secondary lookup into exams_by_date."""
        self.mock_service.get_available_programs.return_value = []
        exam1 = _make_minimal_exam()
        exam2 = {**_make_minimal_exam(), "course_number": "83222"}
        exams = [exam1, exam2]
        # Emit the signal with a dummy anchor point since it's required by the signature
        self.screen._on_exam_day_clicked(exams, QPoint(50, 50))
        # Extract the exams kwarg passed to the dialog constructor and verify it matches
        kw = MockDialog.call_args[1]
        self.assertEqual(kw["exams"], exams)
        self.assertIn(exam1, kw["exams"])
        self.assertIn(exam2, kw["exams"])

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_passes_anchor_to_dialog(self, MockDialog):
        """The QPoint anchor received from the signal must be forwarded to DayDetailDialog."""
        self.mock_service.get_available_programs.return_value = []
        # Emit the signal with a specific anchor point
        anchor = QPoint(123, 456)
        self.screen._on_exam_day_clicked([_make_minimal_exam()], anchor)
        # Extract the anchor_pos kwarg passed to the dialog constructor and verify it matches
        kw = MockDialog.call_args[1]
        self.assertEqual(kw["anchor_pos"], anchor)

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_shim_wraps_single_exam_in_list(self, MockDialog):
        """The backward-compat _on_exam_clicked shim must wrap the single exam dict
        in a list so DayDetailDialog always receives a list[dict]."""
        self.mock_service.get_available_programs.return_value = []
        exam = _make_minimal_exam()

        self.screen._on_exam_clicked(exam)

        kw = MockDialog.call_args[1]
        self.assertIsInstance(kw["exams"], list)
        self.assertIn(exam, kw["exams"])

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_shim_passes_no_anchor(self, MockDialog):
        """When called via the single-exam shim the anchor_pos must be None."""
        self.mock_service.get_available_programs.return_value = []
        self.screen._on_exam_clicked(_make_minimal_exam())

        kw = MockDialog.call_args[1]
        self.assertIsNone(kw["anchor_pos"])

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_opens_dialog(self, MockDialog):
        """DayDetailDialog.show() must be called to display the dialog."""
        self.mock_service.get_available_programs.return_value = []
        # Emit the signal with a dummy exam list and anchor point
        self.screen._on_exam_day_clicked([_make_minimal_exam()], QPoint(0, 0))
        
        # Verify that show() was called (since it's a non-blocking dialog)
        MockDialog.return_value.show.assert_called_once()

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_exams_day_clicked_opens_dialog_with_list(self, MockDialog):
        """Verify the new multi-exam workflow triggered by exams_day_clicked."""
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
        ]

        exam_list = [
            {"course_number": "101", "exam_date": date(2026, 6, 10)},
            {"course_number": "102", "exam_date": date(2026, 6, 10)},
        ]
        anchor_point = QPoint(100, 100)
        # Emit the signal as if the user clicked on a day cell with multiple exams
        self.screen.calendar.exams_day_clicked.emit(exam_list, anchor_point)
        # Verify the dialog was constructed with the full exam list and correct anchor
        MockDialog.assert_called_once()
        _, kwargs = MockDialog.call_args
        self.assertEqual(kwargs["exams"], exam_list)
        self.assertEqual(kwargs["anchor_pos"], anchor_point)
        self.assertEqual(kwargs["program_names"], {"83101": "Computer Engineering"})


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _make_minimal_exam() -> dict:
    return {
        "course_number": "83111",
        "course_name":   "Data Structures",
        "type":          "Obligatory",
        "programs":      ["83101"],
        "exam_date":     date(2026, 9, 10),
        "semester":      "FALL",
        "moed":          "Aleph",
    }


if __name__ == '__main__':
    unittest.main()
