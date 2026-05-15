from parsers.file_parser import IFileParser
from models.course import Course
from models.program_requirement import ProgramRequirement

# Parser class for loading courses
class CourseFileParser(IFileParser):
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
                
            # extract course metadata
            name = lines[0]
            course_id = lines[1]
            instructor = lines[2]
            evaluation = lines[-1]

            course = Course(name, course_id, instructor, evaluation)
            
            # extract program requirements
            for i in range(3, len(lines) - 1):
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
                    semester, 
                    req_type
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
        if course.evaluation != "Exam":
            continue

        # Step 2: Check if course belongs to any selected program via its requirements
        belongs_to_selected = any(
            req.program_id in selected_programs_set for req in course.requirements
        )

        if not belongs_to_selected:
            continue

        valid_courses.append(course)

    return valid_courses