import os
import sys
import argparse

from src.parsers.constraint_settings_loader import ConstraintSettingsLoader

# Import the AppController which now manages the flow according to the UML
try:
    from src.app_controller import AppController
except ModuleNotFoundError:
    # Ensure project root is in sys.path for internal imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.app_controller import AppController


def parse_args(argv: list[str]):
    """Parse CLI arguments for input files and advanced constraint settings."""
    parser = argparse.ArgumentParser()

    parser.add_argument("--courses-file", default=None)
    parser.add_argument("--dates-file", default=None)
    parser.add_argument("--programs-file", default=None)
    parser.add_argument("--constraints-file", default=None)

    known_args, remaining_args = parser.parse_known_args(argv)
    return known_args, remaining_args


def main():
    # Use the same logic to determine the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    known_args, remaining_args = parse_args(sys.argv[1:])

    courses_path = (
        known_args.courses_file
        or os.path.join(project_root, "data", "courses.txt")
    )

    dates_path = (
        known_args.dates_file
        or os.path.join(project_root, "data", "dates.txt")
    )

    programs_path = (
        known_args.programs_file
        or os.path.join(project_root, "data", "programs.txt")   
    )

    # Initialize the AppController as defined in the Class Diagram
    try:
        controller = AppController()

        if known_args.constraints_file:
            settings = ConstraintSettingsLoader.from_file(
                known_args.constraints_file
            )
        else:
            settings = ConstraintSettingsLoader.from_cli_args(
                remaining_args
            )
        
        # Start the application flow using the controller's run method
        # This matches the Runtime Flow UML
        controller.run(courses_path, dates_path, programs_path, settings)
        
    except Exception as e:
        # Central error handling for any issues during parsing or execution
        print(f"Application Error: {e}")

if __name__ == "__main__":
    main()