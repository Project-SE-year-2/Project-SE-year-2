from abc import ABC, abstractmethod

# Define the base interface for all file parsers according to the UML
class IFileParser(ABC):
    @abstractmethod
    def parse(self, filepath: str):
        pass