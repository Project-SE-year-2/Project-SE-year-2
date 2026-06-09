import os

class ProgramsParser:
    """
    Parses the programs text file and extracts a mapping of program IDs to their display names.
    """
    
    @staticmethod
    def parse(filepath: str) -> dict[str, str]:
        """
        Reads the given file and returns a dictionary mapping program_id to program_name.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Programs file not found: {filepath}")

        program_names: dict[str, str] = {}
        
        with open(filepath, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                
                # Skip empty lines if there are any at the end of the file
                if not line:
                    continue
                
                # Split the line by the first whitespace only to separate ID from the full name
                parts = line.split(maxsplit=1)
                
                # Directly assign the ID and name since the file format is strictly defined
                if len(parts) == 2:
                    program_id = parts[0]
                    program_name = parts[1]
                    program_names[program_id] = program_name
                    
        return program_names