"""
engine_listener.py
------------------
QThread that bridges the Engine Process scores queue to Qt signals.

Responsibilities
----------------
This class has ONE responsibility: translate multiprocessing.Queue events
produced by ScoresDatabase into Qt signals for the UI thread.

It is NOT a replacement for GenerateWorker.  The two classes serve
completely different purposes:

  GenerateWorker  — drives schedule generation by calling
                    IAppService.generate_stream() and notifies the UI
                    when each period's generation is complete
                    (signals: period_ready, finished).

  EngineListener  — listens for scoring events posted to the queue by
                    ScoresDatabase after each batch is written to scores.db,
                    and notifies the UI that new ranked results are available
                    (signals: batch_written, engine_done).

Event contract (produced by ScoresDatabase)
-------------------------------------------
  {"event": "batch_written", "period_id": <str>, "count": <int>}
  {"event": "engine_done"}
  {"event": "_stop"}   <- internal sentinel for graceful shutdown

Graceful shutdown
-----------------
Call stop() from the main thread before the application exits.
stop() puts a sentinel event on the queue so run() unblocks and exits
cleanly instead of blocking forever on queue.get().
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
        # Carries period_id and count so WindowManager knows how many new
        # rows arrived without querying the database.
        batch_written = pyqtSignal(str, int)

        # Emitted once when the Engine Process finishes all periods.
        engine_done = pyqtSignal()

        # Emitted if an unexpected exception is raised inside run().
        error = pyqtSignal(str)

        def __init__(self, queue: multiprocessing.Queue, parent=None):
            super().__init__(parent)
            self._queue = queue

        def stop(self) -> None:
            """
            Request a graceful shutdown.

            Puts a sentinel event on the queue so run() unblocks immediately
            and the thread exits cleanly.  Safe to call from any thread.
            """
            self._queue.put({"event": "_stop"})

        def run(self) -> None:
            """
            Main loop — runs on the background QThread, never on the UI thread.

            queue.get() blocks without consuming CPU until an event arrives.
            Exits cleanly on engine_done, _stop sentinel, or any exception.
            """
            try:
                while True:
                    event = self._queue.get()

                    if event.get("event") == "batch_written":
                        period_id = event["period_id"]
                        count = event.get("count", 0)
                        self.batch_written.emit(period_id, count)

                    elif event.get("event") == "engine_done":
                        self.engine_done.emit()
                        break

                    elif event.get("event") == "_stop":
                        break

            except Exception as exc:
                self.error.emit(str(exc))

else:
    class EngineListener:  # type: ignore[no-redef]
        """Stub — PyQt5 not installed."""

        def __init__(self, queue: multiprocessing.Queue, parent=None):
            self._queue = queue

        def stop(self) -> None:
            pass

        def start(self) -> None:
            raise RuntimeError("PyQt5 is not installed. Cannot start EngineListener.")
