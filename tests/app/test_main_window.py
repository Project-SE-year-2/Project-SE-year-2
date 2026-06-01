import unittest
import sys
from PyQt5.QtWidgets import QApplication

# Ensure QApplication exists before creating UI elements
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.main_window import MainWindow

class TestMainWindow(unittest.TestCase):

    def setUp(self):
        """
        Initialize the MainWindow instance before each test.
        """
        self.window = MainWindow()

    def test_stacked_widget_initialization(self):
        """
        Verify that InputScreen is on page 0 and OutputScreen is on page 1.
        """
        # The stack should contain exactly 2 widgets
        self.assertEqual(self.window.stacked_widget.count(), 2)
        
        # Verify the types of widgets at specific indices
        from views.input_screen.input_screen import input_screen
        from src.main_window import PlaceholderOutputScreen
        
        self.assertIsInstance(self.window.stacked_widget.widget(0), input_screen)
        self.assertIsInstance(self.window.stacked_widget.widget(1), PlaceholderOutputScreen)
        
        # The application should start on page 0
        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)

    def test_dependency_injection(self):
        """
        Verify that AppService.getInstance() is injected identically into both screens.
        """
        service_in_input = self.window.input_screen.service
        service_in_output = self.window.output_screen.service
        
        # Using assertIs to verify they point to the exact same memory instance
        self.assertIs(service_in_input, service_in_output)
        self.assertIs(service_in_input, self.window.service)

    def test_signal_wiring_switch_to_output(self):
        """
        Verify that emitting switch_to_output changes the page to index 1.
        """
        # Start at index 0
        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)
        
        # Emit the signal from the input screen
        self.window.input_screen.switch_to_output.emit()
        
        # Assert the view switched to index 1
        self.assertEqual(self.window.stacked_widget.currentIndex(), 1)

    def test_signal_wiring_switch_to_input(self):
        """
        Verify that emitting switch_to_input changes the page back to index 0.
        """
        # Manually force the stack to page 1 first
        self.window.stacked_widget.setCurrentIndex(1)
        
        # Emit the signal from the output screen
        self.window.output_screen.switch_to_input.emit()
        
        # Assert the view switched back to index 0
        self.assertEqual(self.window.stacked_widget.currentIndex(), 0)

if __name__ == '__main__':
    unittest.main()