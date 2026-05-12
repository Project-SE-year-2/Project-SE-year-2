from src.course import Course


def filter_courses_for_scheduling(courses: list[Course], selected_programs: list[str]) -> list[Course]:
    """
    Filter courses to extract only those relevant for exam scheduling.

    Criteria:
    1. Evaluation Method: Course evaluation must be strictly "Exam".
    2. Program Membership: Course must belong to at least one of the selected programs.

    Args:
        courses: List of all parsed courses.
        selected_programs: List of program IDs selected by the user.

    Returns:
        Filtered list of valid courses ready for scheduling.

    Raises:
        ValueError: If selected_programs is empty.
    """
    # Validate input: need at least one program to filter by
    if not selected_programs:
        raise ValueError("At least one program must be selected for filtering")

    # Convert to set for O(1) lookup performance
    selected_programs_set = set(selected_programs)
    valid_courses = []

    # Iterate and apply both filter criteria
    for course in courses:
        # Step 1: Only keep courses with "Exam" evaluation type
        if course.evaluation != "Exam":
            continue

        # Step 2: Check if course belongs to any selected program via its requirements
        belongs_to_selected = any(
            req.program_id in selected_programs_set for req in course.requirements
        )

        # Step 3: Add to valid list only if both criteria pass
        if not belongs_to_selected:
            continue

        valid_courses.append(course)

    return valid_courses
