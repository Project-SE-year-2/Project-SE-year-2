class ProgramRequirement:
    def __init__(self, program_id: str, year: int, semester: str, req_type: str, courses: list[str] = None):
        # program ID
        self.program_id = program_id
        # program year
        self.year = year
        # program semester
        self.semester = semester
        # program req type - Obligatory or Elective
        self.req_type = req_type
        # Initialize an empty list if no courses are provided
        self.courses = courses if courses is not None else []

    def is_obligatory(self) -> bool:
        # Returns True if the requirement type is Obligatory
        return self.req_type == "Obligatory"

    def add_course(self, course: str) -> None:
        # Adds a new course to the program's course list
        if course not in self.courses:
            self.courses.append(course)