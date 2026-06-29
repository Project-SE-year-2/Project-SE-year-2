"""
EP-142 - End-To-End Validation.

Drives the COMPLETE scheduling pipeline from raw input files all the way to a
written report, in BOTH scheduling modes, and verifies the properties the
acceptance criteria call out:

  1. Date-only mode passes all integration tests.
  2. Room scheduling mode passes all integration tests.
  3. Ranking data is persisted correctly (survives a close / reopen).
  4. Export output is valid.
  5. No room conflicts exist in generated schedules.

Unlike the per-component unit tests, every scenario here parses real course /
period / room files with the production parsers, wires the real
SchedulingEngine exactly the way AppController / AppService do, and asserts on
the actual ExamPlacement objects and the written report file.

The scenarios are deliberately small so the full suite stays fast.
"""

from datetime import date

import pytest

from src.app_controller import AppController
from src.parsers.course_parser import CourseFileParser, filter_courses_for_scheduling
from src.parsers.exam_period_file_parser import ExamPeriodFileParser
from src.parsers.room_file_parser import RoomFileParser
from src.algorithm.scheduling_algoritem import match_courses_to_periods
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_engine import SchedulingEngine
from src.algorithm.scoring.schedule_scorer import ScheduleScorer
from src.presenter.scores_database import ScoresDatabase
from src.presenter.ranking_query_engine import RankingQueryEngine
from src.output.schedule_report_writer import ScheduleReportWriter
from src.models.constraint_settings import ConstraintSettings


# --------------------------------------------------------------------------- #
# Sample input files (production parser formats)                              #
# --------------------------------------------------------------------------- #

# Three obligatory courses in one program. Because they share the program they
# all collide, so every feasible schedule must place them on three distinct days.
THREE_COURSES = """$$$$
Algorithms
90001
Dr A
num_students=40
83101,1,FALL,Obligatory
Exam
$$$$
Databases
90002
Dr B
num_students=30
83101,1,FALL,Obligatory
Exam
$$$$
Networks
90003
Dr C
num_students=25
83101,1,FALL,Obligatory
Exam
"""

# A single FALL / Aleph period. Three available days is just enough for the
# three colliding courses, which keeps the room-mode combination count modest.
THREE_DAY_PERIOD = """$$$$
FALL, Aleph
01-02-2026, 03-02-2026
"""

FIVE_DAY_PERIOD = """$$$$
FALL, Aleph
01-02-2026, 05-02-2026
"""

ROOMS = """101,1,50
102,1,50
201,2,60
"""

PROGRAMS = "83101\n"

# Two courses in DIFFERENT programs (no shared students, so they may share a
# date) with only one available day, forcing them onto the same date. With two
# rooms the allocator must hand them distinct rooms when the slot also matches.
TWO_PROGRAM_COURSES = """$$$$
CourseA
A1
Dr A
num_students=40
83101,1,FALL,Obligatory
Exam
$$$$
CourseB
B1
Dr B
num_students=35
83102,1,FALL,Obligatory
Exam
"""

ONE_DAY_PERIOD = """$$$$
FALL, Aleph
02-02-2026, 02-02-2026
"""

