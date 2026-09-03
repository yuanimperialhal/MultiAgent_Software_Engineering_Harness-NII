# 管理连接配置和安全上限

import os
from math import isfinite

EXA_MCP_URL=(
    "https://mcp.exa.ai/mcp?"
    "tools=web_search_exa,web_fetch_exa"
)

EXA_TOOL_NAMES = (
    "web_search_exa",
    "web_fetch_exa",
)

EXA_TOOL_NAME_SET = frozenset(EXA_TOOL_NAMES)

DEFAULT_CONNECTION_TIMEOUT_SECONDS = 20.0
DEFAULT_TOOL_TIMEOUT_SECONDS = 20.0

MAX_SEARCH_QUERY_CHARACTERS = 500
MAX_SEARCH_RESULTS = 10
MAX_FETCH_URLS = 3
MAX_FETCH_CHARACTERS_PER_URL = 8000
MAX_REMOTE_RESULT_CHARACTERS = 20000

def validate_positive_timeout(
    value: object,
    *,
    field_name: str,
) -> float:
    """确保超时时间是有限正数。"""

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} 必须是有限正数。"
        )

    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} 必须是有限正数。"
        ) from exc

    if not isfinite(timeout) or timeout <= 0:
        raise ValueError(
            f"{field_name} 必须是有限正数。"
        )

    return timeout


def build_exa_connection(
    *,
    api_key: str | None = None,
    timeout_seconds: float = (
        DEFAULT_CONNECTION_TIMEOUT_SECONDS
    ),
) -> dict[str, object]:
    """生成 MultiServerMCPClient 使用的连接配置。"""

    timeout = validate_positive_timeout(
        timeout_seconds,
        field_name="timeout_seconds",
    )

    selected_key = (
        api_key
        if api_key is not None
        else os.getenv("EXA_API_KEY", "")
    ).strip()

    connection: dict[str, object] = {
        "transport": "http",
        "url": EXA_MCP_URL,
        "timeout": timeout,
        "sse_read_timeout": timeout,
    }

    if selected_key:
        connection["headers"] = {
            "x-api-key": selected_key,
        }

    return connection

