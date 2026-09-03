import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage

from contracts import (
    GateFinding,
    ReviewerReport,
    TesterReport,
    TestRunResult,
)
from workflow.node_handlers.main import build_main_nodes


class StubMainAgent:
    """避免调用真实模型，只返回固定的 Main Agent 回复。"""

    def __init__(self) -> None:
        self.last_input: object | None = None

    def invoke(self, _input: object) -> dict[str, object]:
        self.last_input = _input
        return {
            "messages": [
                AIMessage(content="已接收报告。"),
            ]
        }


class MainNodeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub_agent = StubMainAgent()
        patcher = patch(
            "workflow.node_handlers.main.build_main_agent",
            return_value=self.stub_agent,
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        self.nodes = build_main_nodes(object())  # type: ignore[arg-type]

    def test_review_main_uses_multi_agent_state_field_names(self) -> None:
        result = self.nodes["review_main_node"](
            {
                "user_request": "开发待办事项程序",
                "artifact_revision": 1,
                "reviewer_report": ReviewerReport(
                    passed=True,
                    revision=1,
                    findings=[],
                ),
                "review_repair_count": 0,
                "max_review_repairs": 3,
            }  # type: ignore[arg-type]
        )

        self.assertEqual(
            result,
            {
                "main_instruction": "已接收报告。",
                "review_repair_count": 0,
                "next_role": "tester",
                "phase": "testing",
                "status": "running",
            },
        )

    def test_test_main_uses_tester_state_field_names(self) -> None:
        try:
            result = self.nodes["test_main_node"](
                {
                    "user_request": "开发待办事项程序",
                    "artifact_revision": 1,
                    "tester_report": TesterReport(
                        passed=False,
                        revision=1,
                        test_results=[
                            TestRunResult(
                                test_id="python_project_tests",
                                command=["python", "-m", "unittest"],
                                exit_code=1,
                                stdout="",
                                stderr="test failed",
                            )
                        ],
                        findings=[
                            GateFinding(
                                category="functional_test",
                                severity="blocking",
                                message="功能测试失败。",
                                evidence="exit_code=1",
                                suggested_fix="修复失败功能。",
                            )
                        ],
                    ),
                    "tester_repair_count": 0,
                    "max_tester_repairs": 3,
                }  # type: ignore[arg-type]
            )
        except NameError as error:
            self.fail(f"Tester 修复计数字段名错误：{error}")

        self.assertEqual(
            result,
            {
                "main_instruction": "已接收报告。",
                "tester_repair_count": 1,
                "next_role": "implementer",
                "phase": "implementing",
                "status": "running",
            },
        )

        self.assertIsInstance(self.stub_agent.last_input, dict)
        messages = self.stub_agent.last_input["messages"]  # type: ignore[index]
        prompt = messages[0]["content"]
        self.assertIn("[修复次数]\n1/3", prompt)


if __name__ == "__main__":
    unittest.main()
