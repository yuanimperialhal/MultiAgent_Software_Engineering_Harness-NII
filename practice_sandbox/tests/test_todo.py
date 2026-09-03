import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the module under test
from todo import TodoItem, TodoManager


class TestTodoItem(unittest.TestCase):
    """Test cases for TodoItem class."""

    def test_valid_initialization(self):
        item = TodoItem(1, "Test Title")
        self.assertEqual(item.id, 1)
        self.assertEqual(item.title, "Test Title")
        self.assertEqual(item.status, "pending")
        self.assertIsNone(item.due_date)
        self.assertIsNotNone(item.created_at)

    def test_invalid_id(self):
        with self.assertRaises(ValueError) as cm:
            TodoItem(0, "Title")
        self.assertIn("positive integer", str(cm.exception))

    def test_empty_title(self):
        with self.assertRaises(ValueError) as cm:
            TodoItem(1, "")
        self.assertIn("non-empty string", str(cm.exception))

    def test_invalid_status(self):
        with self.assertRaises(ValueError) as cm:
            TodoItem(1, "Title", status="invalid")
        self.assertIn("'pending' or 'completed'", str(cm.exception))

    def test_invalid_due_date(self):
        with self.assertRaises(ValueError) as cm:
            TodoItem(1, "Title", due_date="2023-13-01")
        self.assertIn("invalid due_date format", str(cm.exception))

    def test_to_dict_and_from_dict_roundtrip(self):
        original = TodoItem(1, "Test", desc="Desc", due_date="2023-12-25", status="completed")
        d = original.to_dict()
        restored = TodoItem.from_dict(d)
        self.assertEqual(original.id, restored.id)
        self.assertEqual(original.title, restored.title)
        self.assertEqual(original.desc, restored.desc)
        self.assertEqual(original.due_date, restored.due_date)
        self.assertEqual(original.status, restored.status)


class TestTodoManager(unittest.TestCase):
    """Test cases for TodoManager class."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.todo_file = Path(self.temp_dir.name) / "todos.json"
        self.todo_file_patcher = patch(
            "todo.TODO_FILE",
            str(self.todo_file),
        )
        self.todo_file_patcher.start()

        self.manager = TodoManager()

    def tearDown(self):
        self.todo_file_patcher.stop()
        self.temp_dir.cleanup()

    def test_add_item_returns_id(self):
        tid = self.manager.add_item("First task")
        self.assertEqual(tid, 1)
        self.assertEqual(len(self.manager.get_all()), 1)

    def test_get_all_returns_sorted_by_id(self):
        self.manager.add_item("Third")
        self.manager.add_item("First")
        self.manager.add_item("Second")
        all_tasks = self.manager.get_all()
        self.assertEqual([t.id for t in all_tasks], [1, 2, 3])

    def test_get_by_status_pending(self):
        self.manager.add_item("Pending 1")
        self.manager.add_item("Pending 2")
        self.manager.add_item("Completed")
        # Mark one as completed *after* creation, not at add time
        self.manager.mark_completed(3)
        pending = self.manager.get_by_status("pending")
        self.assertEqual(len(pending), 2)

    def test_get_by_status_completed(self):
        self.manager.add_item("Pending")
        self.manager.add_item("Completed 1")
        self.manager.add_item("Completed 2")
        # Mark two as completed
        self.manager.mark_completed(2)
        self.manager.mark_completed(3)
        completed = self.manager.get_by_status("completed")
        self.assertEqual(len(completed), 2)

    def test_mark_completed_success(self):
        tid = self.manager.add_item("To complete")
        result = self.manager.mark_completed(tid)
        self.assertTrue(result)
        task = self.manager.get_all()[0]
        self.assertEqual(task.status, "completed")

    def test_mark_completed_failure_nonexistent(self):
        result = self.manager.mark_completed(999)
        self.assertFalse(result)

    def test_mark_completed_failure_already_completed(self):
        tid = self.manager.add_item("Already done")
        self.manager.mark_completed(tid)  # make it completed
        result = self.manager.mark_completed(tid)
        self.assertFalse(result)

    def test_save_and_load_from_file_isolation(self):
        self.manager.add_item("Task 1")
        self.manager.add_item(
            "Task 2",
            desc="desc",
            due_date="2023-01-01",
        )
        self.manager.save_to_file(str(self.todo_file))

        stored_data = json.loads(
            self.todo_file.read_text(encoding="utf-8")
        )
        self.assertEqual(stored_data[0]["title"], "Task 1")
        self.assertEqual(stored_data[1]["due_date"], "2023-01-01")

        new_manager = TodoManager()
        loaded = new_manager.get_all()

        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].title, "Task 1")
        self.assertEqual(loaded[1].title, "Task 2")
        self.assertEqual(loaded[1].desc, "desc")
        self.assertEqual(loaded[1].due_date, "2023-01-01")

    def test_load_from_corrupted_file_fallbacks(self):
        self.todo_file.write_text(
            "{ invalid json ",
            encoding="utf-8",
        )

        manager = TodoManager()

        self.assertEqual(len(manager.get_all()), 0)
        self.assertEqual(manager._next_id, 1)

    def test_delete_item_success(self):
        tid = self.manager.add_item("To delete")
        self.assertTrue(self.manager.delete_item(tid))
        self.assertEqual(len(self.manager.get_all()), 0)

    def test_delete_item_failure_nonexistent(self):
        self.assertFalse(self.manager.delete_item(999))

    def test_search_by_keyword_title_match(self):
        self.manager.add_item("Buy milk")
        self.manager.add_item("Call mom")
        self.manager.add_item("Send report")
        
        results = self.manager.search_by_keyword("milk")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Buy milk")

    def test_search_by_keyword_desc_match(self):
        self.manager.add_item("Meeting", desc="Discuss Q3 sales targets")
        self.manager.add_item("Lunch", desc="With team")
        
        results = self.manager.search_by_keyword("sales")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Meeting")

    def test_search_by_keyword_case_insensitive(self):
        self.manager.add_item("Prepare presentation")
        
        results = self.manager.search_by_keyword("PRESENTATION")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Prepare presentation")

    def test_search_by_keyword_partial_match(self):
        self.manager.add_item("Refactor authentication module")
        
        results = self.manager.search_by_keyword("auth")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Refactor authentication module")

    def test_search_by_keyword_no_match(self):
        self.manager.add_item("Buy groceries")
        self.manager.add_item("Walk the dog")
        
        results = self.manager.search_by_keyword("xyz")
        self.assertEqual(len(results), 0)

    def test_search_by_keyword_empty_string(self):
        self.manager.add_item("Task 1")
        self.manager.add_item("Task 2")
        
        results = self.manager.search_by_keyword("")
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
