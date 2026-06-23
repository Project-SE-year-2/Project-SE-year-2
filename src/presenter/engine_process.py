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
from pathlib import Path

from src.algorithm.period_results_writer import PeriodResultsWriter
from src.algorithm.constraints.constraint_checker import ConstraintChecker
from src.algorithm.scoring.schedule_scorer import ScheduleScorer
from src.presenter.scores_database import ScoresDatabase


# ------------------------------------------------------------------ #
# Worker — runs inside the Engine Process                             #
# ------------------------------------------------------------------ #

def _solve_single_period(engine, period, courses_dict, root_path, notify_queue, constraint_settings):
    """Worker process target to solve a single period."""
    writer = PeriodResultsWriter(root_path=root_path)
    
    first_batch_sent = False
    def on_batch():
        nonlocal first_batch_sent
        if not first_batch_sent:
            notify_queue.put({"type": "period_ready", "period_id": period.period_id})
            first_batch_sent = True

    checker = ConstraintChecker(constraint_settings) if constraint_settings is not None else None

    scorer = ScheduleScorer.default()
    root = Path(root_path) if root_path else Path(__file__).parents[2] / "data" / "results"
    scores_db = ScoresDatabase(root / "scores.db")

    try:
        engine.solve_to_disk(period, courses_dict, writer, on_batch_written=on_batch, constraint_checker=checker, scorer=scorer, scores_db=scores_db)
    except Exception as exc:
        notify_queue.put({"type": "error", "message": f"Error in {period.period_id}: {str(exc)}"})
    finally:
        notify_queue.put({"type": "period_done", "period_id": period.period_id})

def _engine_worker(task_queue: mp.Queue, notify_queue: mp.Queue, results_path: str | None = None) -> None:
    """
    Entry point for the Engine Process.
    """
    import signal
    import sys

    def sigterm_handler(signum, frame):
        # Kill all running solver children before the worker dies
        for p in mp.active_children():
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    while True:
        msg = task_queue.get()              # blocking wait

        if msg["type"] == "stop":
            break

        if msg["type"] == "solve":
            engine = msg["engine"]
            tasks  = msg["tasks"]
            constraint_settings = msg.get("constraint_settings")

            try:
                import threading
                threads = []
                for period, courses_dict in tasks.items():
                    t = threading.Thread(
                        target=_solve_single_period,
                        args=(engine, period, courses_dict, results_path, notify_queue, constraint_settings),
                        daemon=True
                    )
                    threads.append(t)
                    t.start()
                    
                for t in threads:
                    t.join()

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

    def __init__(self, results_path: str | None = None) -> None:
        self._task_queue:   mp.Queue = mp.Queue()
        self._notify_queue: mp.Queue = mp.Queue()
        self._process = mp.Process(
            target=_engine_worker,
            args=(self._task_queue, self._notify_queue, results_path),
            daemon=True,        # dies with the UI process automatically
        )
        self._results_path = results_path
        self._process = None

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def start(self, engine, tasks: dict, constraint_settings=None) -> None:
        """Starts the background worker to solve all periods."""
        if self._process is None or not self._process.is_alive():
            # Recreate queues to purge any stale messages from a previous run
            self._task_queue = mp.Queue()
            self._notify_queue = mp.Queue()
            
            self._process = mp.Process(
                target=_engine_worker,
                args=(self._task_queue, self._notify_queue, self._results_path),
                daemon=True
            )
            self._process.start()

        # Send the tasks to the worker
        self._task_queue.put({
            "type": "solve",
            "engine": engine,
            "tasks": tasks,
            "constraint_settings": constraint_settings
        })

    def get_notification(self) -> dict:
        """Block until the next notification arrives from the Engine Process."""
        return self._notify_queue.get()

    def stop(self) -> None:
        """Forcefully stops the worker process and its children."""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join()
