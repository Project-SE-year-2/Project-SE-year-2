from abc import ABC, abstractmethod
from typing import List, Dict

class IAppService(ABC):
    
    # ... Other methods ...

    @abstractmethod
    def get_available_programs(self) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def select_programs(self, ids: List[str]) -> None:
        pass

    @abstractmethod
    def get_courses(self, program_id: str) -> List[Dict[str, str]]:
        pass