from models.program_requirement import ProgramRequirement

class Course:
    def __init__(self, name: str, course_id: str, instructor: str, evaluation: str):
        # course name
        self.name = name
        # course ID
        self.course_id = course_id
        # course instructor/proffesor
        self.instructor = instructor
        # course exam type - exam or paper work
        self.evaluation = evaluation
        # List to multiple program req
        self.requirements = []

    def add_requirement(self, req: ProgramRequirement):
        # add a program requirement to a course
        self.requirements.append(req)

    def belongsToProgram(self, program_id: str) -> bool:
        # Check if the course belongs to a specific program ID by searching requirements
        for req in self.requirements:
            if req.program_id == program_id:
                return True
        return False