import tempfile
import unittest
from pathlib import Path

from contracts import TestRunResult
from safety import build_test_runner_tool


class PythonProjectTestRunnerTests(unittest.TestCase):
    def run_project_tests(self, project_root: Path) -> TestRunResult:
        runner = build_test_runner_tool(project_root)

        try:
            raw_result = runner.invoke(
                {"test_id": "python_project_tests"}
            )
        except Exception as error:
            self.fail(
                "Runner 尚不支持通用 Python 项目测试："
                f"{error}"
            )

        return TestRunResult.model_validate_json(raw_result)

    def test_runs_functional_tests_for_a_generic_python_project(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            tests_root = project_root / "tests"
            tests_root.mkdir()

            (project_root / "calculator.py").write_text(
                "def add(left: int, right: int) -> int:\n"
                "    return left + right\n",
                encoding="utf-8",
            )
            (tests_root / "test_calculator.py").write_text(
                "import unittest\n\n"
                "from calculator import add\n\n\n"
                "class CalculatorTests(unittest.TestCase):\n"
                "    def test_adds_two_numbers(self):\n"
                "        self.assertEqual(add(2, 3), 5)\n",
                encoding="utf-8",
            )

            result = self.run_project_tests(project_root)

        self.assertEqual(result.test_id, "python_project_tests")
        self.assertEqual(result.exit_code, 0)
        self.assertIn(
            "Ran 1 test",
            result.stdout + result.stderr,
        )

    def test_fails_when_project_has_no_functional_tests(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "app.py").write_text(
                "VALUE = 1\n",
                encoding="utf-8",
            )

            result = self.run_project_tests(project_root)

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn(
            "未发现功能测试",
            result.stdout + result.stderr,
        )

    def test_fails_when_any_nested_python_file_has_invalid_syntax(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            tests_root = project_root / "tests"
            package_root = project_root / "package"
            tests_root.mkdir()
            package_root.mkdir()

            (project_root / "app.py").write_text(
                "VALUE = 1\n",
                encoding="utf-8",
            )
            (tests_root / "test_app.py").write_text(
                "import unittest\n\n"
                "from app import VALUE\n\n\n"
                "class AppTests(unittest.TestCase):\n"
                "    def test_value(self):\n"
                "        self.assertEqual(VALUE, 1)\n",
                encoding="utf-8",
            )
            (package_root / "broken.py").write_text(
                "def broken(:\n"
                "    pass\n",
                encoding="utf-8",
            )

            result = self.run_project_tests(project_root)

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn(
            "语法检查失败",
            result.stdout + result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
