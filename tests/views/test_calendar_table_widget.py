import unittest
import datetime
import sys
import pytest

from PyQt5.QtCore import QDate, QEvent, QPoint, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication


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
        """Verify that clicking a cell with an exam emits exam_clicked with the correct payload.
        Uses the eventFilter path because NoSelection mode suppresses the built-in clicked() signal."""
        
        schedule_data = [
            {
                "course_name": "Algorithms",
                "course_number": "102",
                "exam_date": datetime.date(2026, 5, 20)
            }
        ]
        self.widget.update_schedule(schedule_data)
        self.widget.setCurrentPage(2026, 5)  # navigate to May 2026

        emitted_data = []
        self.widget.exam_clicked.connect(emitted_data.append)

        # Locate the cell for May 20 and synthesise a left-click on it
        target = QDate(2026, 5, 20)
        model = self.widget._calendar_view.model()
        index = None
        for row in range(1, 7):
            for col in range(0, 7):
                idx = model.index(row, col)
                if self.widget.dateForIndex(idx) == target:
                    index = idx
                    break
            if index:
                break

        self.assertIsNotNone(index, "Could not find May 20 cell in the grid")
        pos = self.widget._calendar_view.visualRect(index).center()
        event = QMouseEvent(QEvent.MouseButtonPress, pos,
                            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.widget.eventFilter(self.widget._calendar_view.viewport(), event)

        # Assert the signal fired exactly once with the correct dictionary
        self.assertEqual(len(emitted_data), 1)
        self.assertEqual(emitted_data[0]["course_name"], "Algorithms")

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
        """Verify that clicking a cell with no exam does not emit the exam_clicked signal.
        Uses the eventFilter path, consistent with how real clicks are handled."""

        # Load no schedule so every cell is empty
        self.widget.update_schedule([])
        self.widget.setCurrentPage(2026, 1)

        emitted_data = []
        self.widget.exam_clicked.connect(emitted_data.append)

        # Pick an arbitrary data cell (row 1, col 0) and fire a left-click on it
        model = self.widget._calendar_view.model()
        index = model.index(1, 0)
        pos = self.widget._calendar_view.visualRect(index).center()
        event = QMouseEvent(QEvent.MouseButtonPress, pos,
                            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.widget.eventFilter(self.widget._calendar_view.viewport(), event)

        # Verify the slot was never called
        self.assertEqual(len(emitted_data), 0)

    # ------------------------------------------------------------------
    # Tests for the event-filter click mechanism (EP-61)
    # These cover the dateForIndex() helper and the eventFilter() handler
    # that replaced the built-in clicked() signal (which is suppressed by
    # NoSelection mode in PyQt5).
    # ------------------------------------------------------------------

    def test_date_for_index_returns_invalid_for_header_row(self):
        """Row 0 is the day-name header; dateForIndex must return an invalid QDate for it."""
        # Build a fake index at row=0 (header) using a real model from the internal view
        model = self.widget._calendar_view.model()
        index = model.index(0, 0)
        result = self.widget.dateForIndex(index)
        # An invalid QDate signals that the click should be ignored
        self.assertFalse(result.isValid())

    def test_date_for_index_first_day_of_month(self):
        """dateForIndex must map the cell that contains the 1st of the shown month correctly."""
        # Navigate to a known month so the grid layout is deterministic
        self.widget.setCurrentPage(2026, 6)  # June 2026
        first_day = QDate(2026, 6, 1)        # June 1 is a Monday → col=1, first week row=1

        model = self.widget._calendar_view.model()
        # Iterate all data rows (rows 1-6) and all columns to find the cell
        found = False
        for row in range(1, 7):
            for col in range(0, 7):
                index = model.index(row, col)
                if self.widget.dateForIndex(index) == first_day:
                    found = True
                    break
            if found:
                break

        self.assertTrue(found, "dateForIndex did not find June 1 2026 in any cell")

    def test_date_for_index_last_day_of_month(self):
        """dateForIndex must return June 30 for the cell containing the last day of June 2026."""
        self.widget.setCurrentPage(2026, 6)
        last_day = QDate(2026, 6, 30)

        model = self.widget._calendar_view.model()
        found = False
        for row in range(1, 7):
            for col in range(0, 7):
                index = model.index(row, col)
                if self.widget.dateForIndex(index) == last_day:
                    found = True
                    break
            if found:
                break

        self.assertTrue(found, "dateForIndex did not find June 30 2026 in any cell")

    def test_event_filter_emits_signal_for_exam_date(self):
        """eventFilter must emit exam_clicked when the user clicks a cell that has an exam."""
        exam_date = datetime.date(2026, 6, 10)
        self.widget.update_schedule([
            {"course_name": "Networks", "course_number": "201",
             "type": "Elective", "programs": ["83101"],
             "exam_date": exam_date, "semester": "FALL", "moed": "Aleph"}
        ])
        self.widget.setCurrentPage(2026, 6)

        emitted = []
        self.widget.exam_clicked.connect(emitted.append)

        # Find the model index whose dateForIndex equals the exam date
        qdate = QDate(2026, 6, 10)
        model = self.widget._calendar_view.model()
        target_index = None
        for row in range(1, 7):
            for col in range(0, 7):
                idx = model.index(row, col)
                if self.widget.dateForIndex(idx) == qdate:
                    target_index = idx
                    break
            if target_index is not None:
                break

        self.assertIsNotNone(target_index, "Could not locate the exam cell in the grid")

        # Build a synthetic mouse-press event at the cell's visual centre
        rect = self.widget._calendar_view.visualRect(target_index)
        pos = rect.center()
        mouse_event = QMouseEvent(
            QEvent.MouseButtonPress, pos,
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        # Invoke the event filter directly (avoids OS-level event dispatch)
        self.widget.eventFilter(self.widget._calendar_view.viewport(), mouse_event)

        self.assertEqual(len(emitted), 1, "exam_clicked should fire exactly once")
        self.assertEqual(emitted[0]["course_name"], "Networks")

    def test_event_filter_does_not_emit_for_empty_date(self):
        """eventFilter must NOT emit exam_clicked when the clicked cell has no exam."""
        # Load no schedule data so every cell is empty
        self.widget.update_schedule([])
        self.widget.setCurrentPage(2026, 6)

        emitted = []
        self.widget.exam_clicked.connect(emitted.append)

        # Pick an arbitrary data cell (row=1, col=0 → some day near the start of the grid)
        model = self.widget._calendar_view.model()
        index = model.index(1, 0)
        rect = self.widget._calendar_view.visualRect(index)
        pos = rect.center()

        mouse_event = QMouseEvent(
            QEvent.MouseButtonPress, pos,
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.widget.eventFilter(self.widget._calendar_view.viewport(), mouse_event)

        self.assertEqual(len(emitted), 0, "exam_clicked must not fire for an empty cell")

    def test_event_filter_ignores_non_left_button(self):
        """eventFilter must ignore right-click and middle-click events."""
        self.widget.update_schedule([
            {"course_name": "AI", "exam_date": datetime.date(2026, 6, 5)}
        ])
        self.widget.setCurrentPage(2026, 6)

        emitted = []
        self.widget.exam_clicked.connect(emitted.append)

        qdate = QDate(2026, 6, 5)
        model = self.widget._calendar_view.model()
        target_index = None
        for row in range(1, 7):
            for col in range(0, 7):
                idx = model.index(row, col)
                if self.widget.dateForIndex(idx) == qdate:
                    target_index = idx
                    break
            if target_index:
                break

        rect = self.widget._calendar_view.visualRect(target_index)
        pos = rect.center()

        # Right-click — must not emit
        right_click = QMouseEvent(
            QEvent.MouseButtonPress, pos,
            Qt.RightButton, Qt.RightButton, Qt.NoModifier
        )
        self.widget.eventFilter(self.widget._calendar_view.viewport(), right_click)

        self.assertEqual(len(emitted), 0, "Right-click must not trigger exam_clicked")

if __name__ == '__main__':
    unittest.main()