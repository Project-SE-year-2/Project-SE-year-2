import os
import sys

# Import the AppController which now manages the flow according to the UML
try:
    from src.app_controller import AppController
except ModuleNotFoundError:
    # Ensure project root is in sys.path for internal imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.app_controller import AppController

def main():
    # Use the same logic to determine the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check if the user provided paths via command line arguments 
    if len(sys.argv) == 4:
        courses_path = sys.argv[1]
        dates_path = sys.argv[2]
        programs_path = sys.argv[3]
    else:
        # Default: take the data from the project root folder
        courses_path = os.path.join(project_root, 'data', 'courses.txt')
        dates_path = os.path.join(project_root, 'data', 'dates.txt')
        programs_path = os.path.join(project_root, 'data', 'programs.txt')

    # Initialize the AppController as defined in the Class Diagram
    try:
        controller = AppController()
        
        # Start the application flow using the controller's run method
        # This matches the Runtime Flow UML
        controller.run(courses_path, dates_path, programs_path)
        
    except Exception as e:
        # Central error handling for any issues during parsing or execution
        print(f"Application Error: {e}")

if __name__ == "__main__":
    main()