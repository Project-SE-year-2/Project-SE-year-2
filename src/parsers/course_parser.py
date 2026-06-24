from src.parsers.file_parser import IFileParser
from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation, Semester, ReqType

# Parser class for loading courses
class CourseFileParser(IFileParser):
    @staticmethod
    def _extract_num_students_and_evaluation(
        self,
        lines: list[str],
    ) -> tuple[int, str, int]:
        """
        Extract optional num_students and evaluation from a course record.

        Old format:
            name
            course_id
            instructor
            requirements...
            evaluation

        New format:
            name
            course_id
            instructor
            num_students=120
            requirements...
            evaluation
        """
        num_students = 0
        first_requirement_index = 3

        optional_students_line = lines[3].strip()
        if optional_students_line.startswith("num_students="):
            raw_value = optional_students_line.split("=", 1)[1].strip()

            try:
                num_students = int(raw_value)
            except ValueError:
                raise ValueError(
                    f"Invalid num_students value: '{raw_value}'. "
                    "Expected a non-negative integer."
                )

            first_requirement_index = 4

        evaluation = lines[-1]
        return num_students, evaluation, first_requirement_index


    def parse(self, filepath: str) -> list[Course]:
        courses = []
        
        # read the file with UTF-8 encoding
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split the content into records by $$$$ 
        raw_records = content.split('$$$$')

        for record in raw_records:
            # remove empty lines
            lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
            
            if not lines:
                continue

            if len(lines) < 5:
                raise ValueError("Invalid course record format")

            name = lines[0]
            course_id = lines[1]
            instructor = lines[2]
            evaluation = lines[-1]

            if "," in name:
                raise ValueError("Missing course name")

            if "," in course_id:
                raise ValueError("Missing course ID")

            if "," in instructor:
                     raise ValueError("Missing instructor name")

            if evaluation not in ["Exam", "Project", "Attendance"]:
                raise ValueError("Missing or invalid evaluation type")
            
            # extract course metadata
            name = lines[0]
            course_id = lines[1]
            instructor = lines[2]
            num_students, evaluation, first_req_index = (
                self._extract_num_students_and_evaluation(lines)
            )

            course = Course(name=name, course_id=course_id, instructor=instructor, evaluation=Evaluation(evaluation), num_students=num_students)
            
            # extract program requirements
            for i in range(first_req_index, len(lines) - 1):
                prog_data = lines[i].split(',')
                
                # raises an error if a program requirement line is missing fields
                if len(prog_data) != 4:
                    raise ValueError(
                        f"Invalid requirement format in course {course_id}: {lines[i]}"
                    )
                prog_id = prog_data[0].strip()
                year = int(prog_data[1].strip())
                semester = prog_data[2].strip()
                req_type = prog_data[3].strip()

                requirement = ProgramRequirement(
                    prog_id, 
                    year, 
                    Semester(semester), 
                    ReqType(req_type)
                )
                course.add_requirement(requirement)
            courses.append(course)

        return courses

def filter_courses_for_scheduling(courses: list[Course], selected_programs: list[str]) -> list[Course]:
    """
    Filter courses to extract only those relevant for exam scheduling.

    Criteria:
    1. Evaluation Method: Course evaluation must be strictly "Exam".
    2. Program Membership: Course must belong to at least one of the selected programs.

    Args:
        courses: List of all parsed courses.
        selected_programs: List of program IDs selected by the user.

    Returns:
        Filtered list of valid courses ready for scheduling.

    Raises:
        ValueError: If selected_programs is empty.
    """
    if not selected_programs:
        raise ValueError("At least one program must be selected for filtering")

    selected_programs_set = set(selected_programs)
    valid_courses = []

    for course in courses:
        # Step 1: Only keep courses with "Exam" evaluation type
        if course.evaluation != Evaluation.Exam:
            continue

        # Step 2: Check if course belongs to any selected program via its requirements
        belongs_to_selected = any(
            req.program_id in selected_programs_set for req in course.requirements
        )

        if not belongs_to_selected:
            continue

        valid_courses.append(course)

    return valid_courses