import unittest
from unittest.mock import patch

from agents.explorer import agent as explorer
from agents.implementer import agent as implementer
from agents.main_agent import agent as main_agent
from agents.planner import agent as planner
from agents.reviewer import agent as reviewer
from agents.tester import agent as tester
from agents.verifier import agent as verifier
from capabilities.local_tools.text_stats import text_stats


class AgentToolInjectionTests(unittest.TestCase):
    def test_explicit_tools_replace_defaults_for_non_tester_agents(
        self,
    ) -> None:
        cases = (
            (main_agent, main_agent.build_main_agent),
            (planner, planner.build_planner_agent),
            (explorer, explorer.build_explorer_agent),
            (implementer, implementer.build_implementer_agent),
            (reviewer, reviewer.build_reviewer_agent),
            (verifier, verifier.build_verifier_agent),
        )

        for module, builder in cases:
            with self.subTest(agent=module.__name__):
                result = self._build_with_captured_arguments(
                    module,
                    builder,
                    tools=(text_stats,),
                )

                self.assertEqual(
                    ["text_stats"],
                    [tool.name for tool in result["tools"]],
                )

    def test_empty_tools_do_not_restore_non_tester_defaults(self) -> None:
        cases = (
            (main_agent, main_agent.build_main_agent),
            (planner, planner.build_planner_agent),
            (explorer, explorer.build_explorer_agent),
            (implementer, implementer.build_implementer_agent),
            (reviewer, reviewer.build_reviewer_agent),
            (verifier, verifier.build_verifier_agent),
        )

        for module, builder in cases:
            with self.subTest(agent=module.__name__):
                result = self._build_with_captured_arguments(
                    module,
                    builder,
                    tools=[],
                )

                self.assertEqual([], result["tools"])

    def test_none_preserves_non_tester_legacy_defaults(self) -> None:
        cases = (
            (main_agent, main_agent.build_main_agent, []),
            (planner, planner.build_planner_agent, []),
            (
                explorer,
                explorer.build_explorer_agent,
                ["submit_explorer_report"],
            ),
            (
                implementer,
                implementer.build_implementer_agent,
                ["submit_file_change"],
            ),
            (
                reviewer,
                reviewer.build_reviewer_agent,
                ["submit_reviewer_report"],
            ),
            (
                verifier,
                verifier.build_verifier_agent,
                ["submit_verifier_report"],
            ),
        )

        for module, builder, expected_names in cases:
            with self.subTest(agent=module.__name__):
                result = self._build_with_captured_arguments(
                    module,
                    builder,
                )

                self.assertEqual(
                    expected_names,
                    [tool.name for tool in result["tools"]],
                )

    def test_tester_legacy_runner_keeps_report_tool(self) -> None:
        result = self._build_with_captured_arguments(
            tester,
            tester.build_tester_agent,
            tester_runner_tool=text_stats,
        )

        self.assertEqual(
            ["text_stats", "submit_tester_report"],
            [tool.name for tool in result["tools"]],
        )

    def test_tester_explicit_tools_replace_legacy_defaults(self) -> None:
        result = self._build_with_captured_arguments(
            tester,
            tester.build_tester_agent,
            tools=(text_stats,),
        )

        self.assertEqual(
            ["text_stats"],
            [tool.name for tool in result["tools"]],
        )

    def test_tester_accepts_an_intentionally_empty_tool_list(self) -> None:
        result = self._build_with_captured_arguments(
            tester,
            tester.build_tester_agent,
            tools=[],
        )

        self.assertEqual([], result["tools"])

    def test_tester_rejects_two_tool_sources(self) -> None:
        with self.assertRaisesRegex(ValueError, "不能同时传入"):
            tester.build_tester_agent(
                object(),
                tester_runner_tool=text_stats,
                tools=[text_stats],
            )

    def test_tester_requires_one_tool_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "必须接收"):
            tester.build_tester_agent(object())

    def _build_with_captured_arguments(
        self,
        module,
        builder,
        **builder_arguments,
    ) -> dict:
        with patch.object(
            module,
            "create_agent",
            side_effect=lambda **arguments: arguments,
        ):
            return builder(object(), **builder_arguments)


if __name__ == "__main__":
    unittest.main()
