import traceback
import sys
import logging

def patch():
    from src.presenter.app_service import AppService
    original = AppService._mark_dirty
    def _mark_dirty(self):
        with open("dirty_trace.log", "a") as f:
            f.write("--- _mark_dirty called ---\n")
            traceback.print_stack(file=f)
        original(self)
    AppService._mark_dirty = _mark_dirty
    
    # We also want to know if `clear_results` is being called
    original_clear = AppService.clear_results
    def clear_results(self):
        with open("dirty_trace.log", "a") as f:
            f.write("--- clear_results called ---\n")
            traceback.print_stack(file=f)
        original_clear(self)
    AppService.clear_results = clear_results

patch()
