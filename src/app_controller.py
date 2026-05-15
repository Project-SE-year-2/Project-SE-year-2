import os
from src.course_parser import CourseFileParser, filter_courses_for_scheduling
from src.exam_period_file_parser import ExamPeriodFileParser
from src.program_parser import ProgramSelectionParser
from src.scheduling_algoritem import match_courses_to_periods

class AppController:
    def __init__(self):
        # Initialize all parser objects according to UML
        self.course_parser = CourseFileParser()
        self.period_parser = ExamPeriodFileParser()
        self.program_parser = ProgramSelectionParser()
        # Future modules like self.engine and self.writer will be added here

    def _validate_paths(self, paths: list):
        # Check if all provided files exist and are not empty
        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Error: Could not find file at {path}!")
            if os.path.getsize(path) == 0:
                raise ValueError(f"Error: The file at {path} is empty!")

    def run(self, courses_path: str, periods_path: str, programs_path: str):
        #Validate input files
        self._validate_paths([courses_path, periods_path, programs_path])

        #Parse all files using the parser objects
        courses = self.course_parser.parse(courses_path)

        periods = self.period_parser.parse(periods_path)

        programs = self.program_parser.parse(programs_path)
        #Filter courses based on requirements
        valid_courses = filter_courses_for_scheduling(courses, programs)

        # Generate tasks mapping: ExamPeriod -> { Course -> [Program IDs] }
        scheduling_tasks = match_courses_to_periods(valid_courses, periods)

        # Returns the mapped tasks for the scheduling algorithm
        return scheduling_tasks

        # In the next step, we will pass valid_courses and periods to the SchedulingEngine
        return valid_courses, periods