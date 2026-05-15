from src.course import Course

# Validates that two courses are not scheduled on the same date
# if both are obligatory courses from the same program and same year.
#
# Raises:
#     ValueError:
#         If both courses belong to the same program and year
#         and both are marked as Obligatory.
def validate_no_same_program_obligatory_conflict(course1, course2, exam_date):

    for req1 in course1.requirements:

        for req2 in course2.requirements:

            if (
                req1.program_id == req2.program_id
                and req1.year == req2.year
                and req1.req_type == "Obligatory"
                and req2.req_type == "Obligatory"
            ):

                raise ValueError(
                    "Cannot schedule exams on the same date: "
                    "two obligatory courses from the same program and year"
                )

# Validates that there are enough available dates to schedule
# all obligatory exams for a selected program and year.
#
# Raises:
#     ValueError:
#         If the number of obligatory exams is greater than
#         the number of available exam dates.
def validate_enough_dates_for_obligatory_courses(
    courses: list[Course],
    selected_program: str,
    available_dates: list
):

    obligatory_courses = []

    for course in courses:
        for req in course.requirements:
            if (
                req.program_id == selected_program
                and req.req_type == "Obligatory"
            ):
                obligatory_courses.append(course)
                break

    if len(obligatory_courses) > len(available_dates):
        raise ValueError(
            f"Cannot schedule exams for program {selected_program}: "
            f"there are {len(obligatory_courses)} obligatory exams "
            f"but only {len(available_dates)} available exam dates"
        )