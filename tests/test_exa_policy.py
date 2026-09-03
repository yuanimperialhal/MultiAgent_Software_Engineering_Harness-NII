import unittest

from capabilities.remote_tools.exa.config import (
    MAX_REMOTE_RESULT_CHARACTERS,
)
from capabilities.remote_tools.exa.policy import (
    UNTRUSTED_WEB_PREFIX,
    format_exa_result,
    validate_exa_arguments,
)


class ExaPolicyTests(unittest.TestCase):
    def test_normalizes_search_query_and_result_count(self) -> None:
        result = validate_exa_arguments(
            "web_search_exa",
            {"query": "  robot MCP  ", "numResults": 3.0},
        )

        self.assertEqual(
            {"query": "robot MCP", "numResults": 3},
            result,
        )

    def test_rejects_empty_or_oversized_search(self) -> None:
        invalid_queries = ("", " ", "x" * 501)

        for query in invalid_queries:
            with self.subTest(query_length=len(query)):
                with self.assertRaises(ValueError):
                    validate_exa_arguments(
                        "web_search_exa",
                        {"query": query},
                    )

    def test_rejects_out_of_range_search_result_count(self) -> None:
        for value in (0, 11, 1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_exa_arguments(
                        "web_search_exa",
                        {"query": "robot MCP", "numResults": value},
                    )

    def test_accepts_only_bounded_http_fetch_requests(self) -> None:
        result = validate_exa_arguments(
            "web_fetch_exa",
            {
                "urls": [" https://example.com/manual "],
                "maxCharacters": 3_000.0,
            },
        )

        self.assertEqual(
            {
                "urls": ["https://example.com/manual"],
                "maxCharacters": 3_000,
            },
            result,
        )

    def test_rejects_invalid_fetch_urls_and_limits(self) -> None:
        invalid_requests = (
            {"urls": []},
            {"urls": ["file:///etc/passwd"]},
            {"urls": ["https://example.com"] * 4},
            {"urls": ["https://example.com"], "maxCharacters": 8_001},
        )

        for arguments in invalid_requests:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    validate_exa_arguments(
                        "web_fetch_exa",
                        arguments,
                    )

    def test_rejects_non_whitelisted_tool(self) -> None:
        with self.assertRaisesRegex(ValueError, "非白名单"):
            validate_exa_arguments(
                "dangerous_remote_shell",
                {},
            )

    def test_marks_content_as_untrusted_and_extracts_text_blocks(self) -> None:
        result = format_exa_result(
            [
                {"type": "text", "text": "first"},
                {"type": "image", "url": "https://example.com/a.png"},
                {"type": "text", "text": "second"},
            ]
        )

        self.assertEqual(
            f"{UNTRUSTED_WEB_PREFIX}first\n\nsecond",
            result,
        )

    def test_truncates_oversized_remote_result(self) -> None:
        result = format_exa_result(
            "x" * (MAX_REMOTE_RESULT_CHARACTERS + 100)
        )

        self.assertEqual(MAX_REMOTE_RESULT_CHARACTERS, len(result))
        self.assertTrue(result.endswith("...[Exa MCP result truncated]"))


if __name__ == "__main__":
    unittest.main()
