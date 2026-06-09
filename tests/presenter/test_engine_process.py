"""
Tests for EngineProcess — the multiprocessing worker that runs
solve_to_disk() in a separate OS process.

These tests verify the process lifecycle (start, submit, notify, stop)
and the communication protocol over multiprocessing.Queue.
"""

import multiprocessing as mp
import time

import pytest

from src.presenter.engine_process import _engine_worker, EngineProcess


# ================================================================== #
# _engine_worker — protocol-level tests (no real engine needed)        #
# ================================================================== #

def test_engine_worker_stop_message_exits_loop(tmp_path):
    """Sending a 'stop' message causes the worker to exit cleanly."""
    task_q = mp.Queue()
    notify_q = mp.Queue()

    task_q.put({"type": "stop"})

    proc = mp.Process(target=_engine_worker, args=(task_q, notify_q, str(tmp_path)), daemon=True)
    proc.start()
    proc.join(timeout=5)

    assert not proc.is_alive(), "Worker did not exit after 'stop' message"


def test_engine_worker_solve_sends_period_done_and_all_done(tmp_path):
    """A 'solve' message causes 'period_done' per period then 'all_done'."""
    from datetime import date
    from src.models.course import Course
    from src.models.exam_period import ExamPeriod
    from src.models.program_requirement import ProgramRequirement
    from src.models.enums import Evaluation, Semester, Moed, ReqType
    from src.algorithm.constraint_index import ConstraintIndex
    from src.algorithm.exam_period_catalog import ExamPeriodCatalog
    from src.algorithm.basic_version_validator import BasicVersionValidator
    from src.algorithm.constraint_validator import ConstraintValidator
    from src.algorithm.scheduling_engine import SchedulingEngine

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    c1 = Course("C1", "10001", "Prof. A", Evaluation.Exam)
    c1.add_requirement(ProgramRequirement("10001", 1, Semester.FALL, ReqType.Obligatory))

    index = ConstraintIndex()
    index.build([c1], ["10001"])
    catalog = ExamPeriodCatalog([fall])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)), catalog, index,
    )

    tasks = {fall: {c1: ["10001"]}}

    task_q = mp.Queue()
    notify_q = mp.Queue()

    task_q.put({"type": "solve", "engine": engine, "tasks": tasks})
    task_q.put({"type": "stop"})

    proc = mp.Process(target=_engine_worker, args=(task_q, notify_q, str(tmp_path)), daemon=True)
    proc.start()
    proc.join(timeout=10)

    messages = []
    while not notify_q.empty():
        messages.append(notify_q.get_nowait())

    types = [m["type"] for m in messages]
    assert "period_done" in types, f"Expected 'period_done', got {types}"
    assert types[-1] == "all_done", f"Last message should be 'all_done', got {types[-1]}"

    # Verify the period_done message carries the correct period_id
    period_done_msg = [m for m in messages if m["type"] == "period_done"][0]
    assert period_done_msg["period_id"] == "FALL_Aleph"


class FakeEngine:
    def solve_to_disk(self, period, courses_dict, writer):
        raise RuntimeError("out of memory")


def test_engine_worker_error_notification_on_solver_failure(tmp_path):
    """When the engine raises, the worker sends an 'error' notification."""
    from datetime import date
    from src.models.exam_period import ExamPeriod
    from src.models.enums import Semester, Moed

    fake_engine = FakeEngine()

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    fall.possible_dates = [date(2026, 1, 1)]

    tasks = {fall: {}}

    task_q = mp.Queue()
    notify_q = mp.Queue()

    task_q.put({"type": "solve", "engine": fake_engine, "tasks": tasks})
    task_q.put({"type": "stop"})

    proc = mp.Process(target=_engine_worker, args=(task_q, notify_q, str(tmp_path)), daemon=True)
    proc.start()
    proc.join(timeout=10)

    messages = []
    while not notify_q.empty():
        messages.append(notify_q.get_nowait())

    error_msgs = [m for m in messages if m["type"] == "error"]
    assert len(error_msgs) >= 1, f"Expected an 'error' message, got {[m['type'] for m in messages]}"
    assert "out of memory" in error_msgs[0]["message"]


# ================================================================== #
# EngineProcess — lifecycle tests                                      #
# ================================================================== #

