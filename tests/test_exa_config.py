import os
import unittest
from unittest.mock import patch

from capabilities.remote_tools.exa.config import (
    EXA_MCP_URL,
    build_exa_connection,
    validate_positive_timeout,
)


class ExaConfigTests(unittest.TestCase):
    def test_builds_anonymous_http_connection_without_headers(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            connection = build_exa_connection()

        self.assertEqual("http", connection["transport"])
        self.assertEqual(EXA_MCP_URL, connection["url"])
        self.assertNotIn("headers", connection)

    def test_sends_api_key_only_in_request_header(self) -> None:
        connection = build_exa_connection(api_key="secret-value")

        self.assertEqual(
            {"x-api-key": "secret-value"},
            connection["headers"],
        )
        self.assertNotIn("secret-value", str(connection["url"]))

    def test_rejects_invalid_timeout_values(self) -> None:
        invalid_values = (0, -1, float("inf"), float("nan"), True)

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "有限正数"):
                    validate_positive_timeout(
                        value,
                        field_name="timeout",
                    )


if __name__ == "__main__":
    unittest.main()