TWO_ROOMS = "101,1,50\n102,1,50\n"


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _make_scenario(tmp_path, courses_txt, dates_txt, rooms_txt=None,
                   programs_txt=PROGRAMS):
    """Write a project-like tmp/data/*.txt layout and return the paths."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    paths = {
        "courses": data_dir / "courses.txt",
        "dates": data_dir / "dates.txt",
        "programs": data_dir / "programs.txt",
    }
    paths["courses"].write_text(courses_txt, encoding="utf-8")
    paths["dates"].write_text(dates_txt, encoding="utf-8")
    paths["programs"].write_text(programs_txt, encoding="utf-8")
    if rooms_txt is not None:
        paths["rooms"] = data_dir / "rooms.txt"
        paths["rooms"].write_text(rooms_txt, encoding="utf-8")
    return paths


def _generate(paths, programs, settings=None, rooms=None):
    """Wire and run the engine exactly like AppController, returning schedules.

    Returns (schedules, metadata) from SchedulingEngine.generateAll for the
    given constraint settings and optional rooms list.
    """
    courses = CourseFileParser().parse(str(paths["courses"]))
    periods = ExamPeriodFileParser().parse(str(paths["dates"]))
    valid = filter_courses_for_scheduling(courses, programs)
    tasks = match_courses_to_periods(valid, periods)

    index = ConstraintIndex()
    index.build(valid, programs)
    catalog = ExamPeriodCatalog(periods)
    validator = ConstraintValidator(index, BasicVersionValidator(index))

    engine = SchedulingEngine(validator, catalog, index, settings, rooms)
    return engine.generateAll(tasks)


def _room_conflicts(schedule):
    """Return a list of (room-slot key -> course ids) that are double-booked.

    A conflict is the SAME physical room (building, room_id) used by two
    DIFFERENT courses at the SAME (date, time_slot). Reusing a room on a
    different date or in a different slot is legal and not reported.
    """
    used: dict[tuple, str] = {}
    conflicts: list[tuple] = []
    for course, placement in schedule.placements.items():
        if not placement.is_room_based:
            continue
        for room in placement.rooms:
            key = (placement.date, placement.time_slot, room.building, room.room_id)
            if key in used and used[key] != course.course_id:
                conflicts.append((key, used[key], course.course_id))
            used[key] = course.course_id
    return conflicts


# --------------------------------------------------------------------------- #
# 1. Date-only mode                                                            #
# --------------------------------------------------------------------------- #

def test_date_only_full_pipeline_writes_valid_report(tmp_path):
    """AC1 + AC4: the date-only CLI pipeline runs and writes a valid report."""
    paths = _make_scenario(tmp_path, THREE_COURSES, FIVE_DAY_PERIOD)

    AppController().run(str(paths["courses"]), str(paths["dates"]),
                        str(paths["programs"]))

    output_dir = tmp_path / "output"
    assert output_dir.exists()
    reports = [p for p in output_dir.iterdir()
               if p.name.startswith("schedule_output_")]
    assert reports, "no schedule report was written"

    content = reports[0].read_text(encoding="utf-8")
    assert "EXAM SCHEDULE GENERATOR - RESULTS" in content
    assert "TOTAL COMPLETE SCHEDULES" in content
    # Every course must appear in the report.
    for cid in ("90001", "90002", "90003"):
        assert f"({cid})" in content


def test_date_only_every_schedule_is_complete_and_collision_free(tmp_path):
    """AC1: each generated schedule places every course on a distinct day."""
    paths = _make_scenario(tmp_path, THREE_COURSES, FIVE_DAY_PERIOD)
    schedules, _ = _generate(paths, ["83101"], ConstraintSettings())

    assert schedules, "date-only generation produced no schedules"
    for sched in schedules:
        placements = sched.placements
        # All three courses scheduled.
        assert {c.course_id for c in placements} == {"90001", "90002", "90003"}
        # Colliding obligatory courses must be on three different dates.
        dates = [pl.date for pl in placements.values()]
        assert len(set(dates)) == 3
        # Pure date-only placements carry no room data.
        assert all(not pl.is_room_based for pl in placements.values())


# --------------------------------------------------------------------------- #
# 2 + 5. Room scheduling mode & room-conflict freedom                          #
# --------------------------------------------------------------------------- #

def test_room_mode_every_placement_has_rooms_within_capacity(tmp_path):
    """AC2: room mode assigns a slot and enough room capacity to every exam."""
    paths = _make_scenario(tmp_path, THREE_COURSES, THREE_DAY_PERIOD, ROOMS)
    settings = ConstraintSettings(room_scheduling_enabled=True)
    rooms = RoomFileParser().parse(str(paths["rooms"]))

    schedules, _ = _generate(paths, ["83101"], settings, rooms)
    assert schedules, "room-mode generation produced no schedules"

    students = {"90001": 40, "90002": 30, "90003": 25}
    for sched in schedules:
        for course, placement in sched.placements.items():
            assert placement.is_room_based
            assert placement.time_slot is not None
            assert placement.rooms
            assert placement.total_capacity >= students[course.course_id]


def test_room_mode_has_no_room_conflicts_in_any_schedule(tmp_path):
    """AC5: no physical room is double-booked at the same date+slot, ever."""
    paths = _make_scenario(tmp_path, THREE_COURSES, THREE_DAY_PERIOD, ROOMS)
    settings = ConstraintSettings(room_scheduling_enabled=True)
    rooms = RoomFileParser().parse(str(paths["rooms"]))

    schedules, _ = _generate(paths, ["83101"], settings, rooms)
    assert schedules

    for sched in schedules:
        assert _room_conflicts(sched) == []


def test_room_allocator_resolves_forced_same_day_collision(tmp_path):
    """AC5 (tight): two courses forced onto one day still get distinct rooms.

    Both courses share the only available day. Whenever the engine also places
    them in the same time slot, the allocator must give them different physical
    rooms - never a conflict - while still respecting each course's capacity.
    """
    paths = _make_scenario(tmp_path, TWO_PROGRAM_COURSES, ONE_DAY_PERIOD,
                           TWO_ROOMS, programs_txt="83101\n83102\n")
    settings = ConstraintSettings(room_scheduling_enabled=True)
    rooms = RoomFileParser().parse(str(paths["rooms"]))

    schedules, _ = _generate(paths, ["83101", "83102"], settings, rooms)
    assert schedules, "expected at least one feasible room schedule"

    saw_same_slot = False
    for sched in schedules:
        assert _room_conflicts(sched) == []
        placements = sched.placements
        assert {c.course_id for c in placements} == {"A1", "B1"}
        slots = [pl.time_slot for pl in placements.values()]
        if len(set(slots)) == 1:
            saw_same_slot = True
            # Same day + same slot => the two rooms must be physically distinct.
            room_ids = [
                (r.building, r.room_id)
                for pl in placements.values() for r in pl.rooms
            ]
            assert len(room_ids) == len(set(room_ids))

    assert saw_same_slot, (
        "scenario never exercised the same-slot case the allocator must resolve"
    )


# --------------------------------------------------------------------------- #
# 3. Ranking persistence                                                       #
# --------------------------------------------------------------------------- #

def test_ranking_data_persists_across_reopen(tmp_path):
    """AC3: scores written for generated schedules survive a DB close/reopen."""
    paths = _make_scenario(tmp_path, THREE_COURSES, FIVE_DAY_PERIOD)
    schedules, _ = _generate(paths, ["83101"], ConstraintSettings())
    assert len(schedules) >= 5

    scorer = ScheduleScorer.default()
    sample = schedules[:5]
    db_path = tmp_path / "results" / "scores.db"
    period = "FALL_Aleph"

    # Write scores through the same class the engine uses, then close the file.
    db = ScoresDatabase(db_path)
    for i, sched in enumerate(sample):
        db.insert(period, batch_number=0, index_in_batch=i,
                  metrics=scorer.compute_scores(sched))
    db.commit()
    db.close()

    assert db_path.exists(), "scores.db file was not created on disk"

    # Reopen with a completely fresh query engine - proves on-disk persistence.
    engine = RankingQueryEngine(db_path)
    try:
        assert engine.count(period) == len(sample)
        rows = engine.fetch_window(period, ["avg_days_all"], limit=len(sample),
                                   offset=0)
        assert len(rows) == len(sample)
        # best_score must match the value the ranked window puts first.
        top = engine.fetch_window(period, ["avg_days_all"], limit=1, offset=0)[0]
        assert engine.best_score(period, "avg_days_all") == top[3]
    finally:
        engine.close()

    # A second independent reopen returns the same count (true persistence).
    engine2 = RankingQueryEngine(db_path)
    try:
        assert engine2.count(period) == len(sample)
    finally:
        engine2.close()


# --------------------------------------------------------------------------- #
# 4. Export validity                                                           #
# --------------------------------------------------------------------------- #

def test_export_date_only_report_is_valid(tmp_path):
    """AC4: a date-only report contains the header, courses, and dates."""
    paths = _make_scenario(tmp_path, THREE_COURSES, FIVE_DAY_PERIOD)
    schedules, metadata = _generate(paths, ["83101"], ConstraintSettings())

    out = tmp_path / "report.txt"
    ScheduleReportWriter().write(schedules=[schedules[0]], metadata=metadata,
                                 programs=["83101"], output_path=str(out))

    content = out.read_text(encoding="utf-8")
    assert "EXAM SCHEDULE GENERATOR - RESULTS" in content
    assert "END OF REPORT" in content
    for cid in ("90001", "90002", "90003"):
        assert f"({cid})" in content
    # Dates are rendered in DD-MM-YYYY.
    assert "-02-2026" in content


def test_export_room_mode_report_includes_room_details(tmp_path):
    """AC4: a room-mode report carries time-slot, room, and capacity columns."""
    paths = _make_scenario(tmp_path, THREE_COURSES, THREE_DAY_PERIOD, ROOMS)
    settings = ConstraintSettings(room_scheduling_enabled=True)
    rooms = RoomFileParser().parse(str(paths["rooms"]))
    schedules, metadata = _generate(paths, ["83101"], settings, rooms)

    out = tmp_path / "room_report.txt"
    ScheduleReportWriter().write(schedules=[schedules[0]], metadata=metadata,
                                 programs=["83101"], output_path=str(out))

    content = out.read_text(encoding="utf-8")
    assert "Assigned Rooms" in content
    # At least one of the loaded rooms is referenced as building-room_id.
    assert ("1-101" in content) or ("1-102" in content) or ("2-201" in content)