def test_engine_process_starts_and_stops_gracefully(tmp_path):
    """EngineProcess starts a daemon process and stop() terminates it."""
    ep = EngineProcess(results_path=str(tmp_path))

    assert ep._process.is_alive(), "Engine process should be alive after creation"

    ep.stop()

    # Give it a moment to terminate
    ep._process.join(timeout=3)
    assert not ep._process.is_alive(), "Engine process should be dead after stop()"


def test_engine_process_submit_and_receive_notification(tmp_path):
    """submit() sends work and get_notification() receives the result."""
    from datetime import date
    from src.models.course import Course
    from src.models.exam_period import ExamPeriod
    from src.models.program_requirement import ProgramRequirement
    from src.models.enums import Evaluation, Semester, Moed, ReqType
    from src.algorithm.constraint_index import ConstraintIndex
    from src.algorithm.exam_period_catalog import ExamPeriodCatalog
    from src.algorithm.basic_version_validator import BasicVersionValidator
    from src.algorithm.constraint_validator import ConstraintValidator
    from src.algorithm.scheduling_engine import SchedulingEngine

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 2))
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]

    c1 = Course("C1", "10001", "Prof. A", Evaluation.Exam)
    c1.add_requirement(ProgramRequirement("10001", 1, Semester.FALL, ReqType.Obligatory))

    index = ConstraintIndex()
    index.build([c1], ["10001"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )

    ep = EngineProcess(results_path=str(tmp_path))
    try:
        ep.submit(engine, {fall: {c1: ["10001"]}})

        # Collect all notifications
        notifications = []
        while True:
            msg = ep.get_notification()
            notifications.append(msg)
            if msg["type"] in ("all_done", "error"):
                break

        types = [n["type"] for n in notifications]
        assert "period_done" in types, f"Got notifications: {notifications}"
        assert "all_done" in types
    finally:
        ep.stop()


def test_engine_process_multiple_submits(tmp_path):
    """Two sequential submits both complete without corruption."""
    from datetime import date
    from src.models.course import Course
    from src.models.exam_period import ExamPeriod
    from src.models.program_requirement import ProgramRequirement
    from src.models.enums import Evaluation, Semester, Moed, ReqType
    from src.algorithm.constraint_index import ConstraintIndex
    from src.algorithm.exam_period_catalog import ExamPeriodCatalog
    from src.algorithm.basic_version_validator import BasicVersionValidator
    from src.algorithm.constraint_validator import ConstraintValidator
    from src.algorithm.scheduling_engine import SchedulingEngine

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 2))
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]

    c1 = Course("C1", "10001", "Prof. A", Evaluation.Exam)
    c1.add_requirement(ProgramRequirement("10001", 1, Semester.FALL, ReqType.Obligatory))

    index = ConstraintIndex()
    index.build([c1], ["10001"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )

    ep = EngineProcess(results_path=str(tmp_path))
    try:
        for _ in range(2):
            ep.submit(engine, {fall: {c1: ["10001"]}})
            while True:
                msg = ep.get_notification()
                if msg["type"] in ("all_done", "error"):
                    assert msg["type"] == "all_done", f"Got error: {msg}"
                    break
    finally:
        ep.stop()


def test_engine_process_timing_response_under_3_seconds(tmp_path):
    """A trivial solve completes and sends 'all_done' within 3 seconds."""
    from datetime import date
    from src.models.course import Course
    from src.models.exam_period import ExamPeriod
    from src.models.program_requirement import ProgramRequirement
    from src.models.enums import Evaluation, Semester, Moed, ReqType
    from src.algorithm.constraint_index import ConstraintIndex
    from src.algorithm.exam_period_catalog import ExamPeriodCatalog
    from src.algorithm.basic_version_validator import BasicVersionValidator
    from src.algorithm.constraint_validator import ConstraintValidator
    from src.algorithm.scheduling_engine import SchedulingEngine

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 2))
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2)]

    c1 = Course("C1", "10001", "Prof. A", Evaluation.Exam)
    c1.add_requirement(ProgramRequirement("10001", 1, Semester.FALL, ReqType.Obligatory))

    index = ConstraintIndex()
    index.build([c1], ["10001"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )

    ep = EngineProcess(results_path=str(tmp_path))
    try:
        start = time.time()
        ep.submit(engine, {fall: {c1: ["10001"]}})

        while True:
            msg = ep.get_notification()
            if msg["type"] in ("all_done", "error"):
                break

        elapsed = time.time() - start
        assert elapsed < 3.0, f"Response took {elapsed:.2f}s, expected < 3s"
    finally:
        ep.stop()
