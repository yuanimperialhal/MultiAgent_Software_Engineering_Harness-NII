import unittest
from pathlib import Path

from agents.tester.prompt import TESTER_SYSTEM_PROMPT


class TesterPromptContractTests(unittest.TestCase):
    def test_requires_real_execution_and_requirement_coverage(
        self,
    ) -> None:
        self.assertIn(
            "python_project_tests",
            TESTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "每一项用户需求",
            TESTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "测试覆盖不足",
            TESTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "只能建议使用 unittest",
            TESTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "不能建议 pytest",
            TESTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "先判断失败来自业务代码还是测试代码",
            TESTER_SYSTEM_PROMPT,
        )
        self.assertIn(
            "临时文件属于真实文件 I/O",
            TESTER_SYSTEM_PROMPT,
        )

    def test_sequential_entrypoint_uses_generic_tester_contract(
        self,
    ) -> None:
        stage_root = Path(__file__).resolve().parents[1]
        source = (stage_root / "main.py").read_text(
            encoding="utf-8",
        )

        self.assertNotIn("todo_syntax", source)
        self.assertIn("python_project_tests", source)
        self.assertIn("build_python_project_snapshot", source)


if __name__ == "__main__":
    unittest.main()
