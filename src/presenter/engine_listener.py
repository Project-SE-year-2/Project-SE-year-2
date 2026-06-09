"""
EngineListener — QThread that bridges Engine Process notifications to Qt signals.

Replaces GenerateWorker.  Instead of running algorithm logic on the thread,
it simply calls service.generate_stream() which (when an EngineProcess is
attached) delegates all computation to the Engine Process.  The listener
then translates each yielded period_id into a Qt signal.

Signals emitted:
  period_ready(str) — a period finished; carries period_id
  finished(int)     — all periods done; carries total schedule count
  error(str)        — an exception occurred; carries the error message

The signal names are intentionally identical to the old GenerateWorker so
InputScreen requires no signal-connection changes.
"""

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

from src.presenter.i_app_service import IAppService


if _QT_AVAILABLE:

    class EngineListener(QThread):
        """
        Lightweight QThread that listens to generate_stream() and emits Qt signals.

        The heavy work (solve_to_disk) happens in the Engine Process.
        This thread only blocks on queue.get() — it never runs Python CPU work.
        """

        period_ready = pyqtSignal(str)   # period_id — identical API to GenerateWorker
        finished     = pyqtSignal(int)   # total combined schedule count
        error        = pyqtSignal(str)

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
    # Fallback stub — identical structure to the GenerateWorker fallback
    class EngineListener:  # type: ignore[no-redef]
        """Stub — PyQt5 not installed. Install PyQt5 to use the real listener."""

        def __init__(self, service: IAppService, parent=None):
            self._service = service

        def start(self) -> None:
            raise RuntimeError("PyQt5 is not installed. Cannot start EngineListener.")
