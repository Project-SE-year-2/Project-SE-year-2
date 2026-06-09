"""
Tests for AppService concurrency and thread safety.

These tests ensure that the singleton AppService can safely handle
concurrent access, specifically testing generate_stream and navigation
functions under multithreaded conditions.
"""

import threading
import time
import pytest
from unittest.mock import MagicMock

from src.presenter.app_service import AppService


@pytest.fixture
def clean_service():
    """Provides a fresh AppService instance for each test, bypassing the singleton."""
    AppService._instance = None
    service = AppService.getInstance()
    
    # Mock dependencies
    service._data_store = MagicMock()
    service._engine_process = MagicMock()
    service._results_reader = MagicMock()
    
    return service


def test_generate_stream_thread_safety(clean_service):
    """
    Test that generate_stream safely yields values and locks correctly
    when accessed from a background thread (GenerateWorker simulator).
    """
    # Setup selected programs
    clean_service.select_programs(["10001"])
    
    # Mock engine process to yield a sequence of messages
    messages = [
        {"type": "period_done", "period_id": "FALL_Aleph"},
        {"type": "period_done", "period_id": "SPRI_Aleph"},
        {"type": "all_done"}
    ]
    
    def mock_get_notification():
        if messages:
            return messages.pop(0)
        time.sleep(0.1) # Simulate waiting
        return {"type": "all_done"}
        
    clean_service._engine_process.get_notification.side_effect = mock_get_notification
    
    # Collect yielded values in a background thread
    yielded_values = []
    
    def worker_thread():
        for val in clean_service.generate_stream():
            yielded_values.append(val)
            
    thread = threading.Thread(target=worker_thread)
    thread.start()
    thread.join(timeout=2.0)
    
    assert not thread.is_alive(), "Worker thread hung"
    
    # Verify the yielded values
    assert len(yielded_values) == 2
    assert yielded_values[0][0] == "FALL_Aleph"
    assert yielded_values[1][0] == "SPRI_Aleph"


def test_navigate_thread_safety(clean_service):
    """
    Test that concurrent calls to navigate() and navigate_global() do not
    corrupt the internal state or cause race conditions.
    """
    # Initialize some periods in the results reader mock
    clean_service._active_periods = ["FALL_Aleph", "SPRI_Aleph"]
    clean_service._results_reader.get_count.side_effect = lambda pid: 10 if pid in clean_service._active_periods else 0
    clean_service._results_reader.get_period_schedule.return_value = []
    
    clean_service._current_indices = {
        "FALL_Aleph": 0,
        "SPRI_Aleph": 0
    }
    
    # A barrier to synchronize threads
    barrier = threading.Barrier(10)
    exceptions = []
    
    def navigate_worker(period_id, direction, iterations):
        try:
            barrier.wait(timeout=2.0)
            for _ in range(iterations):
                try:
                    clean_service.navigate(period_id, direction)
                except IndexError:
                    pass
        except Exception as e:
            exceptions.append(e)
            
    # Spawn 5 threads navigating forward, 5 threads navigating backward
    threads = []
    for i in range(5):
        t1 = threading.Thread(target=navigate_worker, args=("FALL_Aleph", 1, 100))
        t2 = threading.Thread(target=navigate_worker, args=("FALL_Aleph", -1, 100))
        threads.extend([t1, t2])
        
    for t in threads:
        t.start()
        
    for t in threads:
        t.join(timeout=5.0)
        
    assert not exceptions, f"Exceptions occurred in threads: {exceptions}"
    
    # Because there's 500 forward and 500 backward increments (which wrap at 0/9),
    # the exact final index is deterministic but we mainly care that it didn't crash
    # and that the indices are within bounds.
    assert 0 <= clean_service._current_indices["FALL_Aleph"] < 10


def test_get_current_combination_thread_safety(clean_service):
    """
    Test get_current_combination can be called concurrently with navigation.
    """
    clean_service._active_periods = ["FALL_Aleph", "SPRI_Aleph"]
    clean_service._results_reader.get_count.return_value = 5
    clean_service._format_schedule_rows = MagicMock(return_value=[{"course": "Test"}])
    
    clean_service._current_indices = {
        "FALL_Aleph": 0,
        "SPRI_Aleph": 0
    }
    
    stop_event = threading.Event()
    exceptions = []
    
    def read_worker():
        try:
            while not stop_event.is_set():
                combo = clean_service.get_current_combination()
                assert len(combo) == 2  # One for each period
        except Exception as e:
            exceptions.append(e)
            
    def write_worker():
        try:
            while not stop_event.is_set():
                try:
                    clean_service.navigate_global(1)
                except IndexError:
                    pass
        except Exception as e:
            exceptions.append(e)
            
    r_thread = threading.Thread(target=read_worker)
    w_thread = threading.Thread(target=write_worker)
    
    r_thread.start()
    w_thread.start()
    
    time.sleep(0.5)
    stop_event.set()
    
    r_thread.join(timeout=1.0)
    w_thread.join(timeout=1.0)
    
    assert not exceptions, f"Exceptions occurred in threads: {exceptions}"
