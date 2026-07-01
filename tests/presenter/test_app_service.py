"""
Unit tests for AppService — the Presenter singleton.

Strategy:
  - The singleton is reset before and after every test via the
    `reset_singleton` autouse fixture so tests never bleed into each other.
  - DataStore.load() and DataStore.save() are patched to no-ops so no
    real files are read or written during tests.
  - External dependencies (parsers, engine, writer) are monkeypatched
    in the tests that need them.
"""

import json
import pickle
import sqlite3

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from src.algorithm.period_results_writer import BATCH_SIZE
from src.algorithm.manual_move_validator import ManualMoveValidator
from src.presenter.app_service import AppService
from src.presenter.data_store import DataStore
from src.presenter.results_reader import ResultsReader
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_placement import ExamPlacement
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType, TimeSlot
from src.models.room import Room
from src.output.schedule_report_writer import ScheduleReportWriter
from src.output.pdf_schedule_report_writer import PdfScheduleReportWriter


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture(autouse=True)
def reset_singleton():
    """Destroy the singleton before and after every test."""
    AppService._instance = None
    yield
    AppService._instance = None


def _make_service(monkeypatch) -> AppService:
    """Return a fresh AppService with no disk I/O."""
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)
    return AppService()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _make_course(course_id: str, program_id: str = "83101") -> Course:
    course = Course(f"Course {course_id}", course_id, "Prof. X", Evaluation.Exam)
    course.add_requirement(
        ProgramRequirement(program_id, 1, Semester.FALL, ReqType.Obligatory)
    )
    return course


def _make_period(semester: Semester = Semester.FALL, moed: Moed = Moed.Aleph) -> ExamPeriod:
    p = ExamPeriod(semester, moed, date(2026, 2, 1), date(2026, 2, 28))
    p.possible_dates = [date(2026, 2, 1), date(2026, 2, 2)]
    return p


def _make_schedule(period: ExamPeriod, course: Course, exam_date: date) -> ExamSchedule:
    s = ExamSchedule(period)
    s.assign(course, exam_date)
    return s


# ------------------------------------------------------------------ #
# Singleton                                                            #
# ------------------------------------------------------------------ #

def test_get_instance_returns_same_object(monkeypatch):
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    s1 = AppService.getInstance()
    s2 = AppService.getInstance()
    assert s1 is s2


def test_get_instance_returns_app_service(monkeypatch):
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    assert isinstance(AppService.getInstance(), AppService)


# ------------------------------------------------------------------ #
# load_data — file validation                                          #
# ------------------------------------------------------------------ #

