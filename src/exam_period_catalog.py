from src.exam_period import ExamPeriod
from src.course import Course


class ExamPeriodCatalog:
    """
    Wraps the list of ExamPeriod objects and provides lookup utilities
    by semester/moed or by course context.
    """

    def __init__(self, periods: list[ExamPeriod]):
        self._periods: list[ExamPeriod] = periods

    def get(self, semester: str, moed: str) -> ExamPeriod | None:
        for period in self._periods:
            if period.semester.strip() == semester.strip() and period.moed.strip() == moed.strip():
                return period
        return None

    def all(self) -> list[ExamPeriod]:
        return self._periods

    def periodFor(self, course: Course, moed: str) -> ExamPeriod | None:
        for req in course.requirements:
            period = self.get(req.semester.strip(), moed)
            if period is not None:
                return period
        return None
