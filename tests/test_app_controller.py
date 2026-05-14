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