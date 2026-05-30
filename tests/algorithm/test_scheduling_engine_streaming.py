from threading import Event

import pytest

from src.algorithm.generation_result import PeriodGenerationResult
from src.algorithm.scheduling_engine import SchedulingEngine
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.enums import Evaluation, Semester, Moed


def _build_engine(periods: list[ExamPeriod]) -> SchedulingEngine:
    index = ConstraintIndex()
    catalog = ExamPeriodCatalog(periods)
    collision_validator = BasicVersionValidator(index)
    constraint_validator = ConstraintValidator(index, collision_validator)
    return SchedulingEngine(constraint_validator, catalog, index)


def _make_schedule(period: ExamPeriod, course: Course, exam_date) -> ExamSchedule:
    schedule = ExamSchedule(period)
    schedule.assign(course, exam_date)
    return schedule


def test_iter_period_results_yields_updates_before_final_list(monkeypatch):
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-02-2026", "02-02-2026")
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, "01-07-2026", "02-07-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

    engine = _build_engine([fall, spri])

    blocker = Event()

    def fake_solve_period(period, courses_dict):
        if period is spri:
            blocker.wait(timeout=1)

        if period is fall:
            schedule = _make_schedule(fall, course1, fall.start_date)
        else:
            schedule = _make_schedule(spri, course2, spri.start_date)

        return PeriodGenerationResult(
            period=period,
            schedules=[schedule],
            metadata={
                "valid_count": 1,
                "theoretical_count": 1,
                "courses": list(courses_dict.keys()),
                "available_days": 2,
            },
        )

    monkeypatch.setattr(engine, "_solve_period", fake_solve_period)

    scheduling_tasks = {
        fall: {course1: ["83101"]},
        spri: {course2: ["83101"]},
    }

    results = engine.iterPeriodResults(scheduling_tasks)

    first_result = next(results)
    assert first_result.period is fall
    assert first_result.metadata["valid_count"] == 1
    assert first_result.schedules[0].assignments[course1] == fall.start_date

    blocker.set()

    second_result = next(results)
    assert second_result.period is spri
    assert second_result.metadata["valid_count"] == 1
    assert second_result.schedules[0].assignments[course2] == spri.start_date


def test_generate_all_returns_final_combined_schedule(monkeypatch):
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-02-2026", "02-02-2026")
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, "01-07-2026", "02-07-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

    engine = _build_engine([fall, spri])

    def fake_solve_period(period, courses_dict):
        if period is fall:
            schedule = _make_schedule(fall, course1, fall.start_date)
        else:
            schedule = _make_schedule(spri, course2, spri.start_date)

        return PeriodGenerationResult(
            period=period,
            schedules=[schedule],
            metadata={
                "valid_count": 1,
                "theoretical_count": 1,
                "courses": list(courses_dict.keys()),
                "available_days": 2,
            },
        )

    monkeypatch.setattr(engine, "_solve_period", fake_solve_period)

    scheduling_tasks = {
        fall: {course1: ["83101"]},
        spri: {course2: ["83101"]},
    }

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert len(schedules) == 1
    assert metadata[fall]["valid_count"] == 1
    assert metadata[spri]["valid_count"] == 1

    combined_assignments = schedules[0].sortByDate()
    assert len(combined_assignments) == 2

    periods_in_schedule = [item[0] for item in combined_assignments]
    assert fall in periods_in_schedule
    assert spri in periods_in_schedule


def test_iter_period_results_returns_empty_for_empty_tasks():
    engine = _build_engine([])

    assert list(engine.iterPeriodResults({})) == []


def test_generate_all_returns_empty_results_for_empty_tasks():
    engine = _build_engine([])

    schedules, metadata = engine.generateAll({})

    assert schedules == []
    assert metadata == {}


def test_generate_all_preserves_input_order_even_if_completion_is_reversed(monkeypatch):
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-02-2026", "02-02-2026")
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, "01-07-2026", "02-07-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)

    engine = _build_engine([fall, spri])

    blocker = Event()

    def fake_solve_period(period, courses_dict):
        if period is fall:
            blocker.wait(timeout=1)
            schedule = _make_schedule(fall, course1, fall.start_date)
        else:
            schedule = _make_schedule(spri, course2, spri.start_date)

        return PeriodGenerationResult(
            period=period,
            schedules=[schedule],
            metadata={
                "valid_count": 1,
                "theoretical_count": 1,
                "courses": list(courses_dict.keys()),
                "available_days": 2,
            },
        )

    monkeypatch.setattr(engine, "_solve_period", fake_solve_period)

    scheduling_tasks = {
        fall: {course1: ["83101"]},
        spri: {course2: ["83101"]},
    }

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert len(schedules) == 1
    assert list(metadata.keys()) == [fall, spri]


def test_generate_all_supports_three_period_cartesian_product(monkeypatch):
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-02-2026", "03-02-2026")
    spri = ExamPeriod(Semester.SPRI, Moed.Aleph, "01-07-2026", "03-07-2026")
    summ = ExamPeriod(Semester.SUMM, Moed.Aleph, "01-09-2026", "03-09-2026")

    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)
    course2 = Course("Calculus 1", "83112", "Prof. B", Evaluation.Exam)
    course3 = Course("Chemistry 1", "83122", "Prof. C", Evaluation.Exam)

    engine = _build_engine([fall, spri, summ])

    def fake_solve_period(period, courses_dict):
        if period is fall:
            schedules = [
                _make_schedule(fall, course1, fall.start_date),
                _make_schedule(fall, course1, fall.start_date.replace(day=2)),
            ]
        elif period is spri:
            schedules = [
                _make_schedule(spri, course2, spri.start_date),
                _make_schedule(spri, course2, spri.start_date.replace(day=2)),
            ]
        else:
            schedules = [
                _make_schedule(summ, course3, summ.start_date),
                _make_schedule(summ, course3, summ.start_date.replace(day=2)),
            ]

        return PeriodGenerationResult(
            period=period,
            schedules=schedules,
            metadata={
                "valid_count": len(schedules),
                "theoretical_count": len(schedules),
                "courses": list(courses_dict.keys()),
                "available_days": 3,
            },
        )

    monkeypatch.setattr(engine, "_solve_period", fake_solve_period)

    scheduling_tasks = {
        fall: {course1: ["83101"]},
        spri: {course2: ["83101"]},
        summ: {course3: ["83101"]},
    }

    schedules, metadata = engine.generateAll(scheduling_tasks)

    assert len(schedules) == 8
    assert metadata[fall]["valid_count"] == 2
    assert metadata[spri]["valid_count"] == 2
    assert metadata[summ]["valid_count"] == 2


def test_generate_all_propagates_worker_exception(monkeypatch):
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-02-2026", "02-02-2026")
    course1 = Course("Physics 1", "83102", "Prof. A", Evaluation.Exam)

    engine = _build_engine([fall])

    def fake_solve_period(period, courses_dict):
        raise RuntimeError("solver exploded")

    monkeypatch.setattr(engine, "_solve_period", fake_solve_period)

    with pytest.raises(RuntimeError, match="solver exploded"):
        engine.generateAll({fall: {course1: ["83101"]}})
