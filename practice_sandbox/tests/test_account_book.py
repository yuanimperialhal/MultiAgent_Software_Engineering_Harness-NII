import unittest
from unittest.mock import patch, MagicMock
import io
import sys
import tempfile
import json
import os  # Added missing import for os

# Import the module under test
from account_book import AccountRecord, AccountBook, main


class TestAccountRecord(unittest.TestCase):
    """Test cases for AccountRecord class."""

    def test_valid_initialization(self):
        record = AccountRecord("2023-01-01", "income", 100.5, "salary", "food")
        self.assertEqual(record.date, "2023-01-01")
        self.assertEqual(record.type, "income")
        self.assertEqual(record.amount, 100.5)
        self.assertEqual(record.note, "salary")
        self.assertEqual(record.category, "food")

    def test_invalid_record_type(self):
        with self.assertRaises(ValueError) as cm:
            AccountRecord("2023-01-01", "invalid", 100.0, "test", "misc")
        self.assertIn("record_type must be 'income' or 'expense'", str(cm.exception))

    def test_negative_amount(self):
        with self.assertRaises(ValueError) as cm:
            AccountRecord("2023-01-01", "expense", -50.0, "test", "misc")
        self.assertIn("amount must be non-negative", str(cm.exception))

    def test_invalid_date_format(self):
        with self.assertRaises(ValueError) as cm:
            AccountRecord("01-01-2023", "income", 100.0, "test", "misc")
        self.assertIn("date must be in 'YYYY-MM-DD' format", str(cm.exception))

    def test_to_dict_and_from_dict_roundtrip(self):
        original = AccountRecord("2023-01-01", "income", 100.5, "bonus", "salary")
        d = original.to_dict()
        restored = AccountRecord.from_dict(d)
        self.assertEqual(original.date, restored.date)
        self.assertEqual(original.type, restored.type)
        self.assertEqual(original.amount, restored.amount)
        self.assertEqual(original.note, restored.note)
        self.assertEqual(original.category, restored.category)


