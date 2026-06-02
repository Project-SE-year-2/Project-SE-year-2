"""
Unit tests for DataStore — persistence, merging, and query helpers.

All file-system tests use pytest's tmp_path fixture so nothing is
written to the real project data/ directory.
"""

import pytest
from datetime import date

from src.presenter.data_store import DataStore, _period_id
from src.models.course import Course
from src.models.exam_period import ExamPeriod
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, Moed, ReqType


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
    return ExamPeriod(semester, moed, date(2026, 2, 1), date(2026, 2, 28))


# ------------------------------------------------------------------ #
# is_empty                                                             #
# ------------------------------------------------------------------ #

def test_is_empty_on_fresh_store(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    assert store.is_empty() is True


def test_is_not_empty_after_adding_course(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_courses([_make_course("11111")])
    assert store.is_empty() is False


def test_is_not_empty_after_adding_period(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_periods([_make_period()])
    assert store.is_empty() is False


# ------------------------------------------------------------------ #
# save / load roundtrip                                               #
# ------------------------------------------------------------------ #

def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "ds.pkl"
    store = DataStore(path)
    store.set_courses([_make_course("11111")])
    store.set_periods([_make_period()])
    store.save()

    store2 = DataStore(path)
    result = store2.load()

    assert result is True
    assert len(store2.get_all_courses()) == 1
    assert store2.get_all_courses()[0].course_id == "11111"
    assert len(store2.get_periods()) == 1
    assert store2.get_periods()[0].semester == Semester.FALL


def test_load_returns_false_when_no_file(tmp_path):
    store = DataStore(tmp_path / "nonexistent.pkl")
    assert store.load() is False


def test_load_returns_empty_lists_when_no_file(tmp_path):
    store = DataStore(tmp_path / "nonexistent.pkl")
    store.load()
    assert store.get_all_courses() == []
    assert store.get_periods() == []


# ------------------------------------------------------------------ #
# clear                                                                #
# ------------------------------------------------------------------ #

def test_clear_wipes_memory(tmp_path):
    path = tmp_path / "ds.pkl"
    store = DataStore(path)
    store.set_courses([_make_course("11111")])
    store.set_periods([_make_period()])
    store.clear()

    assert store.get_all_courses() == []
    assert store.get_periods() == []


def test_clear_deletes_file(tmp_path):
    path = tmp_path / "ds.pkl"
    store = DataStore(path)
    store.set_courses([_make_course("11111")])
    store.save()
    assert path.exists()

    store.clear()
    assert not path.exists()


def test_clear_is_safe_when_no_file(tmp_path):
    """clear() must not raise when no file exists yet."""
    store = DataStore(tmp_path / "no_file.pkl")
    store.clear()   # should not raise


# ------------------------------------------------------------------ #
# merge_courses — deduplication                                        #
# ------------------------------------------------------------------ #

def test_merge_courses_adds_new_courses(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_courses([_make_course("11111")])
    store.merge_courses([_make_course("22222")])

    ids = {c.course_id for c in store.get_all_courses()}
    assert ids == {"11111", "22222"}


def test_merge_courses_skips_duplicates(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_courses([_make_course("11111")])
    store.merge_courses([_make_course("11111")])   # same id again

    assert len(store.get_all_courses()) == 1


def test_merge_courses_preserves_original_object_on_conflict(tmp_path):
    """When a duplicate arrives the *original* object is kept."""
    store = DataStore(tmp_path / "ds.pkl")
    original = _make_course("11111")
    original.name = "Original"
    duplicate = _make_course("11111")
    duplicate.name = "Duplicate"

    store.set_courses([original])
    store.merge_courses([duplicate])

    assert store.get_all_courses()[0].name == "Original"


# ------------------------------------------------------------------ #
# merge_periods — deduplication                                        #
# ------------------------------------------------------------------ #

def test_merge_periods_adds_new_period(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_periods([_make_period(Semester.FALL, Moed.Aleph)])
    store.merge_periods([_make_period(Semester.SPRI, Moed.Aleph)])

    assert len(store.get_periods()) == 2


def test_merge_periods_skips_duplicate_semester_moed(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_periods([_make_period(Semester.FALL, Moed.Aleph)])
    store.merge_periods([_make_period(Semester.FALL, Moed.Aleph)])

    assert len(store.get_periods()) == 1


# ------------------------------------------------------------------ #
# get_period_by_id                                                     #
# ------------------------------------------------------------------ #

def test_get_period_by_id_returns_correct_period(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    fall = _make_period(Semester.FALL, Moed.Aleph)
    spri = _make_period(Semester.SPRI, Moed.Bet)
    store.set_periods([fall, spri])

    result = store.get_period_by_id("FALL_Aleph")
    assert result is fall


def test_get_period_by_id_returns_none_for_unknown(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_periods([_make_period(Semester.FALL, Moed.Aleph)])

    assert store.get_period_by_id("SUMM_Gimel") is None


def test_get_period_by_id_returns_none_on_empty_store(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    assert store.get_period_by_id("FALL_Aleph") is None


# ------------------------------------------------------------------ #
# get_courses_for_program                                              #
# ------------------------------------------------------------------ #

def test_get_courses_for_program_returns_only_matching(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    c1 = _make_course("11111", "83101")
    c2 = _make_course("22222", "83102")
    store.set_courses([c1, c2])

    result = store.get_courses_for_program("83101")
    assert len(result) == 1
    assert result[0].course_id == "11111"


def test_get_courses_for_program_returns_empty_for_unknown(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_courses([_make_course("11111", "83101")])

    assert store.get_courses_for_program("99999") == []


# ------------------------------------------------------------------ #
# get_programs — derived from courses                                  #
# ------------------------------------------------------------------ #

def test_get_programs_returns_unique_ids(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    c1 = _make_course("11111", "83101")
    c2 = _make_course("22222", "83101")   # same program
    c3 = _make_course("33333", "83102")
    store.set_courses([c1, c2, c3])

    programs = store.get_programs()
    ids = [p["id"] for p in programs]
    assert sorted(ids) == ["83101", "83102"]


def test_get_programs_returns_id_and_name_fields(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_courses([_make_course("11111", "83101")])

    programs = store.get_programs()
    assert len(programs) == 1
    assert "id" in programs[0]
    assert "name" in programs[0]
    assert programs[0]["id"] == "83101"


def test_get_programs_empty_when_no_courses(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    assert store.get_programs() == []


# ------------------------------------------------------------------ #
# _period_id helper                                                    #
# ------------------------------------------------------------------ #

def test_period_id_format():
    period = _make_period(Semester.FALL, Moed.Aleph)
    assert _period_id(period) == "FALL_Aleph"


def test_period_id_uses_enum_values():
    period = _make_period(Semester.SPRI, Moed.Bet)
    assert _period_id(period) == "SPRI_Bet"
