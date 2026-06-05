"""
Memory check for EP-82 file-based generation.

Verifies that RAM stays bounded during generation - at most one batch of
BATCH_SIZE schedules is held in memory at a time.  Stops after MAX_BATCHES
per period so the script finishes even with billions of valid schedules.

Expected peak per batch: a few hundred KB (not hundreds of MB).

Usage:
    python -m scripts.stress_memory_check
"""

import gc
import shutil
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

COURSES_PATH = ROOT / "data" / "stress_courses.txt"
DATES_PATH   = ROOT / "data" / "stress_dates.txt"
RESULTS_PATH = ROOT / "data" / "stress_results"
PROGRAMS     = ["83101", "83102", "83103", "83104", "83105"]
TIME_LIMIT   = 20  # seconds to run per period before stopping


def _kb(b: int) -> str:
    return f"{b / 1024:.1f} KB"


def run():
    if RESULTS_PATH.exists():
        shutil.rmtree(RESULTS_PATH)

    from src.algorithm.constraint_index import ConstraintIndex
    from src.algorithm.exam_period_catalog import ExamPeriodCatalog
    from src.algorithm.basic_version_validator import BasicVersionValidator
    from src.algorithm.constraint_validator import ConstraintValidator
    from src.algorithm.scheduling_engine import SchedulingEngine
    from src.algorithm.scheduling_algoritem import match_courses_to_periods
    from src.algorithm.period_results_writer import PeriodResultsWriter, BATCH_SIZE
    from src.parsers.course_parser import filter_courses_for_scheduling
    from src.presenter.app_service import AppService

    AppService._instance = None
    svc = AppService()
    svc.load_data(str(COURSES_PATH), str(DATES_PATH), "replace")
    svc.select_programs(PROGRAMS)

    ds      = svc._datastore
    valid   = filter_courses_for_scheduling(ds.get_all_courses(), PROGRAMS)
    periods = ds.get_periods()
    tasks   = match_courses_to_periods(valid, periods)

    index = ConstraintIndex()
    index.build(valid, PROGRAMS)
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog(periods),
        index,
    )
    writer = PeriodResultsWriter(root_path=RESULTS_PATH)

    print(f"\n{'='*58}")
    print(f"  EP-82 Memory Check  (BATCH_SIZE={BATCH_SIZE}, {TIME_LIMIT}s per period)")
    print(f"{'='*58}")

    overall_peak = 0

    for period, courses_dict in tasks.items():
        pid          = f"{period.semester.value}_{period.moed.value}"
        courses_list = list(courses_dict.keys())
        if not courses_list:
            continue

        batch      = []
        batch_num  = 0
        deadline   = time.time() + TIME_LIMIT

        tracemalloc.start()
        gc.collect()
        baseline, _ = tracemalloc.get_traced_memory()

        for sched in engine._solver.solve_stream(courses_list, period, engine._validator):
            batch.append(sched)

            if len(batch) >= BATCH_SIZE:
                _, peak = tracemalloc.get_traced_memory()
                net_peak = peak - baseline
                overall_peak = max(overall_peak, net_peak)

                writer.write_batch(pid, batch)
                batch = []
                gc.collect()

                batch_num += 1
                print(f"  {pid}  batch {batch_num:>4}  peak RAM: {_kb(net_peak)}")

                if time.time() >= deadline:
                    print(f"  {pid}  (time limit reached — stopping this period)")
                    break

        if batch:
            writer.write_batch(pid, batch)

        tracemalloc.stop()
        tracemalloc.clear_traces()

    print(f"\n  Overall peak across all batches : {_kb(overall_peak)}")
    print(f"  This should be a few hundred KB — not hundreds of MB.")
    print(f"{'='*58}\n")


if __name__ == "__main__":
    run()
