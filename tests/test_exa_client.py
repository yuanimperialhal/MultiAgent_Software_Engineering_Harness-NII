import asyncio
import unittest
from unittest.mock import patch

from langchain_core.tools import StructuredTool

from capabilities.remote_tools.exa.client import (
    load_exa_remote_tools,
)


def make_remote_tool(name: str) -> StructuredTool:
    def invoke_remote(**arguments: object) -> str:
        return str(arguments)

    return StructuredTool.from_function(
        func=invoke_remote,
        name=name,
        description=f"Remote tool {name}",
        args_schema={
            "type": "object",
            "properties": {},
        },
        infer_schema=False,
    )


class FakeMCPClient:
    tools = []
    error: Exception | None = None
    delay_seconds = 0.0

    def __init__(self, connections, *, handle_tool_errors):
        self.connections = connections
        self.handle_tool_errors = handle_tool_errors

    async def get_tools(self, *, server_name: str):
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        return list(self.tools)


class ExaClientTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeMCPClient.tools = []
        FakeMCPClient.error = None
        FakeMCPClient.delay_seconds = 0.0

    def test_keeps_only_the_two_whitelisted_tools(self) -> None:
        FakeMCPClient.tools = [
            make_remote_tool("web_search_exa"),
            make_remote_tool("web_fetch_exa"),
            make_remote_tool("dangerous_remote_shell"),
        ]

        tools = self._load_tools()

        self.assertEqual(
            {"web_search_exa", "web_fetch_exa"},
            set(tools),
        )

    def test_rejects_missing_whitelisted_tool(self) -> None:
        FakeMCPClient.tools = [
            make_remote_tool("web_search_exa"),
        ]

        with self.assertRaisesRegex(RuntimeError, "web_fetch_exa"):
            self._load_tools()

    def test_rejects_duplicate_whitelisted_tool(self) -> None:
        FakeMCPClient.tools = [
            make_remote_tool("web_search_exa"),
            make_remote_tool("web_search_exa"),
            make_remote_tool("web_fetch_exa"),
        ]

        with self.assertRaisesRegex(RuntimeError, "重名"):
            self._load_tools()

    def test_reports_connection_failure(self) -> None:
        FakeMCPClient.error = OSError("network unavailable")

        with self.assertRaisesRegex(ConnectionError, "无法连接 Exa MCP"):
            self._load_tools()

    def test_reports_connection_timeout(self) -> None:
        FakeMCPClient.delay_seconds = 0.05

        with self.assertRaisesRegex(TimeoutError, "加载工具超时"):
            self._load_tools(timeout=0.001)

    def _load_tools(self, timeout: float = 1.0):
        with patch(
            "capabilities.remote_tools.exa.client.MultiServerMCPClient",
            FakeMCPClient,
        ):
            return asyncio.run(
                load_exa_remote_tools(
                    connection_timeout_seconds=timeout
                )
            )


if __name__ == "__main__":
    unittest.main()
