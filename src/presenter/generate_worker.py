"""
GenerateWorker — QThread that drives streaming schedule generation.

Calls IAppService.generate_stream() on a background thread and emits Qt
signals so the UI can react to each period completing and to overall
completion or failure.
"""

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False


if _QT_AVAILABLE:

    class GenerateWorker(QThread):
        """
        Runs generate_stream() on a background QThread.

        Signals
        -------
        period_ready(str)   — emitted once per period with its period_id
        finished(int)       — emitted after all periods with total schedule count
        error(str)          — emitted if an exception is raised; finished is NOT emitted
        """

        period_ready = pyqtSignal(str)
        finished = pyqtSignal(int)
        error = pyqtSignal(str)

        def __init__(self, service, parent=None):
            super().__init__(parent)
            self._service = service

        def run(self) -> None:
            try:
                for period_id, _schedules in self._service.generate_stream():
                    self.period_ready.emit(period_id)
                count = self._service.get_schedule_count()
                self.finished.emit(count)
            except Exception as exc:
                self.error.emit(str(exc))

else:
    class GenerateWorker:  # type: ignore[no-redef]
        """Stub — PyQt5 not installed."""

        def __init__(self, service, parent=None):
            self._service = service

        def start(self) -> None:
            raise RuntimeError("PyQt5 is not installed. Cannot start GenerateWorker.")
