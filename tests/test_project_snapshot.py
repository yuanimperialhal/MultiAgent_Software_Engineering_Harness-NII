import tempfile
import unittest
from pathlib import Path

from workflow.node_handlers import common


class ProjectSnapshotTests(unittest.TestCase):
    def test_snapshot_includes_nested_python_test_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            tests_root = project_root / "tests"
            tests_root.mkdir()

            (project_root / "app.py").write_text(
                "VALUE = 1\n",
                encoding="utf-8",
            )
            (tests_root / "test_app.py").write_text(
                "from app import VALUE\n",
                encoding="utf-8",
            )

            build_snapshot = getattr(
                common,
                "build_python_project_snapshot",
                None,
            )
            self.assertTrue(
                callable(build_snapshot),
                "尚未实现递归 Python 项目快照函数",
            )

            snapshot = build_snapshot(project_root)

        self.assertIn("### app.py", snapshot)
        self.assertIn("### tests/test_app.py", snapshot)


    def test_snapshot_includes_frontend_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            frontend_root = project_root / "codex-landing"
            frontend_root.mkdir()

            (frontend_root / "index.html").write_text(
                "<h1>Codex</h1>\n",
                encoding="utf-8",
            )
            (frontend_root / "style.css").write_text(
                "body { color: black; }\n",
                encoding="utf-8",
            )

            snapshot = (
                common.build_python_project_snapshot(
                    project_root
                )
            )

        self.assertIn(
            "### codex-landing/index.html",
            snapshot,
        )
        self.assertIn(
            "```html",
            snapshot,
        )
        self.assertIn(
            "### codex-landing/style.css",
            snapshot,
        )
        self.assertIn(
            "```css",
            snapshot,
        )

if __name__ == "__main__":
    unittest.main()
