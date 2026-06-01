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
