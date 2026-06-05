from src.models.course import Course
from src.models.program_requirement import ProgramRequirement
from src.algorithm.constraint_index import ConstraintIndex
from src.algorithm.basic_version_validator import BasicVersionValidator
from src.algorithm.constraint_validator import ConstraintValidator
from src.models.enums import Evaluation, Semester, ReqType


def test_course_with_multiple_obligatory_requirements_collides_with_each_program():
    # Course that belongs obligatorily to two programs
    multi = Course("Multi", "90001", "Dr", Evaluation.Exam)
    multi.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))
    multi.add_requirement(ProgramRequirement("83102", 1, Semester.FALL, ReqType.Obligatory))

    c1 = Course("C1", "90002", "Dr", Evaluation.Exam)
    c1.add_requirement(ProgramRequirement("83101", 1, Semester.FALL, ReqType.Obligatory))

    c2 = Course("C2", "90003", "Dr", Evaluation.Exam)
    c2.add_requirement(ProgramRequirement("83102", 1, Semester.FALL, ReqType.Obligatory))

    courses = [multi, c1, c2]
    index = ConstraintIndex()
    index.build(courses, ["83101", "83102"])  # both programs selected

    collision_validator = BasicVersionValidator(index)
    validator = ConstraintValidator(index, collision_validator)

    # multi should collide with c1 (shares 83101) and with c2 (shares 83102)
    assert validator.collides(multi, c1) is True
    assert validator.collides(multi, c2) is True
