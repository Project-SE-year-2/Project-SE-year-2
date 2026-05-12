import os
import sys

try:
    from src.file_parser import parse_courses_file, parse_exam_periods_file, parse_programs_file
    from src.course_parser import filter_courses_for_scheduling
except ModuleNotFoundError:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.file_parser import parse_courses_file, parse_exam_periods_file, parse_programs_file
    from src.course_parser import filter_courses_for_scheduling

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check if the user provided paths via command line arguments
    if len(sys.argv) == 4:
        courses_path = sys.argv[1]
        dates_path = sys.argv[2]
        programs_path = sys.argv[3]
    else:
        # take the data from the project root so this works from any cwd
        courses_path = os.path.join(project_root, 'data', 'courses.txt')
        dates_path = os.path.join(project_root, 'data', 'dates.txt')
        programs_path = os.path.join(project_root, 'data', 'programs.txt')

    # List of paths to validate
    paths = [courses_path, dates_path, programs_path]

    for path in paths:
        #check file existence
        if not os.path.exists(path):
            print(f"Error: Could not find file at {path}!")
            return
        
        #check if there an empty file
        if os.path.getsize(path) == 0:
            print(f"Error: The file at {path} is empty! Please provide input data.")
            return

    #Courses Parser
    courses = parse_courses_file(courses_path)
    print(f"Successfully loaded {len(courses)} courses")

    #Exam Periods Parser
    periods = parse_exam_periods_file(dates_path)
    print(f"Successfully loaded {len(periods)} exam periods")
    
    #Programs Parser
    programs = parse_programs_file(programs_path)
    print(f"-> Successfully loaded {len(programs)} programs")
    print(f"-> Programs list: {programs}\n")
    
    # Filter courses by evaluation type and program membership
    valid_courses = filter_courses_for_scheduling(courses, programs)
    print(f"Filtered courses: {len(valid_courses)} valid courses for scheduling")
    print(f"  (filtered out {len(courses) - len(valid_courses)} courses)\n")

if __name__ == "__main__":
    main()