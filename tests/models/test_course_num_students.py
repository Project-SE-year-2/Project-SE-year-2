import pickle

import pytest

from src.models.course import Course
from src.models.enums import Evaluation


# Test that old course creation remains backward-compatible.
def test_course_default_num_students_is_zero():
    course = Course(
        name="Algorithms",
        course_id="89123",
        instructor="Dr. Cohen",
        evaluation=Evaluation.Exam,
    )

    assert course.num_students == 0


# Test that Course accepts a positive student count.
def test_course_accepts_positive_num_students():
    course = Course(
        name="Algorithms",
        course_id="89123",
        instructor="Dr. Cohen",
        evaluation=Evaluation.Exam,
        num_students=120,
    )

    assert course.num_students == 120


# Test that zero students is allowed for backward compatibility.
def test_course_accepts_zero_num_students():
    course = Course(
        name="Algorithms",
        course_id="89123",
        instructor="Dr. Cohen",
        evaluation=Evaluation.Exam,
        num_students=0,
    )

    assert course.num_students == 0


# Test that Course rejects negative student counts.
def test_course_rejects_negative_num_students():
    with pytest.raises(ValueError, match="num_students must be non-negative"):
        Course(
            name="Algorithms",
            course_id="89123",
            instructor="Dr. Cohen",
            evaluation=Evaluation.Exam,
            num_students=-1,
        )


# Test that Course rejects non-integer student counts.
def test_course_rejects_non_integer_num_students():
    with pytest.raises(ValueError, match="num_students must be an integer"):
        Course(
            name="Algorithms",
            course_id="89123",
            instructor="Dr. Cohen",
            evaluation=Evaluation.Exam,
            num_students=120.5,
        )


# Test that Course rejects bool values even though bool is a subclass of int.
def test_course_rejects_bool_num_students():
    with pytest.raises(ValueError, match="num_students must be an integer"):
        Course(
            name="Algorithms",
            course_id="89123",
            instructor="Dr. Cohen",
            evaluation=Evaluation.Exam,
            num_students=True,
        )


# Test that old pickled Course objects get num_students after unpickling.
def test_course_unpickle_adds_missing_num_students_default():
    course = Course(
        name="Algorithms",
        course_id="89123",
        instructor="Dr. Cohen",
        evaluation=Evaluation.Exam,
    )
    del course.__dict__["num_students"]

    restored = pickle.loads(pickle.dumps(course))

    assert restored.num_students == 0
