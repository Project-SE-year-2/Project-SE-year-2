from src.course_parser import CourseFileParser

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