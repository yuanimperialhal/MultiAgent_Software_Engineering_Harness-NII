import unittest

from workflow.node_handlers import planner
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

class ConversationSummaryTests(unittest.TestCase):
    def test_old_requests_enter_summary_batch(
        self,
    ) -> None:
        oldest_request = (
            "第一轮：" + "A" * 600
        )
        second_request = (
            "第二轮：" + "B" * 600
        )
        third_request = "第三轮：增加图表"
        current_request = "本轮：修改颜色"

        conversation_history = [
            oldest_request,
            second_request,
            third_request,
            current_request,
        ]

        split_history = getattr(
            planner,
            "split_history_for_summary",
            None,
        )

        self.assertTrue(
            callable(split_history),
            "尚未实现历史压缩分组函数",
        )

        (
            summary_batch,
            recent_requests,
            next_summarized_count,
        ) = split_history(
            conversation_history=conversation_history,
            summarized_request_count=0,
            summary_trigger_chars=1000,
            recent_request_count=2,
        )

        self.assertEqual(
            summary_batch,
            [oldest_request],
        )
        self.assertEqual(
            recent_requests,
            [
                second_request,
                third_request,
            ],
        )
        self.assertEqual(
            next_summarized_count,
            1,
        )

    def test_planner_compresses_old_history_before_planning(
        self,
    ) -> None:
        oldest_request = "第一轮：" + "A" * 600
        second_request = "第二轮：" + "B" * 600
        third_request = "第三轮：增加图表"
        current_request = "本轮：修改颜色"

        fake_model = MagicMock()
        fake_model.invoke.return_value = AIMessage(
            content="长期摘要：第一轮提出了基础需求。"
        )

        fake_planner_agent = MagicMock()
        fake_planner_agent.invoke.return_value = {
            "messages": [
                AIMessage(content="新的执行计划")
            ]
        }

        state = {
            "conversation_history": [
                oldest_request,
                second_request,
                third_request,
                current_request,
            ],
            "conversation_summary": "",
            "summarized_request_count": 0,
            "user_request": current_request,
            "plan_revision": 0,
            "replan_count": 0,
        }

        with patch.object(
            planner,
            "build_planner_agent",
            return_value=fake_planner_agent,
        ):
            planner_node = planner.build_planner_node(
                fake_model
            )
            result = planner_node(state)

        self.assertEqual(
            result["conversation_summary"],
            "长期摘要：第一轮提出了基础需求。",
        )
        self.assertEqual(
            result["summarized_request_count"],
            1,
        )

        planner_payload = (
            fake_planner_agent.invoke.call_args.args[0]
        )
        planner_content = (
            planner_payload["messages"][0]["content"]
        )

        self.assertIn(
            "长期摘要：第一轮提出了基础需求。",
            planner_content,
        )
        self.assertIn(second_request, planner_content)
        self.assertIn(third_request, planner_content)
        self.assertNotIn(oldest_request, planner_content)


if __name__ == "__main__":
    unittest.main()