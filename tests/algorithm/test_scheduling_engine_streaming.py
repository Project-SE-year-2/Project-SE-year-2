from datetime import date
from threading import Event

import pytest

from src.algorithm.generation_result import PeriodGenerationResult
from src.algorithm.period_results_writer import PeriodResultsWriter
from src.algorithm.scheduling_engine import SchedulingEngine
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.constraints.constraint_checker import ConstraintChecker
from src.models.constraint_settings import ConstraintSettings
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.enums import Evaluation, Moed, ReqType, Semester
from src.models.program_requirement import ProgramRequirement
from src.presenter.results_reader import ResultsReader
from tests.algorithm.constraint_helpers import make_elective_course


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


# ================================================================== #
# solve_to_disk                                                        #
# ================================================================== #

# Helper to create a course with no collision constraints (no shared obligatory groups)
def _make_independent_course(cid: str) -> Course:
    """Course with no shared obligatory group — no collision constraints."""
    c = Course(f"Course {cid}", cid, "Prof. Test", Evaluation.Exam)
    c.add_requirement(ProgramRequirement(cid, 1, Semester.FALL, ReqType.Obligatory))
    return c


def test_solve_to_disk_writes_all_schedules(tmp_path):
    """2 independent courses (no collision constraint) × 3 available days = 9 valid
    schedules (3×3, same-day assignments allowed across different programs).
    solve_to_disk() must write them all to disk and return the correct total."""
    c1 = _make_independent_course("10001")
    c2 = _make_independent_course("10002")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([c1, c2], ["10001", "10002"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    total = engine.solve_to_disk(fall, {c1: ["10001"], c2: ["10002"]}, writer)

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == 9
    assert reader.get_count("FALL_Aleph") == 9


def test_solve_to_disk_empty_period_writes_zero_to_manifest(tmp_path):
    """A period with no courses must register 0 in the manifest."""
    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1)]

    index = ConstraintIndex()
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    total = engine.solve_to_disk(fall, {}, writer)

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == 0
    assert reader.get_count("FALL_Aleph") == 0


