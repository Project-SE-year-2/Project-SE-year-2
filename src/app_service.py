from typing import List, Dict

from src.IAppService import IAppService
from src.data_store import DataStore

class app_service(IAppService):
    """
    Singleton Presenter that implements IAppService.
    Acts as the middleman between the UI, the DataStore, and the AppController.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Enforce the Singleton pattern so only one instance exists
        if not cls._instance:
            cls._instance = super(app_service, cls).__new__(cls, *args, **kwargs)
            cls._instance._init_singleton()
        return cls._instance

    @classmethod
    def getInstance(cls):
        # UML explicitly requires a getInstance method
        if not cls._instance:
            cls()
        return cls._instance
    
    def _init_singleton(self):
        # Initialize properties as defined in the class diagram
        self._selected_programs = []
        self._results = []

    def get_available_programs(self) -> List[Dict[str, str]]:
        # Retrieve programs derived from the loaded courses
        programs = self._datastore.get_programs()
        # Format as a dictionary for the UI
        # Note: Replace the hardcoded name if actual program names exist in the data
        return [{"id": str(p), "name": f"Program {p}"} for p in programs]

    def select_programs(self, ids: List[str]) -> None:
        # Validate that a maximum of 5 programs are selected
        if len(ids) > 5:
            raise ValueError("Maximum of 5 programs can be selected.")
            
        # Validate that each ID is exactly a 5-digit string
        for pid in ids:
            if not isinstance(pid, str) or len(pid) != 5 or not pid.isdigit():
                raise ValueError(f"Invalid program ID: '{pid}'. Must be a 5-digit string.")
                
        # Save the valid selection
        self._selected_programs = ids

    def get_courses(self, program_id: str) -> List[Dict[str, str]]:
        course_objects = self._datastore.get_courses(program_id)
        result = []
        
        for course in course_objects:
            # Find the specific ProgramRequirement for the requested program_id
            matching_req = next((req for req in course.requirements if str(req.program_id) == str(program_id)), None)
            
            if matching_req:
                result.append({
                    "number": str(course.course_id), 
                    "name": str(course.name),
                    "evaluation": str(course.evaluation.name if hasattr(course.evaluation, 'name') else course.evaluation),
                    "year": str(matching_req.year),
                    "semester": str(matching_req.semester.name if hasattr(matching_req.semester, 'name') else matching_req.semester),
                    "type": str(matching_req.req_type.name if hasattr(matching_req.req_type, 'name') else matching_req.req_type)
                })
                
        return result