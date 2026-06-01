import unittest
from unittest.mock import MagicMock
import sys
from PyQt5.QtWidgets import QApplication

# A QApplication instance is strictly required before creating any QObject/QThread
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.workers.generate_worker import GenerateWorker

class TestGenerateWorker(unittest.TestCase):

    def setUp(self):
        """
        Set up the worker and mock service before each test.
        Connects the worker's signals to mock slots to verify emissions.
        """
        self.mock_service = MagicMock()
        self.worker = GenerateWorker(self.mock_service)
        
        # Create mock slots (listeners) to capture signal emissions
        self.mock_finished_slot = MagicMock()
        self.mock_error_slot = MagicMock()
        
        # Connect the worker's signals to our mock slots
        self.worker.finished.connect(self.mock_finished_slot)
        self.worker.error.connect(self.mock_error_slot)

    def test_run_success(self):
        """
        Verify that a successful generation emits the 'finished' signal
        and does not emit the 'error' signal.
        """
        # Execute the run method synchronously for testing purposes
        self.worker.run()
        
        # Verify the underlying service algorithm was invoked
        self.mock_service.generate.assert_called_once()
        
        # Verify the exact signals emitted
        self.mock_finished_slot.assert_called_once()
        self.mock_error_slot.assert_not_called()

    def test_run_error(self):
        """
        Verify that an exception raised during generation is caught
        and properly triggers the 'error' signal with the exact message.
        """
        # Configure the mocked service to simulate an algorithm failure
        error_msg = "Scheduling conflict detected. Cannot generate."
        self.mock_service.generate.side_effect = Exception(error_msg)
        
        # Execute the run method
        self.worker.run()
        
        # Verify the underlying service algorithm was invoked
        self.mock_service.generate.assert_called_once()
        
        # Verify the success signal was NEVER called
        self.mock_finished_slot.assert_not_called()
        
        # Verify the error signal was called with the exact exception message
        self.mock_error_slot.assert_called_once_with(error_msg)

if __name__ == '__main__':
    unittest.main()