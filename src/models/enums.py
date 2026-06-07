from enum import Enum
from enum import StrEnum

class Semester(Enum):
    FALL = "FALL"
    SPRI = "SPRI"
    SUMM = "SUMM"

class Moed(Enum):
    Aleph = "Aleph"
    Bet = "Bet"
    Gimel = "Gimel"

class ReqType(Enum):
    Obligatory = "Obligatory"
    Elective = "Elective"

class Evaluation(Enum):
    Exam = "Exam"
    Project = "Project"
    Attendance = "Attendance"

class CalendarMode(StrEnum):
    INPUT = "input"
    OUTPUT = "output"