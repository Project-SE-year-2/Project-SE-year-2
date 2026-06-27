import os
from src.parsers.course_parser import CourseFileParser, filter_courses_for_scheduling
from src.parsers.exam_period_file_parser import ExamPeriodFileParser
from src.parsers.program_parser import ProgramSelectionParser
from src.algorithm.scheduling_algoritem import match_courses_to_periods
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.exam_period_catalog import ExamPeriodCatalog
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.algorithm.scheduling_engine import SchedulingEngine
from src.output.schedule_report_writer import ScheduleReportWriter
from src.output.output_manager import OutputManager
from src.algorithm.constraints.constraint_checker import ConstraintChecker


class AppController:
    def __init__(self):
        self.course_parser = CourseFileParser()
        self.period_parser = ExamPeriodFileParser()
        self.program_parser = ProgramSelectionParser()
        self.output_manager = OutputManager([ScheduleReportWriter()])

    def _validate_paths(self, paths: list):
        for path in paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Error: Could not find file at {path}!")
            if os.path.getsize(path) == 0:
                raise ValueError(f"Error: The file at {path} is empty!")

    def run(self, courses_path: str, periods_path: str, programs_path: str, constraint_settings=None, rooms=None, ranking_config=None):
        self._validate_paths([courses_path, periods_path, programs_path])

        courses = self.course_parser.parse(courses_path)
        periods = self.period_parser.parse(periods_path)
        programs = self.program_parser.parse(programs_path)

        valid_courses = filter_courses_for_scheduling(courses, programs)

        valid_program_ids = {
            req.program_id
            for course in courses
            for req in course.requirements
        }

        for program_id in programs:
            if program_id not in valid_program_ids:
                raise ValueError(f"Program ID does not exist: '{program_id}'")

        # Problem Partition
        scheduling_tasks = match_courses_to_periods(valid_courses, periods)

        # Build constraint index and period catalog
        index = ConstraintIndex()
        index.build(valid_courses, programs)

        catalog = ExamPeriodCatalog(periods)

        collision_validator = BasicVersionValidator(index)
        constraint_validator = ConstraintValidator(index, collision_validator)

        self.engine = SchedulingEngine(constraint_validator, catalog, index, constraint_settings, rooms)

        # Fetch per-period results
        period_results_by_period = {}
        for period_result in self.engine.iterPeriodResults(scheduling_tasks):
            period_results_by_period[period_result.period] = period_result

        all_sub_results = []
        metadata = {}

        checker = None
        if constraint_settings is not None:
            checker = ConstraintChecker(constraint_settings)

        scorer = None
        ascending_cols = {"elective_conflicts", "max_exams_per_day", "avg_room_distance"}
        if ranking_config:
            from src.algorithm.scoring.schedule_scorer import ScheduleScorer
            scorer = ScheduleScorer.default()

        for period in scheduling_tasks.keys():
            period_result = period_results_by_period[period]
            valid_schedules = period_result.schedules
            
            if checker is not None:
                valid_schedules = [s for s in valid_schedules if checker.is_valid(s)]
                
            if scorer is not None and ranking_config:
                metrics_dict = {s: scorer.compute_scores(s) for s in valid_schedules}
                def sort_fn(sched):
                    m = metrics_dict[sched]
                    keys = []
                    for col in ranking_config:
                        val = getattr(m, col)
                        if col in ascending_cols:
                            keys.append(val)
                        else:
                            keys.append(-val)
                    keys.append(sched.sort_key)
                    return tuple(keys)
                valid_schedules.sort(key=sort_fn)
                
            all_sub_results.append(valid_schedules)
            metadata[period] = period_result.metadata

        from src.algorithm.schedule_combiner import ScheduleCombiner
        combined = ScheduleCombiner().combineSubResults(all_sub_results)
        
        # If ranking is enabled, keep the cartesian product order so the best combinations appear first.
        # Otherwise, use chronological sort.
        if not ranking_config:
            combined.sort(key=lambda s: s.sort_key)
            
        schedules = combined

        project_root = os.path.normpath(os.path.join(os.path.dirname(courses_path), ".."))
        output_dir = os.path.join(project_root, "output")
        self.output_manager.prepareOutputDir(output_dir)
        self.output_manager.writeReport(schedules, metadata, programs, output_dir)
