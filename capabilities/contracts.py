"""
Tool（工具）进入系统前的“登记表 + 安检规则”
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from langchain_core.tools import BaseTool

class AgentRole(str, Enum):
    MAIN_AGENT = "main_agent"
    PLANNER="planner"
    EXPLORER="explorer"
    IMPLEMENTER="implementer"
    REVIEWER="reviewer"
    TESTER="tester"
    VERIFIER="verifier"

@dataclass(frozen=True,slots=True)
class ToolRegistration:
    """一个 Tool 进入中央注册表前必须满足的契约。"""

    tool: BaseTool
    source: str
    allowed_roles: frozenset[AgentRole]
    timeout_seconds: float

    """
    tool：具体是什么工具，比如“查天气”“读文件”“统计文本”的工具对象。
    source：工具从哪里来的，例如 "local_tools"、"mcp_server"。
    allowed_roles：哪些角色可以使用它。frozenset 表示这是一个不可修改的角色集合，注册后不能偷偷增减权限。
    timeout_seconds：工具最长允许执行几秒，超时就停止或报错。
    """
    def __post_init__(self) -> None:
        if not isinstance(self.tool, BaseTool):
            raise TypeError("tool 必须是 LangChain BaseTool。")

        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("Tool 来源不能为空。")

        object.__setattr__(self, "source", self.source.strip())

        try:
            roles = frozenset(self.allowed_roles)
        except TypeError as exc:
            raise TypeError("allowed_roles 必须是可迭代的角色集合。") from exc

        if not roles:
            raise ValueError("Tool 至少要授权给一个 Agent 角色。")

        if any(not isinstance(role, AgentRole) for role in roles):
            raise TypeError("allowed_roles 中存在非法 Agent 角色。")

        object.__setattr__(self, "allowed_roles", roles)

        if isinstance(self.timeout_seconds, bool):
            raise ValueError("Tool 超时时间必须是正数。")

        try:
            timeout = float(self.timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("Tool 超时时间必须是数字。") from exc

        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("Tool 超时时间必须是有限正数。")

        object.__setattr__(self, "timeout_seconds", timeout)