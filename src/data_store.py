class DataStore:
    def __init__(self):
        self._path = ""
        self._programs = []
        self._courses = []
        self._periods = []

    def load(self, courses: list, programs: list, periods: list):
        """Populates the datastore with parsed data"""
        self._courses = courses
        self._programs = programs
        self._periods = periods

    def save(self):
        """Placeholder for saving data state"""
        pass

    def clear(self):
        """Clears all data from memory"""
        self._programs = []
        self._courses = []
        self._periods = []

    def get_programs(self) -> list:
        return self._programs

    def get_courses(self, program_id: str) -> list:
        """Returns all courses related to a specific program ID"""
        return [
            course for course in self._courses 
            if any(str(req.program_id) == str(program_id) for req in course.requirements)
        ]

    def get_periods(self) -> list:
        return self._periods