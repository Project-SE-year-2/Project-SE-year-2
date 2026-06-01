# src/workers/generate_worker.py

from PyQt5.QtCore import QThread, pyqtSignal

class GenerateWorker(QThread):
    """
    Background worker thread to execute the heavy schedule generation algorithm.
    Prevents the main UI thread from freezing during execution.
    """
    
    # Define signals to communicate with the main UI thread
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service

    def run(self):
        """
        The main execution method of the thread.
        Calls the generation logic and emits appropriate signals upon completion.
        """
        try:
            # Execute the heavy algorithm via the service
            self.service.generate()
            
            # Emit success signal when done
            self.finished.emit()
            
        except Exception as e:
            # Emit error signal with the exception message if something fails
            self.error.emit(str(e))