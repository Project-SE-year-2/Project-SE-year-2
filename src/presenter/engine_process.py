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
import queue
import threading
from pathlib import Path

from src.algorithm.period_results_writer import PeriodResultsWriter
from src.algorithm.constraints.constraint_checker import ConstraintChecker
from src.algorithm.scoring.schedule_scorer import ScheduleScorer
from src.presenter.scores_database import ScoresDatabase


# ------------------------------------------------------------------ #
# Queue-backed scores proxy                                           #
# ------------------------------------------------------------------ #

class _QueueScoresProxy:
    """
    Drop-in replacement for ScoresDatabase used by solver threads.

    Instead of writing directly to SQLite, it puts rows onto a shared
    queue.Queue.  A single dedicated writer thread drains the queue and
    performs all actual DB writes, so SQLite never sees concurrent writers.
    """

    _SENTINEL = None   # poison pill that signals the writer to stop

    def __init__(self, score_queue: queue.Queue):
        self._q = score_queue

    def insert_batch(self, period_id: str, rows: list) -> None:
        """Forward a batch of score rows to the writer thread via the queue."""
        if rows:
            self._q.put((period_id, rows))

    def clear_period(self, period_id: str) -> None:
        """Forward a clear request to the writer thread."""
        self._q.put(("__clear__", period_id))


def _db_writer(score_queue: queue.Queue, db_path: Path) -> None:
    """
    Dedicated DB writer thread — the ONLY thread that touches scores.db.

    Drains score_queue until it receives the sentinel (None), writing each
    batch in a single transaction.  Because only this thread writes, SQLite
    never sees concurrent writers and no locking is needed.
    """
    with ScoresDatabase(db_path) as scores_db:
        while True:
            item = score_queue.get()
            if item is _QueueScoresProxy._SENTINEL:
                break
            period_id, payload = item
            if period_id == "__clear__":
                scores_db.clear_period(payload)
            else:
                scores_db.insert_batch(period_id, payload)


# ------------------------------------------------------------------ #
# Worker — runs inside the Engine Process                             #
# ------------------------------------------------------------------ #

def _solve_single_period(engine, period, courses_dict, writer, score_proxy, notify_queue, constraint_settings):
    """Solver thread: finds schedules for one period and queues their scores."""
    pid = period.period_id

    first_batch_sent = False

    def on_batch():
        nonlocal first_batch_sent
        if not first_batch_sent:
            notify_queue.put({"type": "period_ready", "period_id": pid})
            first_batch_sent = True

    print(f"[{period.period_id}] Starting generation. Constraint settings: {constraint_settings}")
    checker = ConstraintChecker(constraint_settings) if constraint_settings is not None else None
    scorer = ScheduleScorer.default()

    # ── Feasibility pre-check ─────────────────────────────────────────────────
    courses = list(courses_dict.keys())
    feasible, reason = engine.check_feasibility(period, courses)
    if not feasible:
        score_proxy.clear_period(pid)  # clear stale DB rows so UI doesn't poll for missing files
        notify_queue.put({"type": "period_infeasible", "period_id": pid, "reason": reason})
        notify_queue.put({"type": "period_done", "period_id": pid})
        return

    try:
        total = engine.solve_to_disk(
            period, courses_dict, writer,
            on_batch_written=on_batch,
            constraint_checker=checker,
            scorer=scorer,
            scores_db=score_proxy,
        )
    except Exception as exc:
        notify_queue.put({"type": "error", "message": f"Error in {pid}: {str(exc)}"})
    finally:
        notify_queue.put({"type": "period_done", "period_id": pid})


def _engine_worker(task_queue: mp.Queue, notify_queue: mp.Queue, results_path: str | None = None) -> None:
    """Entry point for the Engine Process."""
    import signal
    import sys

    def sigterm_handler(signum, frame):
        for p in mp.active_children():
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    _solving = False  # guard against duplicate solve messages

    while True:
        msg = task_queue.get()

        if msg["type"] == "stop":
            break

        if msg["type"] == "solve":
            if _solving:
                continue

            engine = msg["engine"]
            tasks  = msg["tasks"]
            constraint_settings = msg.get("constraint_settings")
            _solving = True

            try:
                root = Path(results_path) if results_path else Path(__file__).parents[2] / "data" / "results"
                writer = PeriodResultsWriter(root_path=results_path)

                # Queue shared between solver threads (producers) and writer thread (consumer).
                score_queue: queue.Queue = queue.Queue()
                score_proxy = _QueueScoresProxy(score_queue)

                # Start the single DB writer thread before any solvers.
                db_thread = threading.Thread(
                    target=_db_writer,
                    args=(score_queue, root / "scores.db"),
                    daemon=True,
                )
                db_thread.start()

                # Start one solver thread per period — they write to queue, never to DB.
                solver_threads = []
                for period, courses_dict in tasks.items():
                    t = threading.Thread(
                        target=_solve_single_period,
                        args=(engine, period, courses_dict, writer, score_proxy, notify_queue, constraint_settings),
                        daemon=True,
                    )
                    solver_threads.append(t)
                    t.start()

                # Wait for all solvers to finish, then shut down the writer.
                for t in solver_threads:
                    t.join()

                # Send sentinel to stop the writer thread cleanly.
                score_queue.put(_QueueScoresProxy._SENTINEL)
                db_thread.join()

                notify_queue.put({"type": "all_done"})

            except Exception as exc:
                notify_queue.put({"type": "error", "message": str(exc)})

            finally:
                _solving = False


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
