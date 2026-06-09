import unittest
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.views.output_screen.schedule_navigator_widget import ScheduleNavigatorWidget

class TestScheduleNavigatorWidget(unittest.TestCase):

    def setUp(self):
        self.widget = ScheduleNavigatorWidget()

    def test_initial_state(self):
        """Initial state should show 'Schedule 0 of 0' and buttons disabled."""
        self.assertEqual(self.widget._current_index, 0)
        self.assertEqual(self.widget._total_count, 0)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 0 of 0")
        self.assertFalse(self.widget.prev_btn.isEnabled())
        self.assertFalse(self.widget.next_btn.isEnabled())

    def test_set_data_single_schedule(self):
        """When total=1, neither previous nor next should be enabled."""
        self.widget.set_data(0, 1)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 1 of 1")
        self.assertFalse(self.widget.prev_btn.isEnabled())
        self.assertFalse(self.widget.next_btn.isEnabled())

    def test_set_data_multiple_schedules_first_index(self):
        """When at index 0 of many, previous is disabled, next is enabled."""
        self.widget.set_data(0, 5)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 1 of 5")
        self.assertFalse(self.widget.prev_btn.isEnabled())
        self.assertTrue(self.widget.next_btn.isEnabled())

    def test_set_data_multiple_schedules_middle_index(self):
        """When at a middle index, both buttons are enabled."""
        self.widget.set_data(2, 5)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 3 of 5")
        self.assertTrue(self.widget.prev_btn.isEnabled())
        self.assertTrue(self.widget.next_btn.isEnabled())

    def test_set_data_multiple_schedules_last_index(self):
        """When at the last index, previous is enabled, next is disabled."""
        self.widget.set_data(4, 5)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 5 of 5")
        self.assertTrue(self.widget.prev_btn.isEnabled())
        self.assertFalse(self.widget.next_btn.isEnabled())

    def test_set_data_clamps_negative_index(self):
        """Passing a negative index clamps to 0."""
        self.widget.set_data(-2, 5)
        self.assertEqual(self.widget._current_index, 0)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 1 of 5")

    def test_set_data_clamps_out_of_bounds_index(self):
        """Passing an index >= total clamps to total - 1."""
        self.widget.set_data(10, 5)
        self.assertEqual(self.widget._current_index, 4)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 5 of 5")

    def test_set_data_clamps_negative_total(self):
        """Passing a negative total clamps to 0."""
        self.widget.set_data(1, -5)
        self.assertEqual(self.widget._total_count, 0)
        self.assertEqual(self.widget._current_index, 0)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 0 of 0")

    def test_next_btn_emits_signal_and_updates(self):
        """Clicking next advances the index and emits index_changed."""
        self.widget.set_data(0, 3)
        
        emitted_indices = []
        self.widget.index_changed.connect(emitted_indices.append)
        
        self.widget.next_btn.click()
        
        self.assertEqual(self.widget._current_index, 1)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 2 of 3")
        self.assertEqual(emitted_indices, [1])

    def test_prev_btn_emits_signal_and_updates(self):
        """Clicking previous decrements the index and emits index_changed."""
        self.widget.set_data(2, 3)
        
        emitted_indices = []
        self.widget.index_changed.connect(emitted_indices.append)
        
        self.widget.prev_btn.click()
        
        self.assertEqual(self.widget._current_index, 1)
        self.assertEqual(self.widget.counter_label.text(), "Schedule 2 of 3")
        self.assertEqual(emitted_indices, [1])

    def test_next_btn_ignored_when_at_end(self):
        """Clicking next when already at the end does nothing."""
        self.widget.set_data(2, 3)
        
        emitted_indices = []
        self.widget.index_changed.connect(emitted_indices.append)
        
        # Manually force the click handler directly, just in case Qt allows clicking a disabled button
        self.widget._on_next()
        
        self.assertEqual(self.widget._current_index, 2)
        self.assertEqual(emitted_indices, [])

    def test_prev_btn_ignored_when_at_start(self):
        """Clicking previous when already at the start does nothing."""
        self.widget.set_data(0, 3)
        
        emitted_indices = []
        self.widget.index_changed.connect(emitted_indices.append)
        
        self.widget._on_prev()
        
        self.assertEqual(self.widget._current_index, 0)
        self.assertEqual(emitted_indices, [])

if __name__ == '__main__':
    unittest.main()
