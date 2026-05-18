from datetime import date, datetime, timedelta
from src.models.enums import Semester, Moed

#this class serves as a data container for the period's boundaries.
class ExamPeriod:   
    def __init__(self, semester: Semester, moed: Moed, start_date: str | date, end_date: str | date):
        # Initialize the basic identifying information for the period
        self.semester = semester
        self.moed = moed
        
        # Check if start_date is already a date object, if not, parse it from string
        if isinstance(start_date, str):
            self.start_date = datetime.strptime(start_date.strip(), "%d-%m-%Y").date()
        else:
            self.start_date = start_date

        # Check if end_date is already a date object, if not, parse it from string
        if isinstance(end_date, str):
            self.end_date = datetime.strptime(end_date.strip(), "%d-%m-%Y").date()
        else:
            self.end_date = end_date
            
        self.possible_dates = []

    # Generates a complete list of every single date within this exam period
    # to return a duplicate of the possible_dates
    def getAvailableDates(self) -> list:
        if self.possible_dates:
            return self.possible_dates

        all_dates = []
        current = self.start_date

        # Iterate through the entire range from start_date to end_date.
        while current <= self.end_date:
            all_dates.append(current)
            current += timedelta(days=1)

        return all_dates