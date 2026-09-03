import asyncio
import unittest
from taskgroup_example import run_task_group_demo


class TestTaskGroupDemo(unittest.TestCase):
    """Test suite for the TaskGroup demo function."""

    def test_task_group_failure_propagation(self):
        """
        Test that run_task_group_demo raises an ExceptionGroup
        containing a ValueError when a subtask fails.
        """
        with self.assertRaises(ExceptionGroup) as cm:
            asyncio.run(run_task_group_demo())

        # Verify the ExceptionGroup contains at least one ValueError
        exception_group = cm.exception
        value_errors = [e for e in exception_group.exceptions if isinstance(e, ValueError)]
        self.assertGreater(len(value_errors), 0, "ExceptionGroup does not contain any ValueError")
        self.assertIn("Something went wrong in a task!", str(value_errors[0]))

    def test_task_group_all_success(self):
        """
        Test that run_task_group_demo returns None and prints success message
        when all tasks succeed.
        """
        # Patch stdout to capture print output
        import io
        import sys
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            result = asyncio.run(run_task_group_demo(include_failure=False))
            self.assertIsNone(result)
            output = captured_output.getvalue()
            self.assertIn("All tasks completed successfully.", output)
        finally:
            sys.stdout = sys.__stdout__


if __name__ == "__main__":
    unittest.main()
