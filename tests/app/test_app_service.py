import unittest
from unittest.mock import MagicMock
import json

# Import the application service class to be tested
from src.app_service import app_service

class TestAppService(unittest.TestCase):

    def setUp(self):
        """
        Set up testing environment before each test case execution.
        Initializes the Singleton service instance and mocks its DataStore dependency.
        """
        self.service = app_service() 
        self.service._datastore = MagicMock()

    def test_get_available_programs(self):
        """
        Verify that get_available_programs correctly fetches raw data from the datastore
        and formats it into a list of dictionaries required by the UI components.
        """
        # Mock the datastore to return specific raw program IDs
        self.service._datastore.get_programs.return_value = ['83101', '83102']
        
        # Execute the service method
        result = self.service.get_available_programs()
        
        # Assertions to verify the structured output format for the UI
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], '83101')
        self.assertEqual(result[0]['name'], 'Program 83101')
        self.assertEqual(result[1]['id'], '83102')

    def test_select_programs_valid(self):
        """
        Test the happy path for selecting programs.
        Verifies that a valid list of program IDs (strings of 5 digits, max 5 items)
        is accepted and stored correctly in the service state.
        """
        valid_ids = ['83101', '83102', '83108']
        
        # Execute the method; should run without raising any exceptions
        self.service.select_programs(valid_ids)
        
        # Verify state persistence within the service instance
        self.assertEqual(self.service._selected_programs, valid_ids)

    def test_select_programs_exceeds_maximum(self):
        """
        Validate business rules regarding maximum program selections.
        Ensures a ValueError is raised when trying to select more than 5 programs.
        """
        too_many_ids = ['11111', '22222', '33333', '44444', '55555', '66666']
        
        # Assert that the service guards against selections larger than 5 items
        with self.assertRaises(ValueError) as context:
            self.service.select_programs(too_many_ids)
            
        self.assertTrue("Maximum of 5" in str(context.exception))

    def test_select_programs_invalid_format(self):
        """
        Validate input format enforcement for selected program IDs.
        Ensures a ValueError is raised for inputs containing non-5-digit strings,
        incorrect lengths, or wrong data types.
        """
        invalid_inputs = [
            ['1234'],       # Edge Case: Length too short
            ['123456'],     # Edge Case: Length too long
            ['ABCDE'],      # Edge Case: Alphabetic characters instead of digits
            [12345],        # Edge Case: Incorrect type (int instead of str)
            ['83101', 'X']  # Mixed Case: One valid, one invalid format
        ]
        
        # Iterate through all invalid formats and assert that validation fails
        for invalid_ids in invalid_inputs:
            with self.assertRaises(ValueError):
                self.service.select_programs(invalid_ids)

    def test_get_courses(self):
        """
        Verify that get_courses filters and transforms nested datastore course objects
        into the explicit, flattened dictionary format expected by the UI view layer.
        """
        # Create a mock requirement object mimicking the nested data layout
        mock_req = MagicMock()
        mock_req.program_id = '83101'
        mock_req.year = 2
        mock_req.semester.name = 'SPRING'
        mock_req.req_type.name = 'Obligatory'
        
        # Create a mock course object containing the simulated requirements list
        mock_course = MagicMock()
        mock_course.course_id = '111'
        mock_course.name = 'Data Structures'
        mock_course.evaluation.name = 'Exam'
        mock_course.requirements = [mock_req]
        
        # Inject the mock objects into the mocked datastore layer
        self.service._datastore.get_courses.return_value = [mock_course]
        
        # Execute the mapping workflow
        result = self.service.get_courses('83101')
        
        # Assert that the underlying dependency was called with the correct parameters
        self.service._datastore.get_courses.assert_called_once_with('83101')
        
        # Assert that nested object values were safely mapped and stringified for the UI grid
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['number'], '111')
        self.assertEqual(result[0]['name'], 'Data Structures')
        self.assertEqual(result[0]['year'], '2')
        self.assertEqual(result[0]['semester'], 'SPRING')
        self.assertEqual(result[0]['type'], 'Obligatory')
        self.assertEqual(result[0]['evaluation'], 'Exam')

if __name__ == '__main__':
    unittest.main()