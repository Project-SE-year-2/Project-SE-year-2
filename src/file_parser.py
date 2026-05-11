import os
import re
from datetime import datetime, timedelta

from src.course import Course, ProgramRequirement
from src.exam_period import ExamPeriod

def parse_courses_file(filepath: str) -> list[Course]:
    courses = []
    
    #read the file with UTF-8 encoding
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split the content into records by $$$$ 
    raw_records = content.split('$$$$')

    for record in raw_records:
        #remove empty lines
        lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
        
        if not lines:
            continue
        #extract course metadata
        name = lines[0]
        course_id = lines[1]
        instructor = lines[2]
        evaluation = lines[-1]

        course = Course(name, course_id, instructor, evaluation)
        #extract program requirements
        for i in range(3, len(lines) - 1):
            prog_data = lines[i].split(',')
            
            if len(prog_data) == 4:
                prog_id = prog_data[0].strip()
                year = int(prog_data[1].strip())
                semester = prog_data[2].strip()
                req_type = prog_data[3].strip()
                #create and attach the requirement to the course object
                requirement = ProgramRequirement(prog_id, year, semester, req_type)
                course.add_requirement(requirement)

        courses.append(course)

    return courses
#Parses the exam periods file and handles excluded dates and date ranges
def parse_exam_periods_file(filepath: str) -> list[ExamPeriod]:
    periods = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    raw_records = content.split('$$$$')
    
    #find DD-MM-YYYY format in a string
    date_pattern = r'\d{2}-\d{2}-\d{4}'

    for record in raw_records:
        lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
        if not lines:
            continue
        #extaract Semester and Moed - FALL, Aleph
        sem_moed = lines[0].split(',')
        semester = sem_moed[0].strip()
        moed = sem_moed[1].strip()

        #extarct start and end dates of the exam period
        start_end = lines[1].split(',')
        period = ExamPeriod(semester, moed, start_end[0].strip(), start_end[1].strip())
        #Handle excluded dates or date ranges logic
        #################################################################
        #
        #
        #logic to extract forbidden dates
        #
        #
        #################################################################
        periods.append(period)

    return periods

def parse_programs_file(filepath: str) -> list[str]:
    # Read simple comma-separated file of selected program ID
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    #split by comma and strip whitespace from each program ID
    return [prog.strip() for prog in content.split(',') if prog.strip()]