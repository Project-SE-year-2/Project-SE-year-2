"""
Unit tests for IAppService — verify the ABC contract is enforced correctly.

Rules checked:
  1. A class that doesn't implement ALL abstract methods raises TypeError on instantiation.
  2. A class that implements every abstract method can be instantiated.
  3. Every method on a complete implementation is callable.
"""

import pytest
from datetime import date
from src.presenter.i_app_service import IAppService


# ------------------------------------------------------------------ #
# Helpers — minimal concrete implementations                           #
# ------------------------------------------------------------------ #

class _NoMethods(IAppService):
    """Implements none of the abstract methods."""
    pass


class _PartialImpl(IAppService):
    """Implements only a few of the abstract methods."""
    def load_data(self, courses_path, dates_path, mode): pass
    def get_available_programs(self): return []
    def select_programs(self, ids): pass
    # remaining 11 methods intentionally omitted


class _FullImpl(IAppService):
    """Implements every abstract method with a no-op body."""

    def load_data(self, courses_path, dates_path, mode): pass
    def get_available_programs(self): return []
    def select_programs(self, ids): pass
    def get_courses(self, program_id): return []
    def get_periods(self): return []
    def toggle_day(self, period_id, day): pass
    def shift_period(self, period_id, start, end): pass
    def generate(self): return 0
    def generate_stream(self): return iter([])
    def get_period_ids(self): return []
    def get_period_schedules(self, period_id): return []
    def get_schedule_count(self, period_id=None): return 0
    def get_schedule_batch(self, start, limit): return []
    def get_schedule(self, index): return {}
    def export_schedule(self, index, path): pass
    def navigate(self, period_id, direction): return {}
    def navigate_global(self, direction): return {}
    def export_current(self, path): pass


# ------------------------------------------------------------------ #
# Tests                                                                #
# ------------------------------------------------------------------ #

def test_no_methods_raises_type_error():
    """A class that implements nothing must raise TypeError."""
    with pytest.raises(TypeError):
        _NoMethods()


def test_partial_implementation_raises_type_error():
    """A class that implements only some methods must still raise TypeError."""
    with pytest.raises(TypeError):
        _PartialImpl()


def test_complete_implementation_can_be_instantiated():
    """A class that implements all 14 methods must not raise."""
    service = _FullImpl()
    assert service is not None


def test_all_abstract_methods_are_callable_on_full_implementation():
    """Every method in the interface must be callable on the complete impl."""
    service = _FullImpl()

    # Call every method — if any are missing this will AttributeError / TypeError
    service.load_data("a.txt", "b.txt", "replace")
    service.get_available_programs()
    service.select_programs(["12345"])
    service.get_courses("12345")
    service.get_periods()
    service.toggle_day("FALL_Aleph", date(2026, 2, 1))
    service.shift_period("FALL_Aleph", date(2026, 2, 1), date(2026, 2, 28))
    service.generate()
    list(service.generate_stream())
    service.get_period_ids()
    service.get_period_schedules("FALL_Aleph")
    service.get_schedule_count()
    service.get_schedule(0)
    service.export_schedule(0, "out.txt")


def test_iappservice_is_abstract():
    """IAppService itself cannot be instantiated directly."""
    with pytest.raises(TypeError):
        IAppService()
