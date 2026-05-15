import re
from datetime import datetime, date, timedelta
from src.parsers.file_parser import IFileParser
from src.models.exam_period import ExamPeriod

# Parser class for loading exam periods and forbidden dates
class ExamPeriodFileParser(IFileParser):
    def __init__(self):
        # Store the regex pattern as a class attribute
        self.date_pattern = r'\d{2}-\d{2}-\d{4}'

    # Helper function to extract forbidden dates from the exam period record lines
    def _parse_forbidden_dates(self, record_lines: list[str], period_start: date, period_end: date) -> set:
        forbidden_dates = set()
        for line in record_lines[2:]:
            found = re.findall(self.date_pattern, line)
            if not found:
                continue

            # Treat any two-date line as an inclusive range
            if len(found) == 2:
                start_date = datetime.strptime(found[0], "%d-%m-%Y").date()
                end_date = datetime.strptime(found[1], "%d-%m-%Y").date()
                current = max(start_date, period_start)
                range_end = min(end_date, period_end)
                while current <= range_end:
                    forbidden_dates.add(current)
                    current += timedelta(days=1)
                continue

            # otherwise treat each found date as a discrete forbidden date
            for ds in found:
                d = datetime.strptime(ds, "%d-%m-%Y").date()
                if period_start <= d <= period_end:
                    forbidden_dates.add(d)

        return forbidden_dates

    # Helper function to yield dates one by one
    def _generate_date_range(self, start_date: date, end_date: date):
        current = start_date
        while current <= end_date:
            yield current
            current += timedelta(days=1)

    # Parses the exam periods file and handles excluded dates and date ranges
    def parse(self, filepath: str) -> list[ExamPeriod]:
        periods = []

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        raw_records = content.split('$$$$')

        for record in raw_records:
            lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
            if not lines:
                continue
                
            # extract Semester and Moed
            sem_moed = lines[0].split(',')
            semester = sem_moed[0].strip()
            moed = sem_moed[1].strip()

            # extract start and end dates of the exam period
            start_end = lines[1].split(',')
            period = ExamPeriod(semester, moed, start_end[0].strip(), start_end[1].strip())
            
            # Use self. to call class helper methods
            forbidden_dates = self._parse_forbidden_dates(lines, period.start_date, period.end_date)
            period.possible_dates = [
                current_date
                for current_date in self._generate_date_range(period.start_date, period.end_date)
                if current_date not in forbidden_dates
            ]
            periods.append(period)

        return periods