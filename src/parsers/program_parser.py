from parsers.file_parser import IFileParser

# Parser class for loading selected programs
class ProgramSelectionParser(IFileParser):
    def parse(self, filepath: str) -> list[str]:
        # Read simple comma-separated file of selected program ID
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # split by comma and strip whitespace from each program ID
        programs = [prog.strip() for prog in content.split(',') if prog.strip()]

        # User only allowed up to 5 program ID
        if len(programs) > 5:
            raise ValueError("Programs file cannot contain more than 5 programs")

        return programs