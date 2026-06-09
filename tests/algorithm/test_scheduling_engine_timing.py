"""
Performance / timing tests for the SchedulingEngine.

These tests verify that the engine completes within acceptable time
bounds for small-to-medium inputs.  The bounds are deliberately generous
to avoid CI flakiness.
"""

import time
from datetime import date

import pytest

from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.scheduling_engine import SchedulingEngine
from src.algorithm.period_results_writer import PeriodResultsWriter
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType
from src.presenter.results_reader import ResultsReader


def _make_course(cid: str, program: str, semester: Semester = Semester.FALL) -> Course:
    c = Course(f"Course {cid}", cid, "Prof. Test", Evaluation.Exam)
    c.add_requirement(ProgramRequirement(program, 1, semester, ReqType.Obligatory))
    return c


def _build_engine(courses, programs, periods):
    index = ConstraintIndex()
    index.build(courses, programs)
    catalog = ExamPeriodCatalog(periods)
    collision_validator = BasicVersionValidator(index)
    constraint_validator = ConstraintValidator(index, collision_validator)
    return SchedulingEngine(constraint_validator, catalog, index)


def test_generate_all_three_periods_completes_quickly():
    """generateAll with 3 periods × 3 independent courses × 7 days
    completes in < 5 seconds."""
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 7))
    fall.possible_dates = [date(2026, 1, d) for d in range(1, 8)]
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, date(2026, 6, 1), date(2026, 6, 7))
    spri.possible_dates = [date(2026, 6, d) for d in range(1, 8)]
    summ = ExamPeriod(Semester.SUMM, Moed.Aleph, date(2026, 8, 1), date(2026, 8, 7))
    summ.possible_dates = [date(2026, 8, d) for d in range(1, 8)]

    c1 = _make_course("10001", "10001", Semester.FALL)
    c2 = _make_course("10002", "10002", Semester.SPRI)
    c3 = _make_course("10003", "10003", Semester.SUMM)

    engine = _build_engine([c1, c2, c3], ["10001", "10002", "10003"], [fall, spri, summ])

    tasks = {
        fall: {c1: ["10001"]},
        spri: {c2: ["10002"]},
        summ: {c3: ["10003"]},
    }

    start = time.time()
    schedules, metadata = engine.generateAll(tasks)
    elapsed = time.time() - start

    assert elapsed < 5.0, f"generateAll took {elapsed:.2f}s, expected < 5s"
    assert len(schedules) > 0


def test_solve_to_disk_completes_quickly(tmp_path):
    """solve_to_disk with 2 independent courses × 5 days completes in < 2 seconds."""
    c1 = _make_course("10001", "10001")
    c2 = _make_course("10002", "10002")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 5))
    fall.possible_dates = [date(2026, 1, d) for d in range(1, 6)]

    engine = _build_engine([c1, c2], ["10001", "10002"], [fall])

    writer = PeriodResultsWriter(root_path=tmp_path / "results")

    start = time.time()
    total = engine.solve_to_disk(fall, {c1: ["10001"], c2: ["10002"]}, writer)
    elapsed = time.time() - start

    assert elapsed < 2.0, f"solve_to_disk took {elapsed:.2f}s, expected < 2s"
    assert total == 25  # 5^2 = 25 (independent courses)


def test_iter_period_results_first_result_prompt():
    """iterPeriodResults yields the first period result within 1 second."""
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, date(2026, 1, 1), date(2026, 1, 3))
    fall.possible_dates = [date(2026, 1, d) for d in range(1, 4)]

    c1 = _make_course("10001", "10001")

    engine = _build_engine([c1], ["10001"], [fall])
    tasks = {fall: {c1: ["10001"]}}

    start = time.time()
    gen = engine.iterPeriodResults(tasks)
    first = next(gen)
    elapsed = time.time() - start

    assert elapsed < 1.0, f"First result took {elapsed:.2f}s, expected < 1s"
    assert first.period is fall
    assert len(first.schedules) > 0
