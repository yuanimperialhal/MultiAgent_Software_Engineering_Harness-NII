import sys
import unittest
from pathlib import Path


def main() -> int:
    """发现并运行当前项目中的 unittest 功能测试。"""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    project_root = Path.cwd().resolve()
    tests_root = project_root / "tests"

    excluded_directories = {
        ".git",
        ".venv",
        "__pycache__",
        "venv",
    }

    for source_path in sorted(project_root.rglob("*.py")):
        relative_path = source_path.relative_to(project_root)
        if any(
            part in excluded_directories
            for part in relative_path.parts
        ):
            continue

        try:
            source = source_path.read_text(encoding="utf-8")
            compile(
                source,
                relative_path.as_posix(),
                "exec",
            )
        except (OSError, SyntaxError, UnicodeError) as error:
            print(
                f"语法检查失败：{relative_path.as_posix()}：{error}",
                file=sys.stderr,
            )
            return 3

    sys.path.insert(0, str(project_root))

    if tests_root.is_dir():
        suite = unittest.defaultTestLoader.discover(
            start_dir=str(tests_root),
            pattern="test_*.py",
        )
    else:
        suite = unittest.TestSuite()

    if suite.countTestCases() == 0:
        print(
            "未发现功能测试：请在 tests/ 中提供 test_*.py。",
            file=sys.stderr,
        )
        return 2

    result = unittest.TextTestRunner(
        verbosity=2,
    ).run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
