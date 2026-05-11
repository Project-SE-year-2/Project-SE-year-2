import pytest

from src.file_parser import parse_programs_file

# A test to check that the system can read the programs with spaces between them
def test_parse_programs_file_ignores_spaces(tmp_path):
    content = "83101, 83102, 83108"

    file_path = tmp_path / "programs.txt"
    file_path.write_text(content, encoding="utf-8")

    programs = parse_programs_file(str(file_path))

    assert programs == ["83101", "83102", "83108"]

# A test that checks that the user can choose up to 5 program ID
def test_parse_programs_file_accepts_up_to_five_programs(tmp_path):
    content = "83101, 83102, 83104, 83107, 83108"

    file_path = tmp_path / "programs.txt"
    file_path.write_text(content, encoding="utf-8")

    programs = parse_programs_file(str(file_path))

    assert programs == ["83101", "83102", "83104", "83107", "83108"]

# A test to ensure that a user cannot choose more than 5 program ID
def test_parse_programs_file_rejects_more_than_five_programs(tmp_path):
    content = "83101, 83102, 83104, 83107, 83108, 83109"

    file_path = tmp_path / "programs.txt"
    file_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        parse_programs_file(str(file_path))