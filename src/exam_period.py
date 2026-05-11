from datetime import datetime, timedelta
#this class serves as a data container for the period's boundaries.
class ExamPeriod:   
    def __init__(self, semester: str, moed: str, start_date: str, end_date: str):
        # Initialize the basic identifying information for the period
        self.semester = semester.strip()
        self.moed = moed.strip()
        
        # Convert the date strings into Python date objects
        # This conversion allows other modules to perform date-based logic and comparisons
        self.start_date = datetime.strptime(start_date.strip(), "%d-%m-%Y").date()
        self.end_date = datetime.strptime(end_date.strip(), "%d-%m-%Y").date()
        self.possible_dates = []

    
    # Generates a complete list of every single date within this exam period
    # to return a duplicate of the possible_dates
        if self.possible_dates:
            return self.possible_dates

        all_dates = []
        current = self.start_date

        # Iterate through the entire range from start_date to end_date.
        while current <= self.end_date:
            all_dates.append(current)
            current += timedelta(days=1)

        return all_dates