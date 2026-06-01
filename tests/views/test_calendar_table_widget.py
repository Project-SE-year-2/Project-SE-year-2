# import unittest
# import sys
# from PyQt5.QtWidgets import QApplication
# from PyQt5.QtCore import Qt
# from PyQt5.QtGui import QColor

# # Ensure QApplication exists before testing QWidgets
# app = QApplication.instance()
# if app is None:
#     app = QApplication(sys.argv)

# from src.views.calendar_table_widget import CalendarTableWidget

# class TestCalendarTableWidget(unittest.TestCase):

#     def setUp(self):
#         """
#         Initialize instances for both required modes before each test.
#         """
#         self.period_widget = CalendarTableWidget(mode="period")
#         self.schedule_widget = CalendarTableWidget(mode="schedule")

#     def test_period_mode_coloring(self):
#         """
#         Verify that period mode applies the correct colors:
#         Green for allowed, Red for forbidden, Grey for outside.
#         """
#         dummy_data = [
#             {'date': '01', 'status': 'allowed'},
#             {'date': '02', 'status': 'forbidden'},
#             {'date': '03', 'status': 'outside'}
#         ]
        
#         self.period_widget.render_period_mode(dummy_data)
        
#         # Extract the background colors applied to the generated items
#         color_allowed = self.period_widget.item(0, 0).background().color().name()
#         color_forbidden = self.period_widget.item(0, 1).background().color().name()
#         color_outside = self.period_widget.item(0, 2).background().color().name()
        
#         self.assertEqual(color_allowed, '#2e7d32') # Green
#         self.assertEqual(color_forbidden, '#c62828') # Red
#         self.assertEqual(color_outside, '#424242') # Grey

#     def test_schedule_mode_truncation(self):
#         """
#         Verify that schedule mode shortens long course names to fit the grid.
#         """
#         dummy_data = [
#             {'date': '01', 'course_name': 'Short Name'},
#             {'date': '02', 'course_name': 'Advanced Systems Programming'}
#         ]
        
#         self.schedule_widget.render_schedule_mode(dummy_data)
        
#         item_short = self.schedule_widget.item(0, 0).text()
#         item_long = self.schedule_widget.item(0, 1).text()
        
#         # Verify short names remain untouched
#         self.assertIn('Short Name', item_short)
        
#         # Verify long names are truncated with an ellipsis
#         self.assertIn('Advanced Sys...', item_long)
#         self.assertTrue(len(item_long) < 25)

#     def test_day_clicked_signal_emission(self):
#         """
#         Verify that clicking a cell emits the day_clicked signal with the correct dictionary payload.
#         """
#         dummy_data = [{'date': '15', 'status': 'allowed', 'meta': 'test_data'}]
#         self.period_widget.render_period_mode(dummy_data)
        
#         # Create a mock slot to capture the emitted signal
#         emitted_data = []
#         def mock_slot(data):
#             emitted_data.append(data)
            
#         self.period_widget.day_clicked.connect(mock_slot)
        
#         # Simulate a click on the first cell
#         self.period_widget._handle_cell_click(0, 0)
        
#         # Assert the signal fired exactly once with the correct dictionary
#         self.assertEqual(len(emitted_data), 1)
#         self.assertEqual(emitted_data[0]['meta'], 'test_data')
#         self.assertEqual(emitted_data[0]['date'], '15')

# if __name__ == '__main__':
#     unittest.main()