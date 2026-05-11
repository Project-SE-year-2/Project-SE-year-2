class ProgramRequirement:
    def __init__(self, program_id: str, year: int, semester: str, req_type: str):
        #program ID
        self.program_id = program_id
        #program year
        self.year = year
        #program semster
        self.semester = semester
        #program req type - Obligatory or Elective
        self.req_type = req_type

class Course:
    def __init__(self, name: str, course_id: str, instructor: str, evaluation: str):
        #course name
        self.name = name
        #course ID
        self.course_id = course_id
        #course instructor/proffesor
        self.instructor = instructor
        #course exam type - exam or paper work
        self.evaluation = evaluation
        # List to multiple program requirements for the course
        self.requirements = []

    def add_requirement(self, req: ProgramRequirement):
        # add a program requirement to a course
        self.requirements.append(req)