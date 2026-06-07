import unittest
from unittest.mock import MagicMock, patch
import sys

from datetime import date
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QShowEvent, QHideEvent  

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

        # Verify the dialog was instantiated with the correct exam data
        MockDialog.assert_called_once()
        call_kwargs = MockDialog.call_args
        self.assertEqual(call_kwargs[0][0], exam_data)   # first positional arg

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
    def test_calendar_exam_clicked_signal_is_connected(self, MockDialog):
        """The calendar's exam_clicked signal must be wired to _on_exam_clicked
        during OutputScreen initialisation.
        We verify this by emitting the signal directly and checking that
        _on_exam_clicked reacts (i.e. the dialog constructor is called)."""
        self.mock_service.get_available_programs.return_value = []
        exam_data = _make_minimal_exam()

        # Emit the signal as if a user clicked an exam cell on the calendar
        self.screen.calendar.exam_clicked.emit(exam_data)

        # If the signal is properly connected, the dialog should have been created
        MockDialog.assert_called_once()


# ---------------------------------------------------------------------------
# Module-level helper used by output_screen tests
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
