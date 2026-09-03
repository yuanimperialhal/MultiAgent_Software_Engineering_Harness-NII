import unittest

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from workflow.state import MultiAgentState


def keep_history(
    state: MultiAgentState,
) -> dict[str, object]:
    return {}


def build_history_graph():
    builder = StateGraph(MultiAgentState)

    builder.add_node(
        "keep_history",
        keep_history,
    )
    builder.add_edge(START, "keep_history")
    builder.add_edge("keep_history", END)

    return builder.compile(
        checkpointer=InMemorySaver()
    )


class ConversationHistoryTests(unittest.TestCase):
    def test_same_thread_accumulates_history(
        self,
    ) -> None:
        graph = build_history_graph()

        thread_a = {
            "configurable": {
                "thread_id": "thread-A",
            }
        }

        graph.invoke(
            {
                "conversation_history": [
                    "开发记账软件"
                ]
            },
            config=thread_a,
        )

        result = graph.invoke(
            {
                "conversation_history": [
                    "增加导出功能"
                ]
            },
            config=thread_a,
        )

        self.assertEqual(
            result["conversation_history"],
            [
                "开发记账软件",
                "增加导出功能",
            ],
        )

    def test_different_threads_are_isolated(
        self,
    ) -> None:
        graph = build_history_graph()

        thread_a = {
            "configurable": {
                "thread_id": "thread-A",
            }
        }
        thread_b = {
            "configurable": {
                "thread_id": "thread-B",
            }
        }

        graph.invoke(
            {
                "conversation_history": [
                    "A 的机器人任务"
                ]
            },
            config=thread_a,
        )

        result_b = graph.invoke(
            {
                "conversation_history": [
                    "B 的机器人任务"
                ]
            },
            config=thread_b,
        )

        self.assertEqual(
            result_b["conversation_history"],
            ["B 的机器人任务"],
        )


if __name__ == "__main__":
    unittest.main()