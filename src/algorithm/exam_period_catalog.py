from src.models.exam_period import ExamPeriod
from src.models.course import Course
from src.models.enums import Semester, Moed

class ExamPeriodCatalog:
    """
    Wraps the list of ExamPeriod objects and provides lookup utilities
    by semester/moed or by course context.
    """

    def __init__(self, periods: list[ExamPeriod]):
        self._periods: list[ExamPeriod] = periods

    def get(self, semester: Semester, moed: Moed) -> ExamPeriod | None:
        for period in self._periods:
            if period.semester == semester and period.moed == moed:
                return period
        return None

    def all(self) -> list[ExamPeriod]:
        return self._periods

    def periodFor(self, course: Course, moed: Moed) -> ExamPeriod | None:
        for req in course.requirements:
            period = self.get(req.semester, moed)
            if period is not None:
                return period
        return None
