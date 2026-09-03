import importlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from capabilities import (
    AgentRole,
    ToolRegistration,
    ToolRegistry,
    build_local_tool_registry,
    discover_local_tool_registrations,
)
from capabilities.local_tools.text_stats import (
    TextStatsInput,
    text_stats,
)


class LocalToolRegistryTests(unittest.TestCase):
    def test_discovers_text_stats_from_local_tools_package(self) -> None:
        registrations = discover_local_tool_registrations()

        tool_names = [
            registration.tool.name
            for registration in registrations
        ]

        self.assertIn("text_stats", tool_names)

    def test_role_permissions_enforce_the_approved_distribution(self) -> None:
        registry = build_local_tool_registry()
        expected_names_by_role = {
            AgentRole.MAIN_AGENT: [],
            AgentRole.PLANNER: ["text_stats"],
            AgentRole.EXPLORER: ["text_stats"],
            AgentRole.IMPLEMENTER: [],
            AgentRole.REVIEWER: ["text_stats"],
            AgentRole.TESTER: [],
            AgentRole.VERIFIER: ["text_stats"],
        }

        for role, expected_names in expected_names_by_role.items():
            with self.subTest(role=role.value):
                actual_names = [
                    tool.name
                    for tool in registry.tools_for(role)
                ]
                self.assertEqual(expected_names, actual_names)

    def test_rejects_duplicate_tool_names(self) -> None:
        registration = ToolRegistration(
            tool=text_stats,
            source="local",
            allowed_roles=frozenset({AgentRole.EXPLORER}),
            timeout_seconds=2.0,
        )
        registry = ToolRegistry()
        registry.register(registration)

        with self.assertRaisesRegex(
            ValueError,
            "Tool 名称重复：text_stats",
        ):
            registry.register(registration)

    def test_rejects_empty_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "Tool 来源不能为空"):
            ToolRegistration(
                tool=text_stats,
                source="   ",
                allowed_roles=frozenset({AgentRole.EXPLORER}),
                timeout_seconds=2.0,
            )

    def test_rejects_empty_role_set(self) -> None:
        with self.assertRaisesRegex(ValueError, "至少要授权"):
            ToolRegistration(
                tool=text_stats,
                source="local",
                allowed_roles=frozenset(),
                timeout_seconds=2.0,
            )

    def test_rejects_invalid_timeouts(self) -> None:
        invalid_timeouts = (
            0,
            -1,
            float("inf"),
            float("nan"),
            True,
        )

        for timeout in invalid_timeouts:
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ValueError, "Tool 超时时间"):
                    ToolRegistration(
                        tool=text_stats,
                        source="local",
                        allowed_roles=frozenset(
                            {AgentRole.EXPLORER}
                        ),
                        timeout_seconds=timeout,
                    )

    def test_new_plugin_module_is_discovered_without_registry_edits(
        self,
    ) -> None:
        module_source = """
            from langchain_core.tools import tool

            from capabilities.contracts import (
                AgentRole,
                ToolRegistration,
            )


            @tool
            def echo_local(value: str) -> str:
                \"\"\"Return the supplied value unchanged.\"\"\"
                return value


            TOOL_REGISTRATIONS = (
                ToolRegistration(
                    tool=echo_local,
                    source=\"local\",
                    allowed_roles=frozenset(
                        {AgentRole.EXPLORER}
                    ),
                    timeout_seconds=1.0,
                ),
            )
        """

        registrations = self._discover_temporary_plugin(
            module_source
        )

        self.assertEqual(
            ["echo_local"],
            [registration.tool.name for registration in registrations],
        )

    def test_rejects_plugin_without_registration_export(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "TOOL_REGISTRATIONS",
        ):
            self._discover_temporary_plugin("VALUE = 1")

    def test_text_stats_uses_its_declared_input_schema(self) -> None:
        self.assertIs(TextStatsInput, text_stats.args_schema)

    def test_text_stats_returns_hand_checked_counts(self) -> None:
        result = text_stats.invoke({"text": "robot arm MCP"})

        self.assertEqual(
            {
                "characters": 13,
                "non_whitespace_characters": 11,
                "words": 3,
                "lines": 1,
            },
            result,
        )

    def _discover_temporary_plugin(
        self,
        module_source: str,
    ) -> tuple[ToolRegistration, ...]:
        package_name = "temporary_local_tools_plugin"

        with tempfile.TemporaryDirectory() as temporary_directory:
            package_directory = (
                Path(temporary_directory) / package_name
            )
            package_directory.mkdir()
            (package_directory / "__init__.py").write_text(
                "",
                encoding="utf-8",
            )
            (package_directory / "sample_tool.py").write_text(
                textwrap.dedent(module_source),
                encoding="utf-8",
            )

            sys.path.insert(0, temporary_directory)
            importlib.invalidate_caches()

            try:
                return discover_local_tool_registrations(
                    package_name
                )
            finally:
                sys.path.remove(temporary_directory)
                for module_name in tuple(sys.modules):
                    if (
                        module_name == package_name
                        or module_name.startswith(
                            f"{package_name}."
                        )
                    ):
                        sys.modules.pop(module_name, None)
                importlib.invalidate_caches()


if __name__ == "__main__":
    unittest.main()
