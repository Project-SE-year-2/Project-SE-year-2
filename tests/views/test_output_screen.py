import unittest
from unittest.mock import MagicMock, patch
import sys

from datetime import date
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QShowEvent, QHideEvent  
from PyQt5.QtCore import QPoint

# Ensure QApplication exists
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.output_screen.output_screen import OutputScreen
class TestOutputScreen(unittest.TestCase):

    def setUp(self):
        """Instantiate the screen with a mocked AppService."""
        self.mock_service = MagicMock()
        self.screen = OutputScreen(self.mock_service)

    def test_ui_components_exist(self):
        """Verify the layout instantiates all components required by EP-59."""
        self.assertIsNotNone(self.screen.back_btn)
        self.assertIsNotNone(self.screen.download_btn)
        self.assertIsNotNone(self.screen.calendar)
        self.assertIsNotNone(self.screen.navigator)

    def test_show_event_fetches_initial_batch(self):
        self.mock_service.get_schedule_batch.return_value = []
        self.mock_service.get_schedule_count.return_value = 1
        self.screen.showEvent(QShowEvent())
        
        self.mock_service.get_schedule_batch.assert_called_once_with(0, 10)

    def test_hide_event_stops_polling(self):
        """Verify that navigating away from the screen stops the background timer."""
        self.mock_service.get_schedule_count.return_value = 1
        
        self.screen.showEvent(QShowEvent())
        # Start the timer first
        self.screen.showEvent(QShowEvent())
        self.assertTrue(self.screen.poll_timer.isActive())
        
        # Trigger hideEvent
        self.screen.hideEvent(QHideEvent())
        
        # Verify timer is stopped
        self.assertFalse(self.screen.poll_timer.isActive())

    def test_polling_updates_counter(self):
        """Verify the timer callback queries the service and updates the UI label."""
        self.mock_service.get_schedule_count.return_value = 42
        self.screen._poll_schedule_count()
        self.mock_service.get_schedule_count.assert_called()
        self.assertEqual(self.screen.sched_label.text(), "Schedule 1 of 42")
        
    @patch('src.views.output_screen.output_screen.QFileDialog.getSaveFileName')
    @patch('src.views.output_screen.output_screen.QMessageBox.information')
    def test_download_button_triggers_export(self, _mock_message, mock_file_dialog):
        mock_path = 'C:/fake/path/schedule.csv'
        mock_file_dialog.return_value = (mock_path, '')

        self.screen.current_schedules = ["dummy"]
        self.screen.current_index = 0

        self.screen._on_download_clicked()
        self.mock_service.export_schedule.assert_called_once_with(0, mock_path)

    # ------------------------------------------------------------------
    # Tests for _get_program_names and _on_exam_clicked (EP-61)
    # ------------------------------------------------------------------

    def test_get_program_names_returns_id_to_name_mapping(self):
        """_get_program_names must convert the service's list of program dicts
        into a flat {id: name} dictionary that the dialog can look up directly."""
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
        """If get_available_programs() raises, _get_program_names must return {}
        instead of propagating the exception to the UI."""
        self.mock_service.get_available_programs.side_effect = RuntimeError("db error")
        result = self.screen._get_program_names()
        self.assertEqual(result, {})

    def test_get_program_names_returns_empty_dict_when_service_returns_empty(self):
        """When the service returns an empty list, _get_program_names must return {}."""
        self.mock_service.get_available_programs.return_value = []
        result = self.screen._get_program_names()
        self.assertEqual(result, {})

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_opens_day_detail_dialog(self, MockDialog):
        """_on_exam_clicked must construct a DayDetailDialog and call exec_() on it."""
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
        ]
        exam_data = {
            "course_number": "83111",
            "course_name":   "Algorithms",
            "type":          "Obligatory",
            "programs":      ["83101"],
            "exam_date":     "2026-06-10",
            "semester":      "FALL",
            "moed":          "Aleph",
        }

        self.screen._on_exam_clicked(exam_data)

        # Verify the dialog was instantiated and displayed
        MockDialog.assert_called_once()
        call_kwargs = MockDialog.call_args
        # Dialog is now called with keyword args; exams is a list containing the exam
        passed_exams = call_kwargs.kwargs.get("exams", [])
        self.assertIn(exam_data, passed_exams)

        # Verify the dialog was displayed modally
        MockDialog.return_value.exec_.assert_called_once()

    @patch("src.views.output_screen.output_screen.DayDetailDialog")
    def test_on_exam_clicked_passes_program_names_to_dialog(self, MockDialog):
        """_on_exam_clicked must forward the id→name mapping to DayDetailDialog
        so the chips can display readable program names instead of raw IDs."""
        self.mock_service.get_available_programs.return_value = [
            {"id": "83101", "name": "Computer Engineering"},
            {"id": "83104", "name": "Industrial Engineering"},
        ]
        exam_data = _make_minimal_exam()

        self.screen._on_exam_clicked(exam_data)

        # Extract the program_names kwarg that was passed to the dialog constructor
        call_kwargs = MockDialog.call_args[1]   # keyword arguments
        self.assertIn("program_names", call_kwargs)
        self.assertEqual(call_kwargs["program_names"], {
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
    def test_exams_day_clicked_opens_dialog_modally(self, MockDialog):
        """DayDetailDialog.exec_() must be called so the dialog is modal."""
        self.mock_service.get_available_programs.return_value = []
        # Emit the signal with a dummy exam list and anchor point
        self.screen._on_exam_day_clicked([_make_minimal_exam()], QPoint(0, 0))
        # Verify that exec_() was called to display the dialog modally
        MockDialog.return_value.exec_.assert_called_once()

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
    """Return a minimal exam_data dict sufficient for dialog construction tests."""
    return {
        "course_number": "83111",
        "course_name":   "Data Structures",
        "type":          "Obligatory",
        "programs":      ["83101"],
        "exam_date":     date(2026, 6, 10),
        "semester":      "FALL",
        "moed":          "Aleph",
    }


if __name__ == '__main__':
    unittest.main()
