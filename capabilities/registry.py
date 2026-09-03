
"""
这个 registry.py 负责：

自动找到所有本地工具文件。
读取每个工具文件登记的 TOOL_REGISTRATIONS。
检查登记内容。
按 Agent 身份，把它有权限使用的工具发给它。

告诉程序：本地工具都放在 capabilities/local_tools/ 文件夹里。

"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Iterable

from langchain_core.tools import BaseTool

from .contracts import AgentRole, ToolRegistration


LOCAL_TOOLS_PACKAGE = "capabilities.local_tools"


class ToolRegistry:
    """统一登记 Tool，并按照 Agent 角色发放最小工具集合。"""

    def __init__(self) -> None:
        self._registrations: dict[str, ToolRegistration] = {}

    def register(self, registration: ToolRegistration) -> None:
        if not isinstance(registration, ToolRegistration):
            raise TypeError("只能注册 ToolRegistration。")

        tool_name = registration.tool.name

        if tool_name in self._registrations:
            raise ValueError(f"Tool 名称重复：{tool_name}")

        self._registrations[tool_name] = registration

    def get_registration(
        self,
        tool_name: str,
    ) -> ToolRegistration:
        try:
            return self._registrations[tool_name]
        except KeyError as exc:
            raise KeyError(f"Tool 尚未注册：{tool_name}") from exc

    def tools_for(self, role: AgentRole) -> list[BaseTool]:
        if not isinstance(role, AgentRole):
            raise TypeError("role 必须是 AgentRole。")

        return [
            registration.tool
            for _, registration in sorted(
                self._registrations.items()
            )
            if role in registration.allowed_roles
        ]

    def manifest(self) -> list[dict[str, object]]:
        return [
            {
                "name": registration.tool.name,
                "description": registration.tool.description,
                "source": registration.source,
                "allowed_roles": [
                    role.value
                    for role in sorted(
                        registration.allowed_roles,
                        key=lambda role: role.value,
                    )
                ],
                "timeout_seconds": registration.timeout_seconds,
            }
            for _, registration in sorted(
                self._registrations.items()
            )
        ]

    def __len__(self) -> int:
        return len(self._registrations)


def discover_local_tool_registrations(
    package_name: str = LOCAL_TOOLS_PACKAGE,
) -> tuple[ToolRegistration, ...]:
    """扫描本地插件包并读取每个模块的注册信息。"""

    package = importlib.import_module(package_name)
    package_path = getattr(package, "__path__", None)

    if package_path is None:
        raise TypeError(f"{package_name} 不是可扫描的 Python 包。")

    registrations: list[ToolRegistration] = []

    module_infos = sorted(
        pkgutil.iter_modules(
            package_path,
            prefix=f"{package.__name__}.",
        ),
        key=lambda module_info: module_info.name,
    )

    for module_info in module_infos:
        short_name = module_info.name.rsplit(".", 1)[-1]

        if module_info.ispkg or short_name.startswith("_"):
            continue

        try:
            module = importlib.import_module(module_info.name)
        except Exception as exc:
            raise RuntimeError(
                f"导入本地 Tool 模块失败：{module_info.name}"
            ) from exc

        raw_registrations = getattr(
            module,
            "TOOL_REGISTRATIONS",
            None,
        )

        if raw_registrations is None:
            raise ValueError(
                f"{module_info.name} 没有导出 "
                "TOOL_REGISTRATIONS。"
            )

        if (
            isinstance(raw_registrations, (str, bytes))
            or not isinstance(raw_registrations, Iterable)
        ):
            raise TypeError(
                f"{module_info.name}.TOOL_REGISTRATIONS "
                "必须是可迭代对象。"
            )

        module_registrations = tuple(raw_registrations)

        if not module_registrations:
            raise ValueError(
                f"{module_info.name}.TOOL_REGISTRATIONS "
                "不能为空。"
            )

        for index, registration in enumerate(
            module_registrations
        ):
            if not isinstance(registration, ToolRegistration):
                raise TypeError(
                    f"{module_info.name}.TOOL_REGISTRATIONS"
                    f"[{index}] 不是 ToolRegistration。"
                )

            registrations.append(registration)

    return tuple(registrations)


def build_local_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()

    for registration in discover_local_tool_registrations():
        registry.register(registration)

    return registry