import pytest
from src.app_controller import AppController

def test_validate_paths_raises_error_if_file_missing():
    controller = AppController()
    
    # We pass a path that clearly does not exist
    with pytest.raises(FileNotFoundError):
        controller._validate_paths(["C:/fake_path/that/does_not_exist.txt"])

def test_validate_paths_raises_error_if_file_is_empty(tmp_path):
    controller = AppController()
    
    # tmp_path is a built-in pytest fixture that creates a temporary directory
    empty_file = tmp_path / "empty_test.txt"
    empty_file.touch() # This creates the file, but leaves it at 0 bytes (empty)

    with pytest.raises(ValueError, match="is empty"):
        controller._validate_paths([str(empty_file)])

# Tests that the system raises a clear error message
# when the user selects a program ID that does not exist
# in the parsed courses data.
def test_app_controller_rejects_nonexistent_program_id(tmp_path):

    courses_content = """
$$$$
Physics 1
83102
Prof. A
83101,1,FALL,Obligatory
Exam
"""

    periods_content = """
$$$$
FALL,Aleph
01-02-2026,10-02-2026
"""

    programs_content = "99999"

    courses_file = tmp_path / "courses.txt"
    periods_file = tmp_path / "dates.txt"
    programs_file = tmp_path / "programs.txt"

    courses_file.write_text(courses_content.strip(), encoding="utf-8")
    periods_file.write_text(periods_content.strip(), encoding="utf-8")
    programs_file.write_text(programs_content, encoding="utf-8")

    controller = AppController()

    with pytest.raises(
            ValueError,
            match="Program ID does not exist: '99999'"
    ):
        controller.run(
            str(courses_file),
            str(periods_file),
            str(programs_file)
        )