from enum import Enum

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

class CalendarMode(str, Enum):
    INPUT = "input"
    OUTPUT = "output"

class TimeSlot(Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"