import os
import pytest
from src.parsers.programs_name_parser import ProgramsParser

# =====================================================================
# Tests for ProgramsParser
# =====================================================================

def test_parse_valid_programs_file(tmp_path):
    """
    Test that the parser correctly extracts IDs and names from a clean formatted file.
    """
    file_content = """83101 Computer Engineering
                        83102 Electrical Engineering
                        83104 Industrial Engineering and Information Systems
                        83107 Data Engineering
                        83108 Software Engineering
                        83109 Materials Engineering
                        83105 Computer Engineering - Computer Hardware Track
                        83182 Electrical Engineering - Quantum Engineering Track
                        83103 Electrical Engineering - Neuroengineering Track
                        83115 Electrical Engineering - Biomedical Engineering Track"""
    
    test_file = tmp_path / "test_programs.txt"
    test_file.write_text(file_content, encoding='utf-8')

    # Execute parser
    result = ProgramsParser.parse(str(test_file))

    # Assertions match the English names provided in the mock file content
    assert len(result) == 10
    assert result["83101"] == "Computer Engineering"
    assert result["83108"] == "Software Engineering"
    assert result["83105"] == "Computer Engineering - Computer Hardware Track"
    assert result["83115"] == "Electrical Engineering - Biomedical Engineering Track"


def test_parse_hebrew_programs_file(tmp_path):
    """
    Test that the parser correctly extracts IDs and Hebrew names,
    ensuring that UTF-8 encoding works properly.
    """
    file_content = """83101 הנדסת מחשבים
                        83102 הנדסת חשמל
                        83104 הנדסת תעשיה ומערכות מידע"""
    
    test_file = tmp_path / "test_programs_hebrew.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert len(result) == 3
    assert result["83101"] == "הנדסת מחשבים"
    assert result["83102"] == "הנדסת חשמל"
    assert result["83104"] == "הנדסת תעשיה ומערכות מידע"


def test_parse_empty_file(tmp_path):
    """
    Test that an empty file returns an empty dictionary without crashing.
    """
    test_file = tmp_path / "empty.txt"
    test_file.write_text("", encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert isinstance(result, dict)
    assert len(result) == 0


def test_parse_handles_extra_whitespaces(tmp_path):
    """
    Test that the parser handles extra spaces between the ID and the name correctly.
    """
    file_content = "12345    Program With Extra Spaces   \n"
    test_file = tmp_path / "spaces.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert len(result) == 1
    assert result["12345"] == "Program With Extra Spaces"


def test_parse_raises_file_not_found_error():
    """
    Test that a non-existent file path raises a FileNotFoundError.
    """
    invalid_path = "this_file_does_not_exist.txt"
    
    with pytest.raises(FileNotFoundError) as excinfo:
        ProgramsParser.parse(invalid_path)
        
    assert "Programs file not found" in str(excinfo.value)


def test_parse_skips_invalid_lines(tmp_path):
    """
    Test that lines missing a program name (e.g., only containing an ID)
    are safely skipped by the parser without causing a crash.
    """
    file_content = "83101 Valid Program\n83102\n83103 Another Valid Program"
    test_file = tmp_path / "invalid_lines.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert len(result) == 2
    assert result["83101"] == "Valid Program"
    assert result["83103"] == "Another Valid Program"
    assert "83102" not in result


# =====================================================================
# New Edge-Case Tests
# =====================================================================

def test_parse_mixed_hebrew_and_english(tmp_path):
    """
    Test that the parser can handle program names containing both English and Hebrew.
    """
    file_content = "83101 Software Engineering הנדסת תוכנה\n83102 הנדסת חשמל (Track A)"
    test_file = tmp_path / "mixed_lang.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert len(result) == 2
    assert result["83101"] == "Software Engineering הנדסת תוכנה"
    assert result["83102"] == "הנדסת חשמל (Track A)"


def test_parse_special_characters_and_numbers(tmp_path):
    """
    Test that the parser correctly includes numbers and special characters in the name.
    """
    file_content = "99999 AI & Data Science (Track 2.0) - New!"
    test_file = tmp_path / "special_chars.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert len(result) == 1
    assert result["99999"] == "AI & Data Science (Track 2.0) - New!"


def test_parse_handles_tabs_instead_of_spaces(tmp_path):
    """
    Test that tabs separating the ID and the name are parsed correctly.
    """
    file_content = "83101\tComputer Engineering\n83102\t\tElectrical Engineering"
    test_file = tmp_path / "tabs.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert len(result) == 2
    assert result["83101"] == "Computer Engineering"
    assert result["83102"] == "Electrical Engineering"


def test_parse_duplicate_ids_overwrites_with_latest(tmp_path):
    """
    Test that if a file contains duplicate IDs, the parser retains the last occurrence.
    """
    file_content = "83101 Old Program Name\n83101 New Program Name"
    test_file = tmp_path / "duplicates.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert len(result) == 1
    assert result["83101"] == "New Program Name"


def test_parse_whitespace_only_file(tmp_path):
    """
    Test that a file containing only spaces and newlines is treated as empty.
    """
    file_content = "   \n  \t  \n\n   "
    test_file = tmp_path / "whitespace_only.txt"
    test_file.write_text(file_content, encoding='utf-8')

    result = ProgramsParser.parse(str(test_file))

    assert isinstance(result, dict)
    assert len(result) == 0