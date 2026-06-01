"""
QThread that drives streaming generation off the main thread.

Requires PyQt5. Install before use:
    pip install PyQt5

Flow:
    1. Worker calls service.generate_stream() — a generator.
    2. For each (period_id, schedules) yielded, emits period_ready(period_id).
    3. When the generator is exhausted, emits finished(total_combined_count).
    4. On any exception, emits error(message) instead.

The Output screen connects to period_ready to display each period's
schedules as they arrive. When finished fires, normal navigation and
export are enabled.
"""

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

from src.presenter.i_app_service import IAppService


if _QT_AVAILABLE:

    class GenerateWorker(QThread):
        """Background worker that streams per-period generation results."""

        # Emitted each time a period finishes — carries the period id
        period_ready = pyqtSignal(str)

        # Emitted when all periods are done and the Combiner has run
        # carries the total number of combined schedules
        finished = pyqtSignal(int)

        # Emitted on any exception during generation
        error = pyqtSignal(str)

        def __init__(self, service: IAppService, parent=None):
            super().__init__(parent)
            self._service = service

        def run(self) -> None:
            try:
                for period_id, _ in self._service.generate_stream():
                    self.period_ready.emit(period_id)
                self.finished.emit(self._service.get_schedule_count())
            except Exception as exc:
                self.error.emit(str(exc))

else:
    # Fallback stub so the rest of the codebase can import this module
    # without crashing when PyQt5 is absent (e.g. during unit tests).
    class GenerateWorker:  # type: ignore[no-redef]
        """Stub — PyQt5 not installed. Install PyQt5 to use the real worker."""

        def __init__(self, service: IAppService, parent=None):
            self._service = service

        def start(self):
            raise RuntimeError("PyQt5 is not installed. Cannot start GenerateWorker.")
