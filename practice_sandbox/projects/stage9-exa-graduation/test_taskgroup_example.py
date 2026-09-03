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


if __name__ == "__main__":
    unittest.main()
