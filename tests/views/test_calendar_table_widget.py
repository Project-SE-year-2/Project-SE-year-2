import unittest
import datetime
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QDate

# Ensure QApplication exists before testing QWidgets
app = QApplication.instance() or QApplication(sys.argv)

from src.views.output_screen.calendar_table_widget import ScheduleCalendarWidget

class TestCalendarTableWidget(unittest.TestCase):

    def setUp(self):
        """Initialize the calendar widget before each test."""
        self.widget = ScheduleCalendarWidget()

    def test_update_schedule_handles_datetime_objects(self):
        """Verify that the calendar gracefully handles datetime.date objects without crashing."""
        schedule_data = [
            {
                "course_name": "Data Structures",
                "course_number": "101",
                "exam_date": datetime.date(2026, 1, 15) 
            }
        ]
        
        try:
            self.widget.update_schedule(schedule_data)
            success = True
        except Exception as e:
            success = False
            self.fail(f"update_schedule crashed with object: {e}")
            
        self.assertTrue(success)
        
        # Verify the data was stored correctly in the internal dictionary
        qdate = QDate(2026, 1, 15)
        self.assertIn(qdate, self.widget.exams_by_date)
        self.assertEqual(self.widget.exams_by_date[qdate][0]["course_name"], "Data Structures")
        
    def test_update_schedule_empty(self):
        """Verify the widget handles an empty schedule gracefully."""
        try:
            self.widget.update_schedule([])
            success = True
        except Exception:
            success = False
            
        self.assertTrue(success)
        self.assertEqual(len(self.widget.exams_by_date), 0)

    def test_exam_clicked_signal_emission(self):
        """Verify that clicking a valid date emits the exam_clicked signal with the correct payload."""
        schedule_data = [
            {
                "course_name": "Algorithms",
                "course_number": "102",
                "exam_date": datetime.date(2026, 5, 20)
            }
        ]
        self.widget.update_schedule(schedule_data)
        
        # Create a mock slot to capture the emitted signal
        emitted_data = []
        def mock_slot(data):
            emitted_data.append(data)
            
        self.widget.exam_clicked.connect(mock_slot)
        
        # Simulate a click on the specific date
        qdate = QDate(2026, 5, 20)
        self.widget._on_date_clicked(qdate)
        
        # Assert the signal fired exactly once with the correct dictionary
        self.assertEqual(len(emitted_data), 1)
        self.assertEqual(emitted_data[0]['course_name'], 'Algorithms')

    def test_update_schedule_multiple_exams_same_day(self):
        """Verify that multiple exams on the same day are grouped correctly in the dictionary."""
        schedule_data = [
            {"course_name": "Data Structures", "exam_date": datetime.date(2026, 6, 10)},
            {"course_name": "Algorithms", "exam_date": datetime.date(2026, 6, 10)}
        ]
        
        self.widget.update_schedule(schedule_data)
        
        qdate = QDate(2026, 6, 10)
        self.assertIn(qdate, self.widget.exams_by_date)
        # Verify there are 2 exams in the list for this date
        self.assertEqual(len(self.widget.exams_by_date[qdate]), 2)
        self.assertEqual(self.widget.exams_by_date[qdate][0]["course_name"], "Data Structures")
        self.assertEqual(self.widget.exams_by_date[qdate][1]["course_name"], "Algorithms")

    def test_update_schedule_string_dates(self):
        """Verify that the widget correctly parses string-formatted dates."""
        schedule_data = [
            {"course_name": "Operating Systems", "exam_date": "2026-07-15"}
        ]
        
        self.widget.update_schedule(schedule_data)
        
        qdate = QDate(2026, 7, 15)
        self.assertIn(qdate, self.widget.exams_by_date)

    def test_update_schedule_invalid_or_missing_date(self):
        """Verify that missing or invalid dates are gracefully ignored without crashing."""
        schedule_data = [
            {"course_name": "Course Without Date"}, # No exam_date key
            {"course_name": "Course With None Date", "exam_date": None} # None value
        ]
        
        try:
            self.widget.update_schedule(schedule_data)
            success = True
        except Exception:
            success = False
            
        self.assertTrue(success)
        # Verify nothing was added to the calendar
        self.assertEqual(len(self.widget.exams_by_date), 0)

    def test_empty_date_click_does_not_emit_signal(self):
        """Verify that clicking a date with no exams does not emit the exam_clicked signal."""
        # Create a mock slot to capture signals
        emitted_data = []
        def mock_slot(data):
            emitted_data.append(data)
            
        self.widget.exam_clicked.connect(mock_slot)
        
        # Simulate click on an empty date
        qdate = QDate(2026, 1, 1)
        self.widget._on_date_clicked(qdate)
        
        # Verify the slot was never called
        self.assertEqual(len(emitted_data), 0)
        
if __name__ == '__main__':
    unittest.main()