def test_solve_to_disk_zero_valid_schedules_resets_manifest(tmp_path, monkeypatch):
    """A period with courses but a solver that finds nothing must leave manifest at 0,
    not carry over stale results from a previous run."""
    c1 = _make_independent_course("10001")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([c1], ["10001"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    reader = ResultsReader(root_path=tmp_path / "results")

    # Simulate a first run that produced results
    stale = ExamSchedule(fall)
    stale.assign(c1, date(2026, 1, 1))
    writer.write_batch("FALL_Aleph", [stale])
    assert reader.get_count("FALL_Aleph") == 1

    # Second run: courses present but solver yields nothing (mocked)
    monkeypatch.setattr(engine._solver, "solve_stream", lambda *a, **kw: iter([]))
    total = engine.solve_to_disk(fall, {c1: ["10001"]}, writer)

    assert total == 0
    assert reader.get_count("FALL_Aleph") == 0   # stale result must not persist


def test_solve_to_disk_second_run_replaces_first_run_results(tmp_path):
    """Running solve_to_disk twice on the same period must not accumulate results."""
    c1 = _make_independent_course("10001")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([c1], ["10001"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )

    writer = PeriodResultsWriter(root_path=tmp_path / "results")
    reader = ResultsReader(root_path=tmp_path / "results")

    engine.solve_to_disk(fall, {c1: ["10001"]}, writer)
    first_count = reader.get_count("FALL_Aleph")

    engine.solve_to_disk(fall, {c1: ["10001"]}, writer)
    second_count = reader.get_count("FALL_Aleph")

    # Second run must produce exactly the same count, not double it
    assert second_count == first_count


# ================================================================== #
# solve_to_disk - constraint_checker filter                           #
# ================================================================== #

def test_constraint_checker_none_writes_all_schedules(tmp_path):
    """Explicitly passing constraint_checker=None must behave identically to omitting it."""
    c1 = _make_independent_course("10001")
    c2 = _make_independent_course("10002")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([c1, c2], ["10001", "10002"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )
    writer = PeriodResultsWriter(root_path=tmp_path / "results")

    total = engine.solve_to_disk(
        fall, {c1: ["10001"], c2: ["10002"]}, writer, constraint_checker=None
    )

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == 9
    assert reader.get_count("FALL_Aleph") == 9


def test_constraint_checker_accepting_all_writes_all(tmp_path):
    """A checker with no constraints enabled must pass every schedule through."""
    c1 = _make_independent_course("10001")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([c1], ["10001"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )
    writer = PeriodResultsWriter(root_path=tmp_path / "results")

    total = engine.solve_to_disk(
        fall, {c1: ["10001"]}, writer,
        constraint_checker=ConstraintChecker(ConstraintSettings()),
    )

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == 3
    assert reader.get_count("FALL_Aleph") == 3


def test_daily_cap_filter_removes_same_day_schedules(tmp_path):
    """daily_cap_k=1 rejects schedules where two courses share a day.
    2 courses × 3 days = 9 total: 3 same-day (fail) + 6 cross-day (pass)."""
    c1 = _make_independent_course("10001")
    c2 = _make_independent_course("10002")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([c1, c2], ["10001", "10002"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )
    writer = PeriodResultsWriter(root_path=tmp_path / "results")

    total = engine.solve_to_disk(
        fall, {c1: ["10001"], c2: ["10002"]}, writer,
        constraint_checker=ConstraintChecker(
            ConstraintSettings(daily_cap_enabled=True, daily_cap_k=1)
        ),
    )

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == 6
    assert reader.get_count("FALL_Aleph") == 6


def test_elective_collision_filter_removes_same_day_electives(tmp_path):
    """elective_conflicts_k=1 caps each (program, day) cell at 1 elective.
    Same-day schedules reach count=2 and fail; cross-day reach count=1 and pass.
    2 electives × 3 days = 9 total: 3 same-day (fail) + 6 cross-day (pass)."""
    PROG = "83101"
    e1 = make_elective_course("E1", PROG)
    e2 = make_elective_course("E2", PROG)

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([e1, e2], [PROG])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )
    writer = PeriodResultsWriter(root_path=tmp_path / "results")

    total = engine.solve_to_disk(
        fall, {e1: [PROG], e2: [PROG]}, writer,
        constraint_checker=ConstraintChecker(
            ConstraintSettings(elective_conflicts_enabled=True, elective_conflicts_k=1)
        ),
    )

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == 6
    assert reader.get_count("FALL_Aleph") == 6


def test_two_constraints_both_applied_to_same_schedule(tmp_path):
    """Both daily_cap and elective_conflicts independently reject same-day schedules.
    Enabling both together must still reject them (AND logic, no double-counting):
    2 electives × 3 days = 9 total, 3 same-day fail both → 6 pass."""
    PROG = "83101"
    e1 = make_elective_course("E1", PROG)
    e2 = make_elective_course("E2", PROG)

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([e1, e2], [PROG])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )
    writer = PeriodResultsWriter(root_path=tmp_path / "results")

    total = engine.solve_to_disk(
        fall, {e1: [PROG], e2: [PROG]}, writer,
        constraint_checker=ConstraintChecker(
            ConstraintSettings(
                daily_cap_enabled=True, daily_cap_k=1,
                elective_conflicts_enabled=True, elective_conflicts_k=1,
            )
        ),
    )

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == 6
    assert reader.get_count("FALL_Aleph") == 6


def test_return_value_matches_disk_count(tmp_path):
    """solve_to_disk() return value must equal the number of schedules written, not generated."""
    c1 = _make_independent_course("10001")
    c2 = _make_independent_course("10002")

    fall = ExamPeriod(Semester.FALL, Moed.Aleph, "01-01-2026", "03-01-2026")
    fall.possible_dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    index = ConstraintIndex()
    index.build([c1, c2], ["10001", "10002"])
    engine = SchedulingEngine(
        ConstraintValidator(index, BasicVersionValidator(index)),
        ExamPeriodCatalog([fall]),
        index,
    )
    writer = PeriodResultsWriter(root_path=tmp_path / "results")

    total = engine.solve_to_disk(
        fall, {c1: ["10001"], c2: ["10002"]}, writer,
        constraint_checker=ConstraintChecker(
            ConstraintSettings(daily_cap_enabled=True, daily_cap_k=1)
        ),
    )

    reader = ResultsReader(root_path=tmp_path / "results")
    assert total == reader.get_count("FALL_Aleph")
    assert total < 9