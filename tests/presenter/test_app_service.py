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

import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from src.algorithm.period_results_writer import BATCH_SIZE
from src.presenter.app_service import AppService
from src.presenter.data_store import DataStore
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType


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


def test_set_sort_order_clears_sorted_cache(monkeypatch):
    service = _make_service(monkeypatch)
    service._sorted_cache["FALL_Aleph"] = [(0, 0), (0, 1)]
    service.set_sort_order(["avg_days_all"])
    assert service._sorted_cache == {}


def test_refresh_ranked_view_clears_sorted_cache(monkeypatch):
    service = _make_service(monkeypatch)
    service._sorted_cache["FALL_Aleph"] = [(0, 0)]
    service._sorted_cache["SPRI_Aleph"] = [(1, 2)]
    service.refresh_ranked_view()
    assert service._sorted_cache == {}


def test_build_sorted_cache_handles_empty_ranked_period(monkeypatch, tmp_path):
    service = _make_service(monkeypatch)
    service.set_sort_order(["min_days_required"])

    from src.presenter.scores_database import ScoresDatabase

    db_path = tmp_path / "scores.db"
    with ScoresDatabase(db_path):
        pass

    monkeypatch.setattr(service, "_scores_db_path", lambda: db_path)

    assert service._build_sorted_cache("FALL_Aleph") is True
    assert service._sorted_cache["FALL_Aleph"] == []


def test_get_period_schedule_uses_frozen_cache_when_sort_active(monkeypatch):
    """With sort active and a pre-built cache, get_period_schedule reads the
    schedule pointed to by the cache entry at the requested rank."""
    service = _make_service(monkeypatch)
    service.set_sort_order(["min_days_required"])

    # Inject a pre-built frozen cache: rank 0 → batch 0 position 2
    service._sorted_cache["FALL_Aleph"] = [(0, 2), (0, 0), (0, 1)]

    captured_index = []
    fake_schedule = MagicMock()
    monkeypatch.setattr(
        service._results_reader, "get_schedule_at",
        lambda pid, idx: (captured_index.append(idx) or fake_schedule),
    )
    monkeypatch.setattr(service, "_format_schedule_rows", lambda s: [{"ok": True}])

    result = service.get_period_schedule("FALL_Aleph", 0)

    assert result == [{"ok": True}]
    assert captured_index == [0 * BATCH_SIZE + 2]


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
# _format_schedule_rows - room scheduling integration                  #
# ------------------------------------------------------------------ #

def test_format_schedule_rows_room_based(monkeypatch):
    """_format_schedule_rows must produce rooms_display strings and capacity keys
    when the placement carries time-slot and room data."""
    from src.models.exam_placement import ExamPlacement
    from src.models.room import Room
    from src.models.enums import TimeSlot

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
