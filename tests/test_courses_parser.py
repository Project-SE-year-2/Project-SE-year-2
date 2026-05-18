import pytest

from src.parsers.course_parser import CourseFileParser

def test_parse_courses_file_loads_courses_correctly(tmp_path):
    content = """$$$$
Physics 1
83102
Prof. O. Some
83101,1,FALL,Obligatory
83102,1,FALL,Obligatory
Exam
$$$$
Software Project
83533
Dr. Terry Bell
83108,2,SPRI,Obligatory
Project
"""

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    # Instantiate the class and call the parse method
    parser = CourseFileParser()
    courses = parser.parse(str(file_path))

    assert len(courses) == 2

    assert courses[0].name == "Physics 1"
    assert courses[0].course_id == "83102"
    assert courses[0].instructor == "Prof. O. Some"
    assert courses[0].evaluation == "Exam"

    assert len(courses[0].requirements) == 2

    assert courses[0].requirements[0].program_id == "83101"
    assert courses[0].requirements[0].year == 1
    assert courses[0].requirements[0].semester == "FALL"
    assert courses[0].requirements[0].req_type == "Obligatory"

    assert courses[1].name == "Software Project"
    assert courses[1].evaluation == "Project"

# Tests that the course parser can load a large number of courses
# without crashing or skipping any course records.
def test_parse_courses_file_large_number_of_courses(tmp_path):
    records = []

    for i in range(30):
        record = f"""$$$$
Course {i}
83{i:03}
Dr. Test {i}
83101,1,FALL,Obligatory
Exam
"""
        records.append(record)

    content = "\n".join(records)

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = CourseFileParser()
    courses = parser.parse(str(file_path))

    assert len(courses) == 30

    assert courses[0].name == "Course 0"
    assert courses[0].course_id == "83000"

    assert courses[29].name == "Course 29"
    assert courses[29].course_id == "83029"

# Tests that the parser raises a clear ValueError
# when a program requirement line is missing fields.
def test_parse_courses_file_invalid_requirement_line(tmp_path):

    content = """$$$$
Physics 1
83102
Prof. O. Some
83101,1,FALL
Exam
"""

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = CourseFileParser()

    with pytest.raises(ValueError, match="Invalid requirement format in course 83102: 83101,1,FALL"):
        parser.parse(str(file_path))

# Tests that parsing an empty courses file
# returns an empty list without crashing.
def test_parse_courses_file_empty_file(tmp_path):

    file_path = tmp_path / "courses.txt"
    file_path.write_text("", encoding="utf-8")

    parser = CourseFileParser()
    courses = parser.parse(str(file_path))

    assert courses == []


# Tests that consecutive $$$$ separators
# without course content are ignored safely.
def test_parse_courses_file_ignores_empty_records(tmp_path):

    content = """$$$$
$$$$
Physics 1
83102
Prof. O. Some
83101,1,FALL,Obligatory
Exam
$$$$
$$$$
"""

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = CourseFileParser()
    courses = parser.parse(str(file_path))

    # Only the valid course should be loaded
    assert len(courses) == 1

    assert courses[0].name == "Physics 1"
    assert courses[0].course_id == "83102"


# Tests that the parser raises a clear ValueError when a course record
# is missing the course name field.
def test_parse_courses_file_missing_course_name(tmp_path):
    content = """$$$$

83102
Prof. O. Some
83101,1,FALL,Obligatory
Exam
"""

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = CourseFileParser()
    
    with pytest.raises(ValueError):
        parser.parse(str(file_path))


# Tests that the parser raises a clear ValueError when a course record
# is missing the course ID field.
def test_parse_courses_file_missing_course_id(tmp_path):
    content = """$$$$
Physics 1

Prof. O. Some
83101,1,FALL,Obligatory
Exam
"""

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = CourseFileParser()
    
    with pytest.raises(ValueError):
        parser.parse(str(file_path))


# Tests that the parser raises a clear ValueError when a course record
# is missing the instructor name field.
def test_parse_courses_file_missing_instructor_name(tmp_path):
    content = """$$$$
Physics 1
83102

83101,1,FALL,Obligatory
Exam
"""

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = CourseFileParser()
    
    with pytest.raises(ValueError):
        parser.parse(str(file_path))


# Tests that the parser raises a clear ValueError when a course record
# is missing the evaluation type field.
def test_parse_courses_file_missing_evaluation_type(tmp_path):
    content = """$$$$
Physics 1
83102
Prof. O. Some
83101,1,FALL,Obligatory

"""

    file_path = tmp_path / "courses.txt"
    file_path.write_text(content, encoding="utf-8")

    parser = CourseFileParser()
    
    with pytest.raises(ValueError):
        parser.parse(str(file_path))