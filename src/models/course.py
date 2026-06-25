from src.models.program_requirement import ProgramRequirement
from src.models.enums import Evaluation

class Course:
    def __init__(
        self,
        name: str,
        course_id: str,
        instructor: str,
        evaluation: Evaluation,
        num_students: int = 0,
    ):
        self._validate_num_students(num_students)
        # course name
        self.name = name
        # course ID
        self.course_id = course_id
        # course instructor/proffesor
        self.instructor = instructor
        # course exam type - exam or paper work
        self.evaluation = evaluation
        # number of students enrolled in the course
        self.num_students = num_students
        # List to multiple program req
        self.requirements = []

    @staticmethod
    def _validate_num_students(num_students: int) -> None:
        """Validate that student count is a non-negative integer."""
        if not isinstance(num_students, int) or isinstance(num_students, bool):
            raise ValueError("num_students must be an integer.")

        if num_students < 0:
            raise ValueError("num_students must be non-negative.")

    def __setstate__(self, state: dict) -> None:
        """Restore old pickled Course objects that do not contain num_students."""
        self.__dict__.update(state)

        if "num_students" not in self.__dict__:
            self.num_students = 0
        else:
            self._validate_num_students(self.num_students)

    def add_requirement(self, req: ProgramRequirement):
        # add a program requirement to a course
        self.requirements.append(req)

    def belongsToProgram(self, program_id: str) -> bool:
        # Check if the course belongs to a specific program ID by searching requirements
        for req in self.requirements:
            if req.program_id == program_id:
                return True
        return False
