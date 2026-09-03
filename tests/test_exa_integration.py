import os
import re
import unittest

from dotenv import load_dotenv

from capabilities.remote_tools.exa import build_exa_sync_tools
from capabilities.remote_tools.exa.policy import UNTRUSTED_WEB_PREFIX


@unittest.skipUnless(
    os.getenv("RUN_EXA_INTEGRATION") == "1",
    "set RUN_EXA_INTEGRATION=1 to call the real Exa MCP service",
)
class ExaIntegrationTests(unittest.TestCase):
    def test_search_result_url_can_be_fetched(self) -> None:
        load_dotenv()
        tools = {
            tool.name: tool
            for tool in build_exa_sync_tools()
        }

        search_result = tools["web_search_exa"].invoke(
            {
                "query": "official Python asyncio documentation",
                "numResults": 1,
            }
        )
        url_match = re.search(
            r"URL: (https?://[^\s]+)",
            search_result,
        )

        self.assertIsNotNone(url_match)
        selected_url = url_match.group(1)

        fetch_result = tools["web_fetch_exa"].invoke(
            {
                "urls": [selected_url],
                "maxCharacters": 500,
            }
        )

        self.assertTrue(fetch_result.startswith(UNTRUSTED_WEB_PREFIX))
        self.assertIn("asyncio", fetch_result.lower())


if __name__ == "__main__":
    unittest.main()
