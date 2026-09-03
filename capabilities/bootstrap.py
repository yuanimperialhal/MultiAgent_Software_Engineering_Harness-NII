#把所有来源组装起来
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from langchain_core.tools import BaseTool

from agents.explorer.agent import (
    submit_explorer_report,
)
from agents.implementer.agent import (
    submit_file_change,
)
from agents.reviewer.agent import (
    submit_reviewer_report,
)
from agents.tester.agent import (
    submit_tester_report,
)
from agents.verifier.agent import (
    submit_verifier_report,
)
from safety import build_test_runner_tool

from .contracts import AgentRole, ToolRegistration
from .registry import (
    ToolRegistry,
    discover_local_tool_registrations,
)
from .remote_tools.exa import (
    EXA_TOOL_NAMES,
    build_exa_sync_tools,
)


HARNESS_TOOL_TIMEOUT_SECONDS = 5.0
TEST_RUNNER_TIMEOUT_SECONDS = 15.0
EXA_TOOL_TIMEOUT_SECONDS = 20.0


EXA_ALLOWED_ROLES = {
    "web_search_exa": frozenset(
        {
            AgentRole.PLANNER,
            AgentRole.EXPLORER,
        }
    ),
    "web_fetch_exa": frozenset(
        {
            AgentRole.PLANNER,
            AgentRole.EXPLORER,
            AgentRole.REVIEWER,
            AgentRole.VERIFIER,
        }
    ),
}


def _harness_registrations(
    sandbox_root: Path,
) -> tuple[ToolRegistration, ...]:
    """建立原有 Harness Tool 的注册信息。"""

    return (
        ToolRegistration(
            tool=submit_explorer_report,
            source="harness",
            allowed_roles=frozenset(
                {AgentRole.EXPLORER}
            ),
            timeout_seconds=(
                HARNESS_TOOL_TIMEOUT_SECONDS
            ),
        ),
        ToolRegistration(
            tool=submit_file_change,
            source="harness",
            allowed_roles=frozenset(
                {AgentRole.IMPLEMENTER}
            ),
            timeout_seconds=(
                HARNESS_TOOL_TIMEOUT_SECONDS
            ),
        ),
        ToolRegistration(
            tool=submit_reviewer_report,
            source="harness",
            allowed_roles=frozenset(
                {AgentRole.REVIEWER}
            ),
            timeout_seconds=(
                HARNESS_TOOL_TIMEOUT_SECONDS
            ),
        ),
        ToolRegistration(
            tool=build_test_runner_tool(
                sandbox_root
            ),
            source="harness",
            allowed_roles=frozenset(
                {AgentRole.TESTER}
            ),
            timeout_seconds=(
                TEST_RUNNER_TIMEOUT_SECONDS
            ),
        ),
        ToolRegistration(
            tool=submit_tester_report,
            source="harness",
            allowed_roles=frozenset(
                {AgentRole.TESTER}
            ),
            timeout_seconds=(
                HARNESS_TOOL_TIMEOUT_SECONDS
            ),
        ),
        ToolRegistration(
            tool=submit_verifier_report,
            source="harness",
            allowed_roles=frozenset(
                {AgentRole.VERIFIER}
            ),
            timeout_seconds=(
                HARNESS_TOOL_TIMEOUT_SECONDS
            ),
        ),
    )


def _validate_exa_tools(
    exa_tools: Iterable[BaseTool],
) -> dict[str, BaseTool]:
    """确保进入注册表的 Exa Tool 完整且不重名。"""

    tools = list(exa_tools)
    name_counts = Counter(
        tool.name
        for tool in tools
    )

    duplicate_names = {
        name
        for name, count in name_counts.items()
        if count > 1
    }

    if duplicate_names:
        names = ", ".join(
            sorted(duplicate_names)
        )
        raise ValueError(
            f"Exa Tool 名称重复：{names}"
        )

    tools_by_name = {
        tool.name: tool
        for tool in tools
    }

    expected_names = set(EXA_TOOL_NAMES)
    actual_names = set(tools_by_name)

    if actual_names != expected_names:
        missing = sorted(
            expected_names - actual_names
        )
        unexpected = sorted(
            actual_names - expected_names
        )

        raise ValueError(
            "Exa Tool 集合不符合白名单；"
            f"缺少={missing}；"
            f"额外={unexpected}"
        )

    return tools_by_name


def build_tool_registry(
    sandbox_root: Path,
    *,
    exa_tools: Iterable[BaseTool] | None = None,
) -> ToolRegistry:
    """组装本地、Harness 和 Exa 三类 Tool。"""

    registry = ToolRegistry()

    for registration in (
        discover_local_tool_registrations()
    ):
        registry.register(registration)

    for registration in (
        _harness_registrations(sandbox_root)
    ):
        registry.register(registration)

    selected_exa_tools = (
        build_exa_sync_tools()
        if exa_tools is None
        else list(exa_tools)
    )

    exa_tools_by_name = _validate_exa_tools(
        selected_exa_tools
    )

    for tool_name in EXA_TOOL_NAMES:
        registry.register(
            ToolRegistration(
                tool=exa_tools_by_name[tool_name],
                source="mcp:exa",
                allowed_roles=(
                    EXA_ALLOWED_ROLES[tool_name]
                ),
                timeout_seconds=(
                    EXA_TOOL_TIMEOUT_SECONDS
                ),
            )
        )

    return registry