def test_load_data_raises_file_not_found_for_missing_courses(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    dates_file = tmp_path / "dates.txt"
    dates_file.write_text("content")

    with pytest.raises(FileNotFoundError):
        service.load_data(str(tmp_path / "missing.txt"), str(dates_file), "replace")


def test_load_data_raises_file_not_found_for_missing_dates(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    courses_file = tmp_path / "courses.txt"
    courses_file.write_text("content")

    with pytest.raises(FileNotFoundError):
        service.load_data(str(courses_file), str(tmp_path / "missing.txt"), "replace")


def test_load_data_raises_value_error_for_empty_courses_file(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    courses_file = tmp_path / "courses.txt"
    courses_file.write_text("")          # empty
    dates_file = tmp_path / "dates.txt"
    dates_file.write_text("content")

    with pytest.raises(ValueError):
        service.load_data(str(courses_file), str(dates_file), "replace")


def test_load_data_raises_value_error_for_empty_dates_file(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    courses_file = tmp_path / "courses.txt"
    courses_file.write_text("content")
    dates_file = tmp_path / "dates.txt"
    dates_file.write_text("")           # empty

    with pytest.raises(ValueError):
        service.load_data(str(courses_file), str(dates_file), "replace")


def test_load_data_raises_value_error_for_unknown_mode(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    courses_file = tmp_path / "courses.txt"
    courses_file.write_text("x")
    dates_file = tmp_path / "dates.txt"
    dates_file.write_text("x")

    fake_courses = [_make_course("11111")]
    fake_periods = [_make_period()]

    with patch("src.presenter.app_service.CourseFileParser") as MockCFP, \
         patch("src.presenter.app_service.ExamPeriodFileParser") as MockEFP:
        MockCFP.return_value.parse.return_value = fake_courses
        MockEFP.return_value.parse.return_value = fake_periods

        with pytest.raises(ValueError, match="Unknown mode"):
            service.load_data(str(courses_file), str(dates_file), "invalid")


# ------------------------------------------------------------------ #
# load_data — replace vs append modes                                  #
# ------------------------------------------------------------------ #

def test_load_data_replace_overwrites_courses(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    # Pre-load an old course
    service._datastore.set_courses([_make_course("00000")])

    courses_file = tmp_path / "c.txt"
    courses_file.write_text("x")
    dates_file = tmp_path / "d.txt"
    dates_file.write_text("x")

    new_courses = [_make_course("11111"), _make_course("22222")]
    fake_periods = [_make_period()]

    with patch("src.presenter.app_service.CourseFileParser") as MockCFP, \
         patch("src.presenter.app_service.ExamPeriodFileParser") as MockEFP:
        MockCFP.return_value.parse.return_value = new_courses
        MockEFP.return_value.parse.return_value = fake_periods

        service.load_data(str(courses_file), str(dates_file), "replace")

    ids = {c.course_id for c in service._datastore.get_all_courses()}
    assert ids == {"11111", "22222"}
    assert "00000" not in ids


def test_load_data_append_merges_courses(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    service._datastore.set_courses([_make_course("00000")])

    courses_file = tmp_path / "c.txt"
    courses_file.write_text("x")
    dates_file = tmp_path / "d.txt"
    dates_file.write_text("x")

    new_courses = [_make_course("11111")]
    fake_periods = [_make_period()]

    with patch("src.presenter.app_service.CourseFileParser") as MockCFP, \
         patch("src.presenter.app_service.ExamPeriodFileParser") as MockEFP:
        MockCFP.return_value.parse.return_value = new_courses
        MockEFP.return_value.parse.return_value = fake_periods

        service.load_data(str(courses_file), str(dates_file), "append")

    ids = {c.course_id for c in service._datastore.get_all_courses()}
    assert "00000" in ids
    assert "11111" in ids


def test_load_data_append_skips_duplicate_courses(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    service._datastore.set_courses([_make_course("11111")])

    courses_file = tmp_path / "c.txt"
    courses_file.write_text("x")
    dates_file = tmp_path / "d.txt"
    dates_file.write_text("x")

    with patch("src.presenter.app_service.CourseFileParser") as MockCFP, \
         patch("src.presenter.app_service.ExamPeriodFileParser") as MockEFP:
        MockCFP.return_value.parse.return_value = [_make_course("11111")]  # duplicate
        MockEFP.return_value.parse.return_value = [_make_period()]

        service.load_data(str(courses_file), str(dates_file), "append")

    assert len(service._datastore.get_all_courses()) == 1


# ------------------------------------------------------------------ #
# select_programs                                                      #
# ------------------------------------------------------------------ #

def test_select_programs_stores_valid_ids(monkeypatch):
    service = _make_service(monkeypatch)
    service.select_programs(["83101", "83102"])
    assert service._selected_programs == ["83101", "83102"]


def test_select_programs_raises_when_more_than_five(monkeypatch):
    service = _make_service(monkeypatch)
    with pytest.raises(ValueError, match="5"):
        service.select_programs(["83101", "83102", "83103", "83104", "83105", "83106"])


def test_select_programs_raises_for_non_5_digit_id(monkeypatch):
    service = _make_service(monkeypatch)
    with pytest.raises(ValueError):
        service.select_programs(["831"])  # too short


def test_select_programs_raises_for_non_numeric_id(monkeypatch):
    service = _make_service(monkeypatch)
    with pytest.raises(ValueError):
        service.select_programs(["ABCDE"])


def test_select_programs_raises_for_non_string_id(monkeypatch):
    service = _make_service(monkeypatch)
    with pytest.raises(ValueError):
        service.select_programs([83101])   # int, not str


def test_select_programs_accepts_exactly_five(monkeypatch):
    service = _make_service(monkeypatch)
    ids = ["83101", "83102", "83103", "83104", "83105"]
    service.select_programs(ids)   # must not raise
    assert len(service._selected_programs) == 5


# ------------------------------------------------------------------ #
# get_available_programs                                               #
# ------------------------------------------------------------------ #

def test_get_available_programs_returns_id_and_name(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_courses([_make_course("11111", "83101")])

    programs = service.get_available_programs()
    assert len(programs) == 1
    assert programs[0]["id"] == "83101"
    assert "name" in programs[0]


def test_get_available_programs_empty_when_no_courses(monkeypatch):
    service = _make_service(monkeypatch)
    assert service.get_available_programs() == []


# ------------------------------------------------------------------ #
# get_courses                                                          #
# ------------------------------------------------------------------ #

def test_get_courses_returns_required_fields(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_courses([_make_course("11111", "83101")])

    courses = service.get_courses("83101")
    assert len(courses) == 1
    entry = courses[0]
    assert entry["number"] == "11111"
    assert "name" in entry
    assert "year" in entry
    assert "semester" in entry
    assert "type" in entry
    assert "evaluation" in entry


def test_get_courses_returns_only_matching_program(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_courses([
        _make_course("11111", "83101"),
        _make_course("22222", "83102"),
    ])

    courses = service.get_courses("83101")
    assert len(courses) == 1
    assert courses[0]["number"] == "11111"


def test_get_courses_empty_for_unknown_program(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_courses([_make_course("11111", "83101")])

    assert service.get_courses("99999") == []


# ------------------------------------------------------------------ #
# get_periods                                                          #
# ------------------------------------------------------------------ #

def test_get_periods_returns_required_fields(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_periods([_make_period()])

    periods = service.get_periods()
    assert len(periods) == 1
    p = periods[0]
    assert "id" in p
    assert "semester" in p
    assert "moed" in p
    assert "start_date" in p
    assert "end_date" in p
    assert "allowed_days" in p
    assert "forbidden_days" in p


def test_get_periods_id_format(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_periods([_make_period(Semester.FALL, Moed.Aleph)])

    periods = service.get_periods()
    assert periods[0]["id"] == "FALL_Aleph"


# ------------------------------------------------------------------ #
# toggle_day                                                           #
# ------------------------------------------------------------------ #

def test_toggle_day_adds_day_to_forbidden(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period()
    service._datastore.set_periods([period])

    day = date(2026, 2, 1)
    service.toggle_day("FALL_Aleph", day)

    assert day in period.forbidden_days


def test_toggle_day_removes_day_from_forbidden_on_second_call(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period()
    service._datastore.set_periods([period])

    day = date(2026, 2, 1)
    service.toggle_day("FALL_Aleph", day)   # forbid
    service.toggle_day("FALL_Aleph", day)   # allow again

    assert day not in period.forbidden_days


def test_toggle_day_raises_for_unknown_period(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_periods([_make_period()])

    with pytest.raises(ValueError):
        service.toggle_day("SUMM_Gimel", date(2026, 2, 1))


# ------------------------------------------------------------------ #
# shift_period                                                         #
# ------------------------------------------------------------------ #

def test_shift_period_updates_dates(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period()
    service._datastore.set_periods([period])

    new_start = date(2026, 3, 1)
    new_end   = date(2026, 3, 31)
    service.shift_period("FALL_Aleph", new_start, new_end)

    assert period.start_date == new_start
    assert period.end_date   == new_end


def test_shift_period_raises_when_start_equals_end(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_periods([_make_period()])

    same_day = date(2026, 3, 15)
    with pytest.raises(ValueError):
        service.shift_period("FALL_Aleph", same_day, same_day)


def test_shift_period_raises_when_start_after_end(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_periods([_make_period()])

    with pytest.raises(ValueError):
        service.shift_period("FALL_Aleph", date(2026, 3, 31), date(2026, 3, 1))


def test_shift_period_raises_for_unknown_period(monkeypatch):
    service = _make_service(monkeypatch)
    service._datastore.set_periods([_make_period()])

    with pytest.raises(ValueError):
        service.shift_period("SUMM_Gimel", date(2026, 3, 1), date(2026, 3, 31))


# ------------------------------------------------------------------ #
# generate()                                                           #
# ------------------------------------------------------------------ #

def test_generate_raises_when_no_programs_selected(monkeypatch):
    service = _make_service(monkeypatch)
    # No programs selected — should raise immediately
    with pytest.raises(ValueError, match="No programs selected"):
        service.generate()


def test_generate_raises_when_no_periods_configured(monkeypatch):
    service = _make_service(monkeypatch)
    service._selected_programs = ["83101"]
    # No periods in the data store
    with pytest.raises(ValueError, match="No exam period is configured"):
        service.generate()


def test_generate_raises_when_no_courses_match_periods(monkeypatch):
    service = _make_service(monkeypatch)
    service._selected_programs = ["83101"]
    service._datastore.set_periods([_make_period()])
    # No courses in the data store → scheduling_tasks will be empty
    with pytest.raises(ValueError, match="No courses from the selected programs"):
        service.generate()


def test_generate_returns_schedule_count(monkeypatch):
    service = _make_service(monkeypatch)
    service._selected_programs = ["83101"]

    period = _make_period()
    course = _make_course("11111")
    fake_schedules = [_make_schedule(period, course, date(2026, 2, 1))]

    def fake_prepare():
        engine = MagicMock()
        engine.generateAll.return_value = (fake_schedules, {})
        return engine, {}

    monkeypatch.setattr(service, "_prepare_engine", fake_prepare)

    count = service.generate()
    assert count == 1


def test_generate_zero_when_engine_finds_nothing(monkeypatch):
    service = _make_service(monkeypatch)
    service._selected_programs = ["83101"]

    def fake_prepare():
        engine = MagicMock()
        engine.generateAll.return_value = ([], {})
        return engine, {}

    monkeypatch.setattr(service, "_prepare_engine", fake_prepare)

    assert service.generate() == 0


def test_generate_stream_ignores_score_events_without_type(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period()
    messages = iter([
        {"event": "batch_written", "period_id": period.period_id, "count": 1},
        {"type": "all_done"},
    ])

    class FakeEngineProcess:
        def stop(self):
            pass

        def start(self, engine, scheduling_tasks, constraint_settings):
            pass

        def get_notification(self):
            return next(messages)

    class FakeWriter:
        def clear_period(self, period_id):
            pass

    monkeypatch.setattr(service, "_prepare_engine", lambda: (MagicMock(), {period: {}}))
    monkeypatch.setattr("src.algorithm.period_results_writer.PeriodResultsWriter", FakeWriter)
    service._engine_process = FakeEngineProcess()

    assert list(service.generate_stream()) == [
        (period.period_id, []),
        (period.period_id, []),
    ]


# ------------------------------------------------------------------ #
# get_schedule()                                                       #
# ------------------------------------------------------------------ #

def test_get_schedule_raises_index_error_when_empty(monkeypatch):
    service = _make_service(monkeypatch)
    with pytest.raises(IndexError):
        service.get_schedule(0)


def test_get_schedule_raises_index_error_for_negative(monkeypatch):
    service = _make_service(monkeypatch)
    with pytest.raises(IndexError):
        service.get_schedule(-1)


def test_get_schedule_raises_index_error_out_of_range(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period()
    course = _make_course("11111")
    service._results = [_make_schedule(period, course, date(2026, 2, 1))]
    service._selected_programs = ["83101"]

    with pytest.raises(IndexError):
        service.get_schedule(1)   # only index 0 exists


def test_get_schedule_returns_nested_dict_structure(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period(Semester.FALL, Moed.Aleph)
    course = _make_course("11111", "83101")
    schedule = _make_schedule(period, course, date(2026, 2, 1))

    service._results = [schedule]
    service._selected_programs = ["83101"]

    result = service.get_schedule(0)

    # Top level: semester string
    assert "FALL" in result
    # Second level: moed string
    assert "Aleph" in result["FALL"]
    # Third level: list of dicts
    entries = result["FALL"]["Aleph"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["course_number"] == "11111"
    assert "course_name" in entry
    assert "type" in entry
    assert "programs" in entry
    assert "exam_date" in entry


def test_get_schedule_programs_list_contains_selected_program(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period()
    course = _make_course("11111", "83101")
    service._results = [_make_schedule(period, course, date(2026, 2, 1))]
    service._selected_programs = ["83101"]

    result = service.get_schedule(0)
    entry = result["FALL"]["Aleph"][0]
    assert "83101" in entry["programs"]


# ------------------------------------------------------------------ #
# get_schedule_count()                                                 #
# ------------------------------------------------------------------ #

def test_get_schedule_count_zero_initially(monkeypatch):
    service = _make_service(monkeypatch)
    assert service.get_schedule_count() == 0


def test_get_schedule_count_matches_results(monkeypatch):
    service = _make_service(monkeypatch)
    period = _make_period()
    course = _make_course("11111")
    service._results = [
        _make_schedule(period, course, date(2026, 2, 1)),
        _make_schedule(period, course, date(2026, 2, 2)),
    ]
    assert service.get_schedule_count() == 2


# ------------------------------------------------------------------ #
# export_schedule()                                                    #
# ------------------------------------------------------------------ #

def test_export_schedule_raises_index_error_when_empty(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    with pytest.raises(IndexError):
        service.export_schedule(0, str(tmp_path / "out.txt"))


def test_export_schedule_calls_writer(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    period = _make_period()
    course = _make_course("11111")
    service._results = [_make_schedule(period, course, date(2026, 2, 1))]
    service._selected_programs = ["83101"]

    output_path = str(tmp_path / "out.txt")

    with patch("src.presenter.app_service.ScheduleReportWriter") as MockWriter:
        service.export_schedule(0, output_path)
        MockWriter.return_value.write.assert_called_once()


def test_export_schedule_passes_correct_index(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    period = _make_period()
    course = _make_course("11111")
    s0 = _make_schedule(period, course, date(2026, 2, 1))
    s1 = _make_schedule(period, course, date(2026, 2, 2))
    service._results = [s0, s1]
    service._selected_programs = ["83101"]

    output_path = str(tmp_path / "out.txt")

    with patch("src.presenter.app_service.ScheduleReportWriter") as MockWriter:
        service.export_schedule(1, output_path)
        call_kwargs = MockWriter.return_value.write.call_args
        # The "schedules" arg must contain exactly s1
        assert call_kwargs.kwargs["schedules"] == [s1]

# ------------------------------------------------------------------ #
# EP-74 & EP-77 — Program Names Auto-Loading                         #
# ------------------------------------------------------------------ #

def test_init_auto_loads_default_program_names(monkeypatch, tmp_path):
    """Test that __init__ attempts to load the default programs file if it exists."""
    default_file = tmp_path / "programsName.txt"
    default_file.write_text("83101 Test Program", encoding="utf-8")

    # Mock the default path to point to our temp file
    monkeypatch.setattr(AppService, "_default_program_names_path", lambda self: str(default_file))
    
    # Prevent actual DataStore load/save from doing I/O
    monkeypatch.setattr(DataStore, "load", lambda self: False)
    monkeypatch.setattr(DataStore, "save", lambda self: None)

    with patch.object(DataStore, "set_program_names") as mock_set:
        service = AppService()  # init triggers _load_default_program_names
        mock_set.assert_called_once()
        args, _ = mock_set.call_args
        # The argument to set_program_names should be the dict parsed from our default file
        assert args[0] == {"83101": "Test Program"}


def test_load_data_uses_explicit_programs_path(monkeypatch, tmp_path):
    """Test that load_data prefers an explicitly provided programs_path."""
    service = _make_service(monkeypatch)
    
    courses_file = tmp_path / "c.txt"
    courses_file.write_text("c")
    dates_file = tmp_path / "d.txt"
    dates_file.write_text("d")
    explicit_p_file = tmp_path / "explicit_p.txt"
    explicit_p_file.write_text("11111 Explicit Program", encoding="utf-8")

    # Mock parsers so they don't do actual work or crash
    with patch("src.presenter.app_service.CourseFileParser"), \
         patch("src.presenter.app_service.ExamPeriodFileParser"):
         
        with patch.object(service._datastore, "set_program_names") as mock_set:
            service.load_data(str(courses_file), str(dates_file), "replace", programs_path=str(explicit_p_file))
            
            mock_set.assert_called_once()
            args, _ = mock_set.call_args
            assert args[0] == {"11111": "Explicit Program"}


def test_load_data_falls_back_to_default_programs_path(monkeypatch, tmp_path):
    """Test that load_data uses the default path if no explicit path is given."""
    service = _make_service(monkeypatch)
    
    courses_file = tmp_path / "c.txt"
    courses_file.write_text("c")
    dates_file = tmp_path / "d.txt"
    dates_file.write_text("d")
    default_p_file = tmp_path / "default_p.txt"
    default_p_file.write_text("22222 Default Program", encoding="utf-8")

    # Force the fallback path
    monkeypatch.setattr(service, "_default_program_names_path", lambda: str(default_p_file))

    with patch("src.presenter.app_service.CourseFileParser"), \
         patch("src.presenter.app_service.ExamPeriodFileParser"):
         
        with patch.object(service._datastore, "set_program_names") as mock_set:
            # programs_path is omitted/None
            service.load_data(str(courses_file), str(dates_file), "append")
            
            mock_set.assert_called_once()
            args, _ = mock_set.call_args
            assert args[0] == {"22222": "Default Program"}
            

def test_load_data_skips_programs_if_none_provided_and_no_default(monkeypatch, tmp_path):
    """Test that load_data doesn't crash if no explicit and no default path exist."""
    service = _make_service(monkeypatch)
    
    courses_file = tmp_path / "c.txt"
    courses_file.write_text("c")
    dates_file = tmp_path / "d.txt"
    dates_file.write_text("d")

    # Force default path to return None (simulating file missing)
    monkeypatch.setattr(service, "_default_program_names_path", lambda: None)

    with patch("src.presenter.app_service.CourseFileParser"), \
         patch("src.presenter.app_service.ExamPeriodFileParser"):
         
        with patch.object(service._datastore, "set_program_names") as mock_set:
            service.load_data(str(courses_file), str(dates_file), "replace")
            # Should not be called because there's no programs path at all
            mock_set.assert_not_called()


def test_load_data_raises_file_not_found_for_missing_programs_path(monkeypatch, tmp_path):
    """Test that providing an invalid programs_path raises an error."""
    service = _make_service(monkeypatch)
    courses_file = tmp_path / "c.txt"
    courses_file.write_text("c")
    dates_file = tmp_path / "d.txt"
    dates_file.write_text("d")
    
    missing_p_file = tmp_path / "missing_p.txt"
    
    with pytest.raises(FileNotFoundError):
        # We explicitly pass a path that does not exist
        service.load_data(str(courses_file), str(dates_file), "replace", programs_path=str(missing_p_file))


# ------------------------------------------------------------------ #
# EP-119 — ranked sort order and frozen cache                         #
# ------------------------------------------------------------------ #

def test_set_sort_order_stores_columns(monkeypatch):
    service = _make_service(monkeypatch)
    service.set_sort_order(["min_days_required", "avg_days_all"])
    assert service.get_sort_order() == ["min_days_required", "avg_days_all"]
    assert service._sort_cols == ["min_days_required", "avg_days_all"]




def test_get_period_schedule_falls_back_when_no_sort_active(monkeypatch):
    """With no sort order set, get_period_schedule must not touch scores.db."""
    service = _make_service(monkeypatch)
    # No set_sort_order call - _sort_cols stays empty

    disk_called = []
    monkeypatch.setattr(
        service._results_reader, "get_count",
        lambda pid: (disk_called.append(pid) or 1),
    )
    fake_schedule = MagicMock()
    monkeypatch.setattr(service._results_reader, "get_schedule_at", lambda pid, idx: fake_schedule)
    monkeypatch.setattr(service, "_format_schedule_rows", lambda s: [])

    service.get_period_schedule("FALL_Aleph", 0)

    # went through disk path, not ranked path
    assert "FALL_Aleph" in disk_called  


# ------------------------------------------------------------------ #
# _format_schedule_rows — room scheduling integration                  #
# ------------------------------------------------------------------ #

def test_format_schedule_rows_room_based(monkeypatch):
    """_format_schedule_rows must produce rooms_display strings and capacity keys
    when the placement carries time-slot and room data."""

    service = _make_service(monkeypatch)
    service._selected_programs = {"83101"}

    course = _make_course("10001")
    course.num_students = 45

    period = _make_period()
    room = Room("202", "B", 60)  # Room(room_id, building, capacity)
    placement = ExamPlacement(date(2026, 2, 1), TimeSlot.MORNING, (room,))

    schedule = ExamSchedule(period)
    schedule.assign(course, placement)

    rows = service._format_schedule_rows(schedule)

    assert len(rows) == 1
    row = rows[0]

    assert row["time_slot"] == "MORNING"
    assert row["num_students"] == 45
    assert row["total_capacity"] == 60
    assert "rooms_display" in row
    assert len(row["rooms_display"]) == 1
    assert "Building B" in row["rooms_display"][0]
    assert "202" in row["rooms_display"][0]
    assert "60 seats" in row["rooms_display"][0]


def test_format_schedule_rows_date_only(monkeypatch):
    """Date-only placements must not produce room keys — existing callers unaffected."""
    service = _make_service(monkeypatch)
    service._selected_programs = {"83101"}

    course  = _make_course("10002")
    period  = _make_period()
    schedule = _make_schedule(period, course, date(2026, 2, 1))

    rows = service._format_schedule_rows(schedule)

    assert len(rows) == 1
    row = rows[0]
    assert "time_slot"     not in row
    assert "rooms_display" not in row
    assert "num_students"  not in row
    assert "total_capacity" not in row


# ------------------------------------------------------------------ #
# clear_rooms - stale data after failed load                           #
# ------------------------------------------------------------------ #

def test_clear_rooms_after_failed_load_removes_stored_rooms(monkeypatch):
    """Valid rooms loaded → invalid file selected → DataStore rooms must be empty.

    Covers the reviewer's requirement: a failed room-file parse must invalidate
    any previously loaded rooms so the engine cannot silently use stale data.
    """
    service = _make_service(monkeypatch)

    # Prime DataStore with a valid room set (simulates a successful prior load).
    service._datastore.set_rooms([Room("101", "A", 50)])
    assert len(service._datastore.get_rooms()) == 1

    # clear_rooms() is what _on_rooms_file_selected calls on parse failure.
    service.clear_rooms()

    assert service._datastore.get_rooms() == []
    assert service.needs_generation() is True


# ------------------------------------------------------------------ #
# PDF / TXT export writer selection                                    #
# ------------------------------------------------------------------ #

def test_create_export_writer_returns_pdf_writer_for_pdf(monkeypatch):
    """Verify that AppService selects PdfScheduleReportWriter for .pdf paths."""
    service = _make_service(monkeypatch)

    writer = service._create_export_writer("report.pdf")

    assert isinstance(writer, PdfScheduleReportWriter)


def test_create_export_writer_returns_text_writer_for_txt(monkeypatch):
    """Verify that AppService selects ScheduleReportWriter for .txt paths."""
    service = _make_service(monkeypatch)

    writer = service._create_export_writer("report.txt")

    assert isinstance(writer, ScheduleReportWriter)


def test_create_export_writer_is_case_insensitive_for_pdf(monkeypatch):
    """Verify that uppercase .PDF paths are still exported as PDF."""
    service = _make_service(monkeypatch)

    writer = service._create_export_writer("REPORT.PDF")

    assert isinstance(writer, PdfScheduleReportWriter)


# ------------------------------------------------------------------ #
# validate_manual_move - integration: dict keys from get_period_schedule
# ------------------------------------------------------------------ #

def test_validate_manual_move_dict_keys_match_validator_contract(monkeypatch):
    """
    Integration test: pass real get_period_schedule() output into
    ManualMoveValidator to confirm all required dict keys are present
    and no KeyError is raised when the validator accesses them.
    """
    service = _make_service(monkeypatch)
    service._selected_programs = ["83101"]

    period = _make_period(Semester.FALL, Moed.Aleph)
    course = _make_course("11111", "83101")
    schedule = _make_schedule(period, course, date(2026, 2, 1))

    pid = "FALL_Aleph"
    service._datastore.set_periods([period])
    service._results_by_period[pid] = [schedule]

    rows = service.get_period_schedule(pid, 0)

    assert len(rows) == 1, "Expected one exam row from get_period_schedule()"
    moving = rows[0]

    # Verify the keys the validator requires are all present
    assert "course_number" in moving
    assert "course_name"   in moving
    assert "exam_date"     in moving
    assert "type"          in moving
    assert "programs"      in moving

    # Pass through the validator - must not raise KeyError
    target = date(2026, 2, 5)
    period_dict = service.get_periods()[0]
    errors = ManualMoveValidator().validate(
        exam_rows=rows,
        moving_exam=moving,
        target_date=target,
        period=period_dict,
        settings=service.get_constraint_settings(),
    )

    # Target date is within the period and no collisions - should be valid
    assert isinstance(errors, list)
    assert all(hasattr(e, "rule") and hasattr(e, "reason") for e in errors)


# ------------------------------------------------------------------ #
# save_manual_edit                                                   #
# ------------------------------------------------------------------ #

def test_save_manual_edit_overrides_get_period_schedule(monkeypatch):
    """After save_manual_edit, get_period_schedule returns the saved rows at the same index."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    period = _make_period()
    course = _make_course("11111")
    schedule = _make_schedule(period, course, date(2026, 2, 1))
    service._datastore.set_periods([period])
    service._results_by_period[pid] = [schedule]
    service._current_indices[pid] = 0

    original = service.get_period_schedule(pid, 0)
    assert len(original) == 1

    edited = [dict(original[0], exam_date=date(2026, 2, 5))]
    service.save_manual_edit(pid, 0, edited)

    result = service.get_period_schedule(pid, 0)
    assert result == edited


def test_save_manual_edit_does_not_affect_other_indices(monkeypatch):
    """Saving an edit at index 0 must not affect index 1."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    period = _make_period()
    course = _make_course("11111")
    schedules = [
        _make_schedule(period, course, date(2026, 2, 1)),
        _make_schedule(period, course, date(2026, 2, 2)),
    ]
    service._results_by_period[pid] = schedules

    service.save_manual_edit(pid, 0, [{"course_number": "edited"}])

    result_idx1 = service.get_period_schedule(pid, 1)
    assert result_idx1 != [{"course_number": "edited"}]


def test_save_manual_edit_stores_a_copy(monkeypatch):
    """Mutating the list after save must not affect get_period_schedule."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    rows = [{"course_number": "111", "exam_date": date(2026, 2, 1)}]
    service.save_manual_edit(pid, 0, rows)

    rows.append({"course_number": "999"})
    result = service.get_period_schedule(pid, 0)
    assert len(result) == 1


def test_save_manual_edit_closes_ranking_engine(monkeypatch):
    """Saving an edit must close and null the ranking engine."""
    service = _make_service(monkeypatch)
    mock_engine = MagicMock()
    service._ranking_engine = mock_engine

    service.save_manual_edit("FALL_Aleph", 0, [])

    mock_engine.close.assert_called_once()
    assert service._ranking_engine is None


def test_save_manual_edit_writes_to_disk_and_updates_scores(monkeypatch, tmp_path):
    """When disk results exist, save_manual_edit overwrites the batch file and updates scores.db."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    period = _make_period()
    course = _make_course("11111")
    schedule = _make_schedule(period, course, date(2026, 2, 1))

    # Set up a fake results directory with one batch file and manifest
    results_root = tmp_path / "results" / pid
    results_root.mkdir(parents=True)
    batch_path = results_root / "batch_0000.pkl"
    with open(batch_path, "wb") as f:
        pickle.dump([schedule], f)
    manifest = results_root / "manifest.json"
    manifest.write_text(json.dumps({"count": 1}))

    # Set up a fake scores.db with one row for this schedule
    scores_path = tmp_path / "results" / "scores.db"
    with sqlite3.connect(str(scores_path)) as conn:
        conn.execute("""
            CREATE TABLE scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id TEXT, batch_number INTEGER, index_in_batch INTEGER,
                min_days_required REAL, avg_days_all REAL,
                elective_conflicts INTEGER, span_required INTEGER,
                max_exams_per_day INTEGER, avg_room_distance REAL DEFAULT 0
            )
        """)
        conn.execute(
            "INSERT INTO scores VALUES (NULL,?,?,?,?,?,?,?,?,?)",
            (pid, 0, 0, 1.0, 2.0, 0, 10, 3, 0.0),
        )
        conn.commit()

    # Point service to the tmp results directory
    service._results_reader = ResultsReader(root_path=tmp_path / "results")
    service._datastore.set_periods([period])
    service._datastore.set_courses([course])

    edited_rows = [{"course_number": "11111", "exam_date": date(2026, 2, 5)}]
    service.save_manual_edit(pid, 0, edited_rows)

    # Batch file should be updated on disk: new date must be stored
    with open(batch_path, "rb") as f:
        batch = pickle.load(f)
    stored_schedule = batch[0]
    stored_dates = list(stored_schedule.assignments.values())
    assert stored_dates == [date(2026, 2, 5)]

    # scores.db row should be updated (not duplicated)
    with sqlite3.connect(str(scores_path)) as conn:
        rows = conn.execute("SELECT * FROM scores WHERE period_id=?", (pid,)).fetchall()
    assert len(rows) == 1


def test_save_manual_edit_preserves_room_data_on_disk(monkeypatch, tmp_path):
    """Room placements (time_slot + room_ids) must survive the disk write-back."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    period = _make_period()
    course = _make_course("11111")
    room = Room(room_id="101", building="B1", capacity=50)

    placement = ExamPlacement.with_rooms(date(2026, 2, 1), TimeSlot.MORNING, (room,))
    schedule = ExamSchedule(period)
    schedule.assign(course, placement)

    results_root = tmp_path / "results" / pid
    results_root.mkdir(parents=True)
    batch_path = results_root / "batch_0000.pkl"
    with open(batch_path, "wb") as f:
        pickle.dump([schedule], f)
    (results_root / "manifest.json").write_text(json.dumps({"count": 1}))

    service._results_reader = ResultsReader(root_path=tmp_path / "results")
    service._datastore.set_periods([period])
    service._datastore.set_courses([course])
    service._datastore.set_rooms([room])

    # Move exam to a new date while keeping the same room/slot
    edited_rows = [{
        "course_number": "11111",
        "exam_date": date(2026, 2, 5),
        "time_slot": "MORNING",
        "room_ids": ["B1:101"],
    }]
    service.save_manual_edit(pid, 0, edited_rows)

    with open(batch_path, "rb") as f:
        batch = pickle.load(f)
    stored = batch[0]
    placements = list(stored.placements.values())
    assert len(placements) == 1
    p = placements[0]
    assert p.date == date(2026, 2, 5)
    assert p.time_slot == TimeSlot.MORNING
    assert len(p.rooms) == 1
    assert p.rooms[0].room_id == "101"
    assert p.rooms[0].building == "B1"


def test_clear_results_removes_manual_edits(monkeypatch):
    """clear_results must discard any saved manual edits."""
    service = _make_service(monkeypatch)
    service._manual_edits["FALL_Aleph"] = {0: [{"course_number": "111"}]}

    service.clear_results()

    assert service._manual_edits == {}


def test_save_manual_edit_uses_physical_index_when_ranking_active(monkeypatch, tmp_path):
    """When ranking is active, save_manual_edit must overwrite the physical slot,
    not the display (rank) position."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    period = _make_period()
    course = _make_course("11111")

    # Two schedules on disk: physical slot 0 (Feb 1) and slot 1 (Feb 2).
    sched_0 = _make_schedule(period, course, date(2026, 2, 1))
    sched_1 = _make_schedule(period, course, date(2026, 2, 2))

    results_root = tmp_path / "results" / pid
    results_root.mkdir(parents=True)
    batch_path = results_root / "batch_0000.pkl"
    with open(batch_path, "wb") as f:
        pickle.dump([sched_0, sched_1], f)
    (results_root / "manifest.json").write_text(json.dumps({"count": 2}))

    scores_path = tmp_path / "results" / "scores.db"
    with sqlite3.connect(str(scores_path)) as conn:
        conn.execute("""
            CREATE TABLE scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id TEXT, batch_number INTEGER, index_in_batch INTEGER,
                min_days_required REAL, avg_days_all REAL,
                elective_conflicts INTEGER, span_required INTEGER,
                max_exams_per_day INTEGER, avg_room_distance REAL DEFAULT 0
            )
        """)
        conn.execute("INSERT INTO scores VALUES (NULL,?,?,?,?,?,?,?,?,?)", (pid, 0, 0, 1.0, 2.0, 0, 10, 3, 0.0))
        conn.execute("INSERT INTO scores VALUES (NULL,?,?,?,?,?,?,?,?,?)", (pid, 0, 1, 1.0, 2.0, 0, 10, 3, 0.0))
        conn.commit()

    service._results_reader = ResultsReader(root_path=tmp_path / "results")
    service._datastore.set_periods([period])
    service._datastore.set_courses([course])

    # Ranking engine says: rank 0 → physical slot 1 (the schedule at batch 0, index 1).
    fake_engine = MagicMock()
    fake_engine.fetch_window.return_value = [(0, 1, 1.0, 2.0, 0, 10, 3, 0.0)]
    service._ranking_engine = fake_engine
    service._sort_cols = ["min_days_required"]

    edited_rows = [{"course_number": "11111", "exam_date": date(2026, 2, 9)}]
    service.save_manual_edit(pid, 0, edited_rows)

    with open(batch_path, "rb") as f:
        batch = pickle.load(f)

    # Physical slot 0 (Feb 1) must be untouched.
    assert list(batch[0].assignments.values()) == [date(2026, 2, 1)]
    # Physical slot 1 (Feb 2 → Feb 9) must be overwritten.
    assert list(batch[1].assignments.values()) == [date(2026, 2, 9)]


def test_resolve_physical_index_raises_when_ranking_engine_unavailable(monkeypatch, tmp_path):
    """If ranking is active but the engine is unavailable, raise RuntimeError."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    period = _make_period()
    course = _make_course("11111")
    schedule = _make_schedule(period, course, date(2026, 2, 1))

    results_root = tmp_path / "results" / pid
    results_root.mkdir(parents=True)
    with open(results_root / "batch_0000.pkl", "wb") as f:
        pickle.dump([schedule], f)
    (results_root / "manifest.json").write_text(json.dumps({"count": 1}))

    service._results_reader = ResultsReader(root_path=tmp_path / "results")
    service._datastore.set_periods([period])
    service._datastore.set_courses([course])
    service._sort_cols = ["min_days_required"]
    # No scores.db → engine returns None

    with pytest.raises(RuntimeError, match="ranking database is unavailable"):
        service.save_manual_edit(pid, 0, [{"course_number": "11111", "exam_date": date(2026, 2, 5)}])

    # In-memory cache must not be updated after a failed save.
    assert pid not in service._manual_edits


def test_resolve_physical_index_raises_when_engine_returns_no_rows(monkeypatch, tmp_path):
    """If the ranking engine returns no rows for the requested rank, raise RuntimeError."""
    service = _make_service(monkeypatch)
    pid = "FALL_Aleph"
    period = _make_period()
    course = _make_course("11111")
    schedule = _make_schedule(period, course, date(2026, 2, 1))

    results_root = tmp_path / "results" / pid
    results_root.mkdir(parents=True)
    with open(results_root / "batch_0000.pkl", "wb") as f:
        pickle.dump([schedule], f)
    (results_root / "manifest.json").write_text(json.dumps({"count": 1}))

    # scores.db must exist so _get_ranking_engine doesn't short-circuit to None.
    scores_path = tmp_path / "results" / "scores.db"
    with sqlite3.connect(str(scores_path)) as conn:
        conn.execute("""
            CREATE TABLE scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id TEXT, batch_number INTEGER, index_in_batch INTEGER,
                min_days_required REAL, avg_days_all REAL,
                elective_conflicts INTEGER, span_required INTEGER,
                max_exams_per_day INTEGER, avg_room_distance REAL DEFAULT 0
            )
        """)
        conn.commit()

    service._results_reader = ResultsReader(root_path=tmp_path / "results")
    service._datastore.set_periods([period])
    service._datastore.set_courses([course])

    fake_engine = MagicMock()
    fake_engine.fetch_window.return_value = []
    service._ranking_engine = fake_engine
    service._sort_cols = ["min_days_required"]

    with pytest.raises(RuntimeError, match="failed to resolve the ranked schedule index"):
        service.save_manual_edit(pid, 0, [{"course_number": "11111", "exam_date": date(2026, 2, 5)}])

    # In-memory cache must not be updated after a failed save.
    assert pid not in service._manual_edits


# ------------------------------------------------------------------ #
# rank_of_last_saved_edit                                             #
# ------------------------------------------------------------------ #

def test_rank_of_last_saved_edit_returns_none_before_any_save(monkeypatch):
    service = _make_service(monkeypatch)
    assert service.rank_of_last_saved_edit("FALL_Aleph") is None


def test_rank_of_last_saved_edit_returns_none_for_wrong_period(monkeypatch):
    service = _make_service(monkeypatch)
    service._last_saved_physical = ("FALL_Aleph", 3)
    assert service.rank_of_last_saved_edit("SPRI_Aleph") is None


def test_rank_of_last_saved_edit_returns_physical_index_when_no_sort(monkeypatch):
    service = _make_service(monkeypatch)
    service._last_saved_physical = ("FALL_Aleph", 7)
    service._sort_cols = []
    assert service.rank_of_last_saved_edit("FALL_Aleph") == 7


def test_rank_of_last_saved_edit_returns_physical_index_when_no_engine(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    service._last_saved_physical = ("FALL_Aleph", 5)
    service._sort_cols = ["span_required"]
    # No scores.db -> _get_ranking_engine returns None -> falls back to physical index
    service._results_reader = ResultsReader(root_path=tmp_path / "results")
    assert service.rank_of_last_saved_edit("FALL_Aleph") == 5


def test_rank_of_last_saved_edit_queries_find_rank_when_sort_active(monkeypatch, tmp_path):
    from src.presenter.scores_database import ScoresDatabase, ScheduleMetrics

    service = _make_service(monkeypatch)

    results_root = tmp_path / "results"
    results_root.mkdir(parents=True)
    db_path = results_root / "scores.db"

    db = ScoresDatabase(db_path)
    db.insert("FALL_Aleph", 0, 0, ScheduleMetrics(1, 1, 0, 5,  1, 0.0))
    db.insert("FALL_Aleph", 0, 1, ScheduleMetrics(1, 1, 0, 20, 1, 0.0))
    db.insert("FALL_Aleph", 0, 2, ScheduleMetrics(1, 1, 0, 10, 1, 0.0))
    db.close()

    service._results_reader = ResultsReader(root_path=results_root)
    service._sort_cols = ["span_required"]
    # Physical index 1 -> batch 0, slot 1 -> span=20 -> rank 0 (best)
    service._last_saved_physical = ("FALL_Aleph", 1)

    assert service.rank_of_last_saved_edit("FALL_Aleph") == 0
