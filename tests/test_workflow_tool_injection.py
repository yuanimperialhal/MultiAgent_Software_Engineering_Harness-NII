import unittest
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from langchain_core.tools import StructuredTool

from agents.explorer import agent as explorer
from agents.implementer import agent as implementer
from agents.main_agent import agent as main_agent
from agents.planner import agent as planner
from agents.reviewer import agent as reviewer
from agents.tester import agent as tester
from agents.verifier import agent as verifier
from capabilities import AgentRole, build_tool_registry
from workflow import build_planning_nodes


def fake_search(query: str, numResults: int = 5) -> str:
    """Return a deterministic fake search result."""
    return f"search:{query}:{numResults}"


def fake_fetch(urls: list[str], maxCharacters: int = 1000) -> str:
    """Return deterministic fake webpage content."""
    return f"fetch:{','.join(urls)}:{maxCharacters}"


class WorkflowToolInjectionTests(unittest.TestCase):
    def test_registry_permissions_reach_each_created_agent(self) -> None:
        fake_exa_tools = [
            StructuredTool.from_function(
                fake_search,
                name="web_search_exa",
                description="Fake Exa search for offline tests.",
            ),
            StructuredTool.from_function(
                fake_fetch,
                name="web_fetch_exa",
                description="Fake Exa fetch for offline tests.",
            ),
        ]
        captured_tool_names: dict[AgentRole, list[str]] = {}
        agent_modules = {
            AgentRole.MAIN_AGENT: main_agent,
            AgentRole.PLANNER: planner,
            AgentRole.EXPLORER: explorer,
            AgentRole.IMPLEMENTER: implementer,
            AgentRole.REVIEWER: reviewer,
            AgentRole.TESTER: tester,
            AgentRole.VERIFIER: verifier,
        }

        def capture_agent(role: AgentRole):
            def fake_create_agent(**arguments):
                captured_tool_names[role] = [
                    tool.name
                    for tool in arguments["tools"]
                ]
                return object()

            return fake_create_agent

        with TemporaryDirectory() as temporary_directory:
            registry = build_tool_registry(
                Path(temporary_directory),
                exa_tools=fake_exa_tools,
            )

            with ExitStack() as stack:
                for role, module in agent_modules.items():
                    stack.enter_context(
                        patch.object(
                            module,
                            "create_agent",
                            side_effect=capture_agent(role),
                        )
                    )

                build_planning_nodes(
                    object(),
                    tool_registry=registry,
                )

        self.assertEqual(
            {
                AgentRole.MAIN_AGENT: [],
                AgentRole.PLANNER: [
                    "text_stats",
                    "web_fetch_exa",
                    "web_search_exa",
                ],
                AgentRole.EXPLORER: [
                    "submit_explorer_report",
                    "text_stats",
                    "web_fetch_exa",
                    "web_search_exa",
                ],
                AgentRole.IMPLEMENTER: [
                    "submit_file_change",
                ],
                AgentRole.REVIEWER: [
                    "submit_reviewer_report",
                    "text_stats",
                    "web_fetch_exa",
                ],
                AgentRole.TESTER: [
                    "run_allowed_test",
                    "submit_tester_report",
                ],
                AgentRole.VERIFIER: [
                    "submit_verifier_report",
                    "text_stats",
                    "web_fetch_exa",
                ],
            },
            captured_tool_names,
        )


if __name__ == "__main__":
    unittest.main()
