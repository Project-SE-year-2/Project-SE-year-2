"""
engine_listener.py
------------------
QThread that bridges the Engine Process event queue to Qt signals.

The Engine Process (and ScoresDatabase) post lightweight dict events onto a
multiprocessing.Queue.  This thread calls queue.get() — a *blocking* wait,
not a poll — so it consumes zero CPU between events.  Each event is
immediately translated into a pyqtSignal that Qt delivers to connected slots
on the main (UI) thread.

Event format produced by ScoresDatabase:
  {"event": "batch_written", "period_id": <str>}  — new scores committed
  {"event": "engine_done"}                         — generation finished

Signals emitted:
  batch_written(str)  — carries period_id; triggers WindowManager to check
                        whether a better schedule arrived
  engine_done()       — generation is complete; UI hides the spinner
  error(str)          — an unexpected exception; carries the message
"""

import multiprocessing

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False


if _QT_AVAILABLE:

    class EngineListener(QThread):
        """
        Lightweight QThread: blocks on queue.get(), emits a signal per event.

        No timers, no sleep(), no repeated checks — the thread is idle until
        the Engine Process puts something on the queue.
        """

        # Emitted every time ScoresDatabase commits a new batch of scores.
        # Carries the period_id so WindowManager can check only the relevant period.
        batch_written = pyqtSignal(str)

        # Emitted once when the Engine Process finishes all periods.
        engine_done = pyqtSignal()

        # Emitted if an unexpected exception is raised inside run().
        error = pyqtSignal(str)

        def __init__(self, queue: multiprocessing.Queue, parent=None):
            """
            Parameters
            ----------
            queue:
                The same multiprocessing.Queue that was passed to ScoresDatabase
                at construction time.  Both ends must reference the same Queue
                object (created before the Engine Process is spawned so it is
                inherited by the child process).
            """
            super().__init__(parent)
            self._queue = queue

        def run(self) -> None:
            """
            Main loop — runs on the background QThread, never on the UI thread.

            queue.get() blocks without consuming CPU until an event arrives.
            Each event dict is dispatched to the matching signal.  The loop
            exits cleanly on "engine_done" or on any unhandled exception.
            """
            try:
                while True:
                    # Blocking wait — no polling, no sleep() required.
                    event = self._queue.get()

                    if event.get("event") == "batch_written":
                        # Signal delivery crosses the thread boundary automatically;
                        # Qt queues the call and executes it on the main thread.
                        self.batch_written.emit(event["period_id"])

                    elif event.get("event") == "engine_done":
                        self.engine_done.emit()
                        break   # exit the loop; the thread finishes naturally

            except Exception as exc:
                self.error.emit(str(exc))

else:
    # Stub for environments without PyQt5 (CI, unit tests, server installs).
    class EngineListener:  # type: ignore[no-redef]
        """Stub — PyQt5 not installed."""

        def __init__(self, queue: multiprocessing.Queue, parent=None):
            self._queue = queue

        def start(self) -> None:
            raise RuntimeError("PyQt5 is not installed. Cannot start EngineListener.")
