import unittest

from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, ToolMessage

from agents.explorer.agent import (
    force_explorer_report_submission,
)


def model_response(*tool_names: str) -> ModelResponse:
    tool_calls = [
        {
            "name": tool_name,
            "args": {},
            "id": f"call-{index}",
            "type": "tool_call",
        }
        for index, tool_name in enumerate(
            tool_names,
            start=1,
        )
    ]

    return ModelResponse(
        result=[
            AIMessage(
                content=(
                    "plain answer"
                    if not tool_calls
                    else ""
                ),
                tool_calls=tool_calls,
            )
        ]
    )


def request_with_messages(
    messages: list[ToolMessage] | None = None,
) -> ModelRequest:
    return ModelRequest(
        model=object(),
        messages=list(messages or []),
    )


def selected_tool_name(request: ModelRequest) -> str | None:
    choice = request.tool_choice

    if not isinstance(choice, dict):
        return None

    function = choice.get("function")

    if not isinstance(function, dict):
        return None

    name = function.get("name")
    return name if isinstance(name, str) else None


def tool_message(
    name: str,
    index: int,
    *,
    status: str = "success",
    artifact: object | None = None,
) -> ToolMessage:
    return ToolMessage(
        content=f"result-{index}",
        tool_call_id=f"call-{index}",
        name=name,
        status=status,
        artifact=artifact,
    )


class ExplorerResearchMiddlewareTests(unittest.TestCase):
    def test_allows_one_research_call_when_two_attempts_exist(self) -> None:
        request = request_with_messages(
            [
                tool_message("web_search_exa", 1),
                tool_message("web_fetch_exa", 2),
            ]
        )

        def handler(current_request: ModelRequest) -> ModelResponse:
            if selected_tool_name(current_request):
                return model_response("submit_explorer_report")
            return model_response("web_fetch_exa")

        response = force_explorer_report_submission.wrap_model_call(
            request,
            handler,
        )

        self.assertEqual(
            ["web_fetch_exa"],
            [
                call["name"]
                for call in response.result[-1].tool_calls
            ],
        )

    def test_forces_report_after_three_research_attempts(self) -> None:
        request = request_with_messages(
            [
                tool_message("web_search_exa", 1),
                tool_message("web_fetch_exa", 2),
                tool_message("web_search_exa", 3),
            ]
        )

        response = force_explorer_report_submission.wrap_model_call(
            request,
            self._research_unless_report_is_forced,
        )

        self.assertEqual(
            ["submit_explorer_report"],
            [
                call["name"]
                for call in response.result[-1].tool_calls
            ],
        )

    def test_failed_research_calls_consume_the_budget(self) -> None:
        request = request_with_messages(
            [
                tool_message(
                    "web_search_exa",
                    1,
                    status="error",
                ),
                tool_message(
                    "web_fetch_exa",
                    2,
                    status="error",
                ),
                tool_message(
                    "web_search_exa",
                    3,
                    status="error",
                ),
            ]
        )

        response = force_explorer_report_submission.wrap_model_call(
            request,
            self._research_unless_report_is_forced,
        )

        self.assertEqual(
            "submit_explorer_report",
            response.result[-1].tool_calls[0]["name"],
        )

    def test_plain_answer_is_replaced_with_a_forced_report(self) -> None:
        def handler(current_request: ModelRequest) -> ModelResponse:
            forced_name = selected_tool_name(current_request)
            return (
                model_response(forced_name)
                if forced_name
                else model_response()
            )

        response = force_explorer_report_submission.wrap_model_call(
            request_with_messages(),
            handler,
        )

        self.assertEqual(
            "submit_explorer_report",
            response.result[-1].tool_calls[0]["name"],
        )

    def test_parallel_calls_are_replaced_with_one_report(self) -> None:
        def handler(current_request: ModelRequest) -> ModelResponse:
            forced_name = selected_tool_name(current_request)
            return (
                model_response(forced_name)
                if forced_name
                else model_response(
                    "web_search_exa",
                    "web_fetch_exa",
                )
            )

        response = force_explorer_report_submission.wrap_model_call(
            request_with_messages(),
            handler,
        )

        self.assertEqual(
            ["submit_explorer_report"],
            [
                call["name"]
                for call in response.result[-1].tool_calls
            ],
        )

    def test_successful_report_disables_further_tool_calls(self) -> None:
        request = request_with_messages(
            [
                tool_message(
                    "submit_explorer_report",
                    1,
                    artifact={"plan_approved": True},
                )
            ]
        )

        def handler(current_request: ModelRequest) -> ModelResponse:
            return (
                model_response()
                if current_request.tool_choice == "none"
                else model_response("web_search_exa")
            )

        response = force_explorer_report_submission.wrap_model_call(
            request,
            handler,
        )

        self.assertEqual([], response.result[-1].tool_calls)

    @staticmethod
    def _research_unless_report_is_forced(
        request: ModelRequest,
    ) -> ModelResponse:
        forced_name = selected_tool_name(request)
        return (
            model_response(forced_name)
            if forced_name
            else model_response("web_search_exa")
        )


if __name__ == "__main__":
    unittest.main()
