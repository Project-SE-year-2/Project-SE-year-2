import os
from src.course_parser import CourseFileParser, filter_courses_for_scheduling
from src.exam_period_file_parser import ExamPeriodFileParser
from src.program_parser import ProgramSelectionParser
from src.scheduling_algoritem import match_courses_to_periods
from src.constraint_index import ConstraintIndex
from src.exam_period_catalog import ExamPeriodCatalog
from src.basic_version_validator import BasicVersionValidator
from src.constraint_validator import ConstraintValidator
from src.scheduling_engine import SchedulingEngine
from src.schedule_report_writer import ScheduleReportWriter


class AppController:
    def __init__(self):
        self.course_parser = CourseFileParser()
        self.period_parser = ExamPeriodFileParser()
        self.program_parser = ProgramSelectionParser()
        self.writer = ScheduleReportWriter()

    def _validate_paths(self, paths: list):
        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Error: Could not find file at {path}!")
            if os.path.getsize(path) == 0:
                raise ValueError(f"Error: The file at {path} is empty!")

    def run(self, courses_path: str, periods_path: str, programs_path: str):
        self._validate_paths([courses_path, periods_path, programs_path])

        courses = self.course_parser.parse(courses_path)
        periods = self.period_parser.parse(periods_path)
        programs = self.program_parser.parse(programs_path)

        valid_courses = filter_courses_for_scheduling(courses, programs)

        # Problem Partition — already implemented
        scheduling_tasks = match_courses_to_periods(valid_courses, periods)

        # Build constraint index and period catalog
        index = ConstraintIndex()
        index.build(valid_courses, programs)

        catalog = ExamPeriodCatalog(periods)

        collision_validator = BasicVersionValidator(index)
        constraint_validator = ConstraintValidator(index, collision_validator)

        self.engine = SchedulingEngine(constraint_validator, catalog, index)

        schedules, metadata = self.engine.generateAll(scheduling_tasks)

        output_path = os.path.join(os.path.dirname(courses_path), "..", "schedule_output.txt")
        output_path = os.path.normpath(output_path)
        self.writer.write(schedules, metadata, programs, output_path=output_path)
        print(f"\nOutput saved to: {output_path}")