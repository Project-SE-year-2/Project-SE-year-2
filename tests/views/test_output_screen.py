import unittest
from unittest.mock import MagicMock, patch
import sys

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

if __name__ == '__main__':
    unittest.main()
