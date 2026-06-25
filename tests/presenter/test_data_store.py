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
from src.models.room import Room


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
# save / load roundtrip                                                #
# ------------------------------------------------------------------ #

def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "ds.pkl"
    store = DataStore(path)
    store.set_courses([_make_course("11111")])
    store.set_periods([_make_period()])
    store.set_program_names({"83101": "Computer Engineering"}) # EP-74
    store.save()

    store2 = DataStore(path)
    result = store2.load()

    assert result is True
    assert len(store2.get_all_courses()) == 1
    assert store2.get_all_courses()[0].course_id == "11111"
    assert len(store2.get_periods()) == 1
    assert store2.get_periods()[0].semester == Semester.FALL
    assert store2._program_names == {"83101": "Computer Engineering"} # EP-74


def test_load_returns_false_when_no_file(tmp_path):
    store = DataStore(tmp_path / "nonexistent.pkl")
    assert store.load() is False


def test_load_returns_empty_lists_when_no_file(tmp_path):
    store = DataStore(tmp_path / "nonexistent.pkl")
    store.load()
    assert store.get_all_courses() == []
    assert store.get_periods() == []
    assert store._program_names == {}


# ------------------------------------------------------------------ #
# clear                                                                #
# ------------------------------------------------------------------ #

def test_clear_wipes_memory(tmp_path):
    path = tmp_path / "ds.pkl"
    store = DataStore(path)
    store.set_courses([_make_course("11111")])
    store.set_periods([_make_period()])
    store.set_program_names({"83101": "Computer Engineering"}) # EP-74
    store.clear()

    assert store.get_all_courses() == []
    assert store.get_periods() == []
    assert store._program_names == {} # EP-74


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


def test_get_programs_empty_when_no_courses(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    assert store.get_programs() == []


# ------------------------------------------------------------------ #
# EP-74 Program Names Mapping                                        #
# ------------------------------------------------------------------ #

def test_set_program_names_updates_dict(tmp_path):
    """Test that setting program names correctly updates the internal dictionary."""
    store = DataStore(tmp_path / "ds.pkl")
    mapping = {"83101": "Computer Engineering", "83102": "Electrical Engineering"}
    store.set_program_names(mapping)
    assert store._program_names == mapping


def test_get_programs_uses_display_name_when_available(tmp_path):
    """Test that get_programs uses the mapped name instead of the ID if it exists."""
    store = DataStore(tmp_path / "ds.pkl")
    store.set_courses([_make_course("11111", "83101")])
    store.set_program_names({"83101": "Computer Engineering"})
    
    programs = store.get_programs()
    assert len(programs) == 1
    assert programs[0]["id"] == "83101"
    assert programs[0]["name"] == "Computer Engineering"


def test_get_programs_falls_back_to_id_when_name_missing(tmp_path):
    """Test that get_programs falls back to the program ID if no name mapping is found."""
    store = DataStore(tmp_path / "ds.pkl")
    store.set_courses([_make_course("11111", "99999")])
    # Mapping exists, but not for "99999"
    store.set_program_names({"83101": "Computer Engineering"})
    
    programs = store.get_programs()
    assert len(programs) == 1
    assert programs[0]["id"] == "99999"
    assert programs[0]["name"] == "99999"


# ------------------------------------------------------------------ #
# _period_id helper                                                    #
# ------------------------------------------------------------------ #

def test_period_id_format():
    period = _make_period(Semester.FALL, Moed.Aleph)
    assert _period_id(period) == "FALL_Aleph"


def test_period_id_uses_enum_values():
    period = _make_period(Semester.SPRI, Moed.Bet)
    assert _period_id(period) == "SPRI_Bet"


# ------------------------------------------------------------------ #
# Room persistence (Task 2: Persist Rooms in DataStore)              #
# ------------------------------------------------------------------ #

def _make_room(room_id: str = "101", building: str = "1", capacity: int = 50) -> Room:
    return Room(room_id, building, capacity)


def test_get_rooms_returns_empty_on_fresh_store(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    assert store.get_rooms() == []


def test_set_rooms_replaces_all(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_rooms([_make_room("101"), _make_room("102")])
    assert len(store.get_rooms()) == 2


def test_set_rooms_overwrites_previous(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_rooms([_make_room("101")])
    store.set_rooms([_make_room("201"), _make_room("202")])

    ids = {r.room_id for r in store.get_rooms()}
    assert ids == {"201", "202"}


def test_get_rooms_returns_copy(tmp_path):
    """Mutating the returned list must not affect internal state."""
    store = DataStore(tmp_path / "ds.pkl")
    store.set_rooms([_make_room("101")])

    result = store.get_rooms()
    result.clear()

    assert len(store.get_rooms()) == 1


def test_rooms_saved_and_loaded(tmp_path):
    path = tmp_path / "ds.pkl"
    store = DataStore(path)
    store.set_rooms([_make_room("101", "1", 50), _make_room("201", "2", 80)])
    store.save()

    store2 = DataStore(path)
    store2.load()
    rooms = store2.get_rooms()

    assert len(rooms) == 2
    assert {r.room_id for r in rooms} == {"101", "201"}


def test_load_backward_compat_no_rooms_key(tmp_path):
    """A saved file without a 'rooms' key must load successfully with an empty list."""
    import pickle
    path = tmp_path / "ds.pkl"
    # Write old-style data without 'rooms' key.
    with open(path, "wb") as f:
        pickle.dump({"courses": [], "periods": [], "program_names": {}}, f)

    store = DataStore(path)
    result = store.load()

    assert result is True
    assert store.get_rooms() == []


def test_clear_wipes_rooms(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_rooms([_make_room("101")])
    store.clear()

    assert store.get_rooms() == []


def test_merge_rooms_adds_new_rooms(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_rooms([_make_room("101", "1")])
    store.merge_rooms([_make_room("102", "1")])

    ids = {r.room_id for r in store.get_rooms()}
    assert ids == {"101", "102"}


def test_merge_rooms_skips_duplicate_building_room_id(tmp_path):
    store = DataStore(tmp_path / "ds.pkl")
    store.set_rooms([_make_room("101", "1", 50)])
    store.merge_rooms([_make_room("101", "1", 99)])  # same key, different capacity

    assert len(store.get_rooms()) == 1
    # Original must be preserved, not replaced.
    assert store.get_rooms()[0].capacity == 50


def test_merge_rooms_allows_same_id_in_different_buildings(tmp_path):
    """room_id '101' in building '1' and '2' are distinct physical rooms."""
    store = DataStore(tmp_path / "ds.pkl")
    store.set_rooms([_make_room("101", "1")])
    store.merge_rooms([_make_room("101", "2")])

    assert len(store.get_rooms()) == 2
