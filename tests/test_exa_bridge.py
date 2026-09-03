import asyncio
import unittest
from unittest.mock import patch

from langchain_core.tools import StructuredTool

from capabilities.remote_tools.exa.bridge import (
    build_exa_sync_tools,
    build_sync_proxy,
    invoke_mcp_tool_sync,
    run_coroutine_sync,
)
from capabilities.remote_tools.exa.policy import (
    UNTRUSTED_WEB_PREFIX,
)


def make_async_tool(
    name: str,
    *,
    delay_seconds: float = 0.0,
) -> StructuredTool:
    async def invoke_remote(**arguments: object):
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
        return [
            {
                "type": "text",
                "text": f"{name}:{arguments}",
            }
        ]

    return StructuredTool.from_function(
        coroutine=invoke_remote,
        name=name,
        description=f"Remote tool {name}",
        args_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
        infer_schema=False,
    )


class ExaBridgeTests(unittest.TestCase):
    def test_invokes_async_remote_tool_from_sync_code(self) -> None:
        remote_tool = make_async_tool("web_search_exa")

        result = invoke_mcp_tool_sync(
            remote_tool,
            {"query": "robot MCP"},
        )

        self.assertTrue(result.startswith(UNTRUSTED_WEB_PREFIX))
        self.assertIn("web_search_exa", result)
        self.assertIn("robot MCP", result)

    def test_reports_remote_tool_timeout(self) -> None:
        remote_tool = make_async_tool(
            "web_search_exa",
            delay_seconds=0.05,
        )

        with self.assertRaisesRegex(TimeoutError, "调用超时"):
            invoke_mcp_tool_sync(
                remote_tool,
                {"query": "robot MCP"},
                timeout_seconds=0.001,
            )

    def test_sync_proxy_preserves_remote_name_and_schema(self) -> None:
        remote_tool = make_async_tool("web_search_exa")

        proxy = build_sync_proxy(
            remote_tool,
            timeout_seconds=1.0,
        )

        self.assertEqual("web_search_exa", proxy.name)
        self.assertEqual(remote_tool.args_schema, proxy.args_schema)
        self.assertEqual("mcp:exa", proxy.metadata["source"])

    def test_builds_proxies_in_stable_order(self) -> None:
        remote_tools = {
            "web_search_exa": make_async_tool("web_search_exa"),
            "web_fetch_exa": self._make_fetch_tool(),
        }

        async def fake_load(**arguments):
            return remote_tools

        with patch(
            "capabilities.remote_tools.exa.bridge.load_exa_remote_tools",
            fake_load,
        ):
            proxies = build_exa_sync_tools()

        self.assertEqual(
            ["web_search_exa", "web_fetch_exa"],
            [proxy.name for proxy in proxies],
        )

    def test_rejects_sync_bridge_inside_running_event_loop(self) -> None:
        async def call_bridge() -> None:
            with self.assertRaisesRegex(RuntimeError, "事件循环"):
                run_coroutine_sync(
                    lambda: asyncio.sleep(0)
                )

        asyncio.run(call_bridge())

    @staticmethod
    def _make_fetch_tool() -> StructuredTool:
        async def fetch_remote(**arguments: object):
            return [{"type": "text", "text": str(arguments)}]

        return StructuredTool.from_function(
            coroutine=fetch_remote,
            name="web_fetch_exa",
            description="Fetch a webpage",
            args_schema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                "required": ["urls"],
            },
            infer_schema=False,
        )


if __name__ == "__main__":
    unittest.main()