class TestAccountBook(unittest.TestCase):
    """Test cases for AccountBook class."""

    def setUp(self):
        self.book = AccountBook()

    def test_add_record_success(self):
        self.book.add_record("2023-01-01", "income", 100.0, "salary", "food")
        records = self.book.get_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].date, "2023-01-01")
        self.assertEqual(records[0].type, "income")
        self.assertEqual(records[0].amount, 100.0)
        self.assertEqual(records[0].category, "food")

    def test_add_record_invalid_type(self):
        with self.assertRaises(ValueError) as cm:
            self.book.add_record("2023-01-01", "debt", 100.0, "test", "misc")
        self.assertIn("record_type must be 'income' or 'expense'", str(cm.exception))

    def test_add_record_negative_amount(self):
        with self.assertRaises(ValueError) as cm:
            self.book.add_record("2023-01-01", "expense", -50.0, "test", "misc")
        self.assertIn("amount must be non-negative", str(cm.exception))

    def test_add_record_invalid_date(self):
        with self.assertRaises(ValueError) as cm:
            self.book.add_record("01/01/2023", "income", 100.0, "test", "misc")
        self.assertIn("date must be in 'YYYY-MM-DD' format", str(cm.exception))

    def test_query_by_date_range(self):
        self.book.add_record("2023-01-01", "income", 100.0, "test", "food")
        self.book.add_record("2023-01-02", "expense", 30.0, "test", "transport")
        self.book.add_record("2023-01-03", "income", 200.0, "test", "salary")

        result = self.book.query_by_date_range("2023-01-01", "2023-01-02")
        self.assertEqual(len(result), 2)

        # Test invalid date range
        with self.assertRaises(ValueError) as cm:
            self.book.query_by_date_range("2023-01-03", "2023-01-02")
        self.assertIn("start_date must be <= end_date", str(cm.exception))

    def test_query_by_type(self):
        self.book.add_record("2023-01-01", "income", 100.0, "test", "food")
        self.book.add_record("2023-01-02", "expense", 30.0, "test", "transport")
        self.book.add_record("2023-01-03", "income", 200.0, "test", "salary")

        income_records = self.book.query_by_type("income")
        self.assertEqual(len(income_records), 2)

        expense_records = self.book.query_by_type("expense")
        self.assertEqual(len(expense_records), 1)

        with self.assertRaises(ValueError) as cm:
            self.book.query_by_type("invalid")
        self.assertIn("record_type must be 'income' or 'expense'", str(cm.exception))

    def test_get_summary(self):
        self.book.add_record("2023-01-01", "income", 100.0, "test", "salary")
        self.book.add_record("2023-01-02", "expense", 30.0, "test", "food")
        self.book.add_record("2023-01-03", "income", 200.0, "test", "salary")
        self.book.add_record("2023-01-04", "expense", 50.0, "test", "transport")

        summary = self.book.get_summary()
        self.assertEqual(summary["total_income"], 300.0)
        self.assertEqual(summary["total_expense"], 80.0)
        self.assertEqual(summary["balance"], 220.0)

    def test_save_and_load_from_file_isolation(self):
        # Use a temporary file to avoid side effects
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            filepath = tmp.name

        try:
            # Add some records
            self.book.add_record("2023-01-01", "income", 100.0, "test", "salary")
            self.book.add_record("2023-01-02", "expense", 30.0, "test", "food")

            # Save
            self.book.save_to_file(filepath)

            # Verify file content
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["date"], "2023-01-01")
            self.assertEqual(data[0]["category"], "salary")

            # Load into new book
            new_book = AccountBook()
            new_book.load_from_file(filepath)

            loaded_records = new_book.get_all()
            self.assertEqual(len(loaded_records), 2)
            self.assertEqual(loaded_records[0].date, "2023-01-01")
            self.assertEqual(loaded_records[0].category, "salary")
            self.assertEqual(loaded_records[1].category, "food")
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_from_corrupted_file_fallbacks(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            filepath = tmp.name

        try:
            # Write malformed JSON
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("{ invalid json ")

            # Load should fallback silently
            book = AccountBook()
            book.load_from_file(filepath)
            self.assertEqual(len(book.get_all()), 0)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_from_missing_file_fallbacks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = os.path.join(tmpdir, "missing.json")
            book = AccountBook()
            book.load_from_file(missing_path)
            self.assertEqual(len(book.get_all()), 0)


class TestAccountBookCLI(unittest.TestCase):
    """Test cases for CLI interaction using mock input/output."""

    def setUp(self):
        # Capture stdout
        self.held, sys.stdout = sys.stdout, io.StringIO()

    def tearDown(self):
        sys.stdout = self.held

    @patch('sys.argv', ['main.py', 'add', '--date', '2023-01-01', '--amount', '100.0', '--type', 'income', '--category', 'salary'])
    def test_main_add_and_exit(self):
        try:
            main()
        except SystemExit:
            pass
        output = sys.stdout.getvalue()
        self.assertIn("✅ 记录已添加。", output)

    @patch('sys.argv', ['main.py', 'add', '--date', '2023-01-01', '--amount', '100.0', '--type', 'income', '--category', 'salary'])
    def test_main_add_and_exit_with_category(self):
        try:
            main()
        except SystemExit:
            pass
        output = sys.stdout.getvalue()
        self.assertIn("✅ 记录已添加。", output)

    @patch('sys.argv', ['main.py'])
    def test_main_exit_immediately(self):
        try:
            main()
        except SystemExit:
            pass
        output = sys.stdout.getvalue()
        # argparse prints help when no subcommand given — this is expected behavior
        # We expect usage print, not exit message; CLI tests now match argparse contract
        self.assertIn("usage:", output)
        self.assertIn("add", output)
        self.assertIn("list", output)
        self.assertIn("summary", output)

    @patch('sys.argv', ['main.py', 'list'])
    def test_main_list_all_empty(self):
        # Ensure clean state: remove any existing data.json before test
        if os.path.exists("data.json"):
            os.unlink("data.json")
        try:
            main()
        except SystemExit:
            pass
        output = sys.stdout.getvalue()
        self.assertIn("(暂无数据)", output)

    @patch('sys.argv', ['main.py', 'summary'])
    def test_main_summary(self):
        # Ensure clean state: remove any existing data.json before test
        if os.path.exists("data.json"):
            os.unlink("data.json")
        try:
            main()
        except SystemExit:
            pass
        output = sys.stdout.getvalue()
        self.assertIn("📊 汇总统计：", output)
        self.assertIn("总收入：¥0.00", output)
        self.assertIn("总支出：¥0.00", output)
        self.assertIn("余额：  ¥0.00", output)


if __name__ == "__main__":
    unittest.main()
