#连接 Exa、发现并过滤 Tool

import asyncio
from collections import Counter

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import (
    MultiServerMCPClient,
)

from .config import (
    DEFAULT_CONNECTION_TIMEOUT_SECONDS,
    EXA_TOOL_NAME_SET,
    build_exa_connection,
    validate_positive_timeout,
)


async def load_exa_remote_tools(
    *,
    api_key: str | None = None,
    connection_timeout_seconds: float = (
        DEFAULT_CONNECTION_TIMEOUT_SECONDS
    ),
) -> dict[str, BaseTool]:
    """连接 Exa，并只返回白名单内的 Tool。"""

    timeout = validate_positive_timeout(
        connection_timeout_seconds,
        field_name="connection_timeout_seconds",
    )

    client = MultiServerMCPClient(
        {
            "exa": build_exa_connection(
                api_key=api_key,
                timeout_seconds=timeout,
            )
        },
        handle_tool_errors=False,
    )

    try:
        remote_tools = await asyncio.wait_for(
            client.get_tools(server_name="exa"),
            timeout=timeout,
        )
    except TimeoutError as exc:
        raise TimeoutError(
            "连接 Exa MCP 并加载工具超时。"
        ) from exc
    except Exception as exc:
        raise ConnectionError(
            "无法连接 Exa MCP 或加载远程工具。"
        ) from exc

    allowed_tools = [
        remote_tool
        for remote_tool in remote_tools
        if remote_tool.name in EXA_TOOL_NAME_SET
    ]

    name_counts = Counter(
        remote_tool.name
        for remote_tool in allowed_tools
    )

    duplicate_names = {
        name
        for name, count in name_counts.items()
        if count > 1
    }

    if duplicate_names:
        names = ", ".join(sorted(duplicate_names))
        raise RuntimeError(
            f"Exa MCP 返回重名工具：{names}"
        )

    tools_by_name = {
        remote_tool.name: remote_tool
        for remote_tool in allowed_tools
    }

    missing_names = (
        EXA_TOOL_NAME_SET
        - tools_by_name.keys()
    )

    if missing_names:
        names = ", ".join(sorted(missing_names))
        raise RuntimeError(
            f"Exa MCP 缺少白名单工具：{names}"
        )

    return tools_by_name