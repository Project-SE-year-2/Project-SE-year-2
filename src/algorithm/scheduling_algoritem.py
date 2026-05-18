from src.models.course import Course
from src.models.exam_period import ExamPeriod

def match_courses_to_periods(valid_courses: list[Course], periods: list[ExamPeriod]) -> dict[ExamPeriod, dict[Course, list[str]]]:
    """
    Maps each ExamPeriod to its scheduled courses. Each course appears exactly once 
    per period, mapped to a list of all program IDs it belongs to for that semester.
    """
    period_to_tasks = {}
    
    for period in periods:
        # Initialize an empty dictionary for the current exam period
        # This inner dictionary maps a single Course object to a list of Program IDs
        period_to_tasks[period] = {}
        
        for course in valid_courses:
            for req in course.requirements:
                # Match based on the semester defined in the course requirements
                if req.semester == period.semester:
                    
                    # If the course is not yet in this period's dictionary, initialize it
                    if course not in period_to_tasks[period]:
                        period_to_tasks[period][course] = []
                    
                    # Append the program ID to the course's list (avoiding duplicates)
                    if req.program_id not in period_to_tasks[period][course]:
                        period_to_tasks[period][course].append(req.program_id)
                            
    return period_to_tasks