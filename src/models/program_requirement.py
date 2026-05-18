from src.models.enums import Semester, ReqType

class ProgramRequirement:
    """
    This class acts as a data container that defines a specific 'context' for a course.

    - A 'Course' represents the general subject (e.g., 'Calculus').
    - A 'ProgramRequirement' represents WHO needs to take it and WHEN.
    - Since one course can be required by multiple programs, 
      each Course object holds a list of these ProgramRequirement objects.
    """
    def __init__(self, program_id: str, year: int, semester: Semester, req_type: ReqType, courses: list[str] = None):
        # program ID
        self.program_id = program_id
        
        self.year = year
        self.semester = semester
        # program req type - Obligatory or Elective
        self.req_type = req_type
        
        # Initialize an empty list if no courses are provided
        self.courses = courses if courses is not None else []

    def add_course(self, course: str) -> None:
        # Adds a new course to the program's course list
        if course not in self.courses:
            self.courses.append(course)

    def is_obligatory(self) -> bool:
        # Check against the Enum value instead of a string
        return self.req_type == ReqType.Obligatory