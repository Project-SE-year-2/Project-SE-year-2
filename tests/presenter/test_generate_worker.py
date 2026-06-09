"""
Tests for GenerateWorker — the QThread that drives streaming generation.

Requires PyQt5. The entire file is skipped automatically when PyQt5 is
absent, matching the stub fallback in src/presenter/generate_worker.py.

Strategy: call worker.run() directly (synchronously in the test thread)
rather than worker.start(). When the emitter and the receiver are on the
same thread, PyQt5 signal connections fire synchronously, so no event loop
is needed and assertions can follow run() directly.
"""

import sys
import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not installed — skipping GenerateWorker tests")

from PyQt5.QtCore import QCoreApplication
from unittest.mock import MagicMock

from src.presenter.generate_worker import GenerateWorker


# ------------------------------------------------------------------ #
# Session-scoped QCoreApplication (required for pyqtSignal)          #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    return app


# ================================================================== #
# period_ready signal                                                  #
# ================================================================== #

def test_period_ready_emitted_once_per_period(qapp):
    received = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([
        ("FALL_Aleph", []),
        ("SPRI_Aleph", []),
        ("SUMM_Aleph", []),
    ])
    mock_service.get_schedule_count.return_value = 0

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received.append)
    worker.run()

    assert received == ["FALL_Aleph", "SPRI_Aleph", "SUMM_Aleph"]


def test_period_ready_not_emitted_when_stream_is_empty(qapp):
    received = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([])
    mock_service.get_schedule_count.return_value = 0

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received.append)
    worker.run()

    assert received == []


def test_period_ready_carries_correct_period_id(qapp):
    received = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([("FALL_Bet", [])])
    mock_service.get_schedule_count.return_value = 0

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received.append)
    worker.run()

    assert received == ["FALL_Bet"]


# ================================================================== #
# finished signal                                                      #
# ================================================================== #

def test_finished_emitted_with_schedule_count_from_service(qapp):
    counts = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([("FALL_Aleph", [])])
    mock_service.get_schedule_count.return_value = 42

    worker = GenerateWorker(mock_service)
    worker.finished.connect(counts.append)
    worker.run()

    assert counts == [42]


def test_finished_emitted_exactly_once(qapp):
    counts = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([
        ("FALL_Aleph", []),
        ("SPRI_Aleph", []),
    ])
    mock_service.get_schedule_count.return_value = 5

    worker = GenerateWorker(mock_service)
    worker.finished.connect(lambda _: counts.append(1))
    worker.run()

    assert len(counts) == 1


def test_finished_fires_after_all_period_ready_signals(qapp):
    """Signal order must be: period_ready × N, then finished × 1."""
    log = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([
        ("FALL_Aleph", []),
        ("SPRI_Aleph", []),
    ])
    mock_service.get_schedule_count.return_value = 7

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(lambda pid: log.append(f"ready:{pid}"))
    worker.finished.connect(lambda n: log.append(f"finished:{n}"))
    worker.run()

    assert log == ["ready:FALL_Aleph", "ready:SPRI_Aleph", "finished:7"]


def test_finished_emitted_with_zero_when_no_schedules_produced(qapp):
    counts = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([])
    mock_service.get_schedule_count.return_value = 0

    worker = GenerateWorker(mock_service)
    worker.finished.connect(counts.append)
    worker.run()

    assert counts == [0]


# ================================================================== #
# error signal                                                         #
# ================================================================== #

def test_error_emitted_when_generate_stream_raises(qapp):
    errors = []

    mock_service = MagicMock()
    mock_service.generate_stream.side_effect = RuntimeError("solver exploded")

    worker = GenerateWorker(mock_service)
    worker.error.connect(errors.append)
    worker.run()

    assert len(errors) == 1
    assert "solver exploded" in errors[0]


def test_error_message_contains_original_exception_text(qapp):
    errors = []

    mock_service = MagicMock()
    mock_service.generate_stream.side_effect = ValueError("no programs selected")

    worker = GenerateWorker(mock_service)
    worker.error.connect(errors.append)
    worker.run()

    assert "no programs selected" in errors[0]


def test_finished_not_emitted_when_exception_occurs(qapp):
    """On exception: error fires, finished must NOT fire."""
    finished_calls = []
    errors = []

    mock_service = MagicMock()
    mock_service.generate_stream.side_effect = RuntimeError("crash")

    worker = GenerateWorker(mock_service)
    worker.finished.connect(finished_calls.append)
    worker.error.connect(errors.append)
    worker.run()

    assert finished_calls == []
    assert len(errors) == 1


