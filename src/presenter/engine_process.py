"""
Engine Process — runs solve_to_disk() in a fully separate OS process.

The Engine Process has its own Python interpreter and its own GIL, so
the UI is never blocked by algorithm computation regardless of how long
a period takes to solve.

Communication protocol (lightweight — no ExamSchedule objects cross the boundary):
  task_queue   : UI Process → Engine Process   {"type": "solve", "engine": ..., "tasks": ...}
                                                {"type": "stop"}
  notify_queue : Engine Process → UI Process   {"type": "period_done", "period_id": str}
                                                {"type": "all_done"}
                                                {"type": "error",      "message":  str}
"""

import multiprocessing as mp

from src.algorithm.period_results_writer import PeriodResultsWriter


# ------------------------------------------------------------------ #
# Worker — runs inside the Engine Process                             #
# ------------------------------------------------------------------ #

def _engine_worker(task_queue: mp.Queue, notify_queue: mp.Queue) -> None:
    """
    Entry point for the Engine Process.

    Blocks on task_queue waiting for work.  For each 'solve' message it
    calls engine.solve_to_disk() for every period in the task dict, writing
    results to the default data/results/ directory.  A 'period_done'
    notification is sent after each period so the UI can start displaying
    partial results immediately.
    """
    writer = PeriodResultsWriter()          # uses default data/results/ path

    while True:
        msg = task_queue.get()              # blocking wait

        if msg["type"] == "stop":
            break

        if msg["type"] == "solve":
            engine = msg["engine"]
            tasks  = msg["tasks"]

            try:
                for period, courses_dict in tasks.items():
                    pid = f"{period.semester.value}_{period.moed.value}"
                    engine.solve_to_disk(period, courses_dict, writer)
                    # Send only the period_id — no heavy objects through the queue
                    notify_queue.put({"type": "period_done", "period_id": pid})

                notify_queue.put({"type": "all_done"})

            except Exception as exc:
                notify_queue.put({"type": "error", "message": str(exc)})


# ------------------------------------------------------------------ #
# EngineProcess — manages the subprocess from the UI side             #
# ------------------------------------------------------------------ #

class EngineProcess:
    """
    Manages the lifecycle of the Engine subprocess.

    Created once in main.py and injected into AppService.  The subprocess
    starts immediately and waits for work via task_queue.  Being a daemon
    process it is automatically terminated when the main (UI) process exits.
    """

    def __init__(self) -> None:
        self._task_queue:   mp.Queue = mp.Queue()
        self._notify_queue: mp.Queue = mp.Queue()
        self._process = mp.Process(
            target=_engine_worker,
            args=(self._task_queue, self._notify_queue),
            daemon=True,        # dies with the UI process automatically
        )
        self._process.start()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def submit(self, engine, tasks: dict) -> None:
        """Send engine + scheduling tasks to the Engine Process."""
        self._task_queue.put({
            "type":   "solve",
            "engine": engine,
            "tasks":  tasks,
        })

    def get_notification(self) -> dict:
        """Block until the next notification arrives from the Engine Process."""
        return self._notify_queue.get()

    def stop(self) -> None:
        """Shut down the Engine Process gracefully (5-second timeout)."""
        self._task_queue.put({"type": "stop"})
        self._process.join(timeout=5)
        if self._process.is_alive():
            self._process.terminate()