def test_error_emitted_when_exception_raised_mid_stream(qapp):
    """Exception after some period_ready signals were already emitted."""
    received_periods = []
    errors = []
    finished_calls = []

    def stream_that_explodes():
        yield "FALL_Aleph", []
        yield "SPRI_Aleph", []
        raise RuntimeError("disk full mid-stream")

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = stream_that_explodes()

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received_periods.append)
    worker.finished.connect(finished_calls.append)
    worker.error.connect(errors.append)
    worker.run()

    # Periods emitted before the crash must still have been signalled
    assert received_periods == ["FALL_Aleph", "SPRI_Aleph"]
    # finished must NOT have fired
    assert finished_calls == []
    # error must carry the crash message
    assert "disk full mid-stream" in errors[0]


# ================================================================== #
# Concurrent signal ordering                                           #
# ================================================================== #

def test_period_ready_signals_arrive_in_stream_order(qapp):
    """Even with many periods, signals arrive in the order yielded by the stream."""
    received = []
    period_ids = [f"PERIOD_{i}" for i in range(10)]

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter(
        [(pid, []) for pid in period_ids]
    )
    mock_service.get_schedule_count.return_value = 10

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received.append)
    worker.run()

    assert received == period_ids


def test_finished_carries_count_not_period_count(qapp):
    """finished signal carries the total schedule count from service,
    not the number of periods."""
    counts = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([
        ("P1", []), ("P2", []), ("P3", []),
    ])
    mock_service.get_schedule_count.return_value = 999

    worker = GenerateWorker(mock_service)
    worker.finished.connect(counts.append)
    worker.run()

    assert counts == [999]


# ================================================================== #
# Large stream performance                                             #
# ================================================================== #

def test_large_stream_completes_without_signal_loss(qapp):
    """A stream of 100 periods emits exactly 100 period_ready signals."""
    import time
    received = []
    n = 100

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter(
        [(f"P_{i}", []) for i in range(n)]
    )
    mock_service.get_schedule_count.return_value = n

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received.append)

    start = time.time()
    worker.run()
    elapsed = time.time() - start

    assert len(received) == n
    assert elapsed < 2.0, f"100-period stream took {elapsed:.2f}s, expected < 2s"


# ================================================================== #
# Service interaction counts                                           #
# ================================================================== #

def test_generate_stream_called_exactly_once(qapp):
    """generate_stream is called once per worker.run() invocation."""
    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([("P1", [])])
    mock_service.get_schedule_count.return_value = 1

    worker = GenerateWorker(mock_service)
    worker.run()

    mock_service.generate_stream.assert_called_once()


def test_get_schedule_count_called_after_stream_exhausted(qapp):
    """get_schedule_count is called after the stream is fully consumed."""
    call_log = []

    def fake_stream():
        call_log.append("stream_start")
        yield "P1", []
        call_log.append("stream_end")

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = fake_stream()
    mock_service.get_schedule_count.side_effect = lambda: (
        call_log.append("get_count"), 42
    )[1]

    worker = GenerateWorker(mock_service)
    worker.run()

    # get_count must come after stream_end
    assert call_log.index("stream_end") < call_log.index("get_count")


# ================================================================== #
# Re-run safety                                                        #
# ================================================================== #

def test_worker_can_be_run_twice(qapp):
    """Calling run() a second time must work (stateless between runs)."""
    received_1 = []
    received_2 = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([("P1", [])])
    mock_service.get_schedule_count.return_value = 1

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received_1.append)
    worker.run()

    # Reset for second run
    mock_service.generate_stream.return_value = iter([("P2", [])])
    worker.period_ready.disconnect()
    worker.period_ready.connect(received_2.append)
    worker.run()

    assert received_1 == ["P1"]
    assert received_2 == ["P2"]


# ================================================================== #
# Signal type validation                                               #
# ================================================================== #

def test_period_ready_signal_is_str(qapp):
    """period_ready signal must emit a str, not bytes or other types."""
    received = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([("FALL_Aleph", [])])
    mock_service.get_schedule_count.return_value = 1

    worker = GenerateWorker(mock_service)
    worker.period_ready.connect(received.append)
    worker.run()

    assert isinstance(received[0], str)


def test_finished_signal_is_int(qapp):
    """finished signal must emit an int."""
    received = []

    mock_service = MagicMock()
    mock_service.generate_stream.return_value = iter([])
    mock_service.get_schedule_count.return_value = 0

    worker = GenerateWorker(mock_service)
    worker.finished.connect(received.append)
    worker.run()

    assert isinstance(received[0], int)


def test_error_signal_is_str(qapp):
    """error signal must emit a str."""
    received = []

    mock_service = MagicMock()
    mock_service.generate_stream.side_effect = RuntimeError("crash")

    worker = GenerateWorker(mock_service)
    worker.error.connect(received.append)
    worker.run()

    assert isinstance(received[0], str)

