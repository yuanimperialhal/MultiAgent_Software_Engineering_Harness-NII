from collections.abc import Callable, Sequence
from langchain_core.tools import BaseTool
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from agents.main_agent import build_main_agent
from workflow.state import MultiAgentState

from .common import get_last_reply


GraphNode = Callable[[MultiAgentState], dict[str, Any]]


def build_main_nodes(
    model: BaseChatModel,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, GraphNode]:
    """创建 Main Agent 对应的两个 LangGraph Node。"""
    main_agent = build_main_agent(model, tools=tools)

    def planning_main_node(state: MultiAgentState) -> dict[str, Any]:
        """接收 ExplorerReport，确定规划阶段下一站。"""
        replan_count = state.get("replan_count", 0)
        max_replans = state.get("max_replans", 0)

        if state["plan_approved"]:
            next_role = "implementer"
        elif replan_count >= max_replans:
            next_role = None
        else:
            next_role = "planner"

        result = main_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            f"[当前计划版本]\n"
                            f"{state['plan_revision']}\n\n"
                            f"[ExplorerReport]\n"
                            f"{state['explorer_report']}\n\n"
                            f"[已重新规划次数]\n"
                            f"{replan_count}/{max_replans}\n\n"
                            "请接收报告并说明下一站。"
                        ),
                    }
                ]
            }
        )

        instruction = get_last_reply(result)

        print("\n=== Main Agent Node：确定规划下一站 ===")
        print(instruction)

        return {
            "main_instruction": instruction,
            "next_role": next_role,
        }

    def review_main_node(state: MultiAgentState) -> dict[str, Any]:
        """接收 ReviewerReport，确定审查阶段下一站。"""

        reviewer_report = state.get("reviewer_report")

        if reviewer_report is None:
            raise ValueError("Review Main 没有收到 ReviewerReport。")

        review_repair_count = state.get("review_repair_count", 0)
        max_repairs = state.get("max_review_repairs", 0)

        if reviewer_report.passed:
            next_role = "tester"
            next_phase = "testing"
            next_status = "running"
        elif review_repair_count >= max_repairs:
            next_role = None
            next_phase = "failed"
            next_status = "failed"
        else:
            review_repair_count += 1
            next_role = "implementer"
            next_phase = "implementing"
            next_status = "running"

        report_json = reviewer_report.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )

        result = main_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            f"[当前代码版本]\n"
                            f"{state['artifact_revision']}\n\n"
                            f"[ReviewerReport]\n"
                            f"{report_json}\n\n"
                            f"[修复次数]\n"
                            f"{review_repair_count}/{max_repairs}\n\n"
                            f"[Python 已确定的下一站]\n"
                            f"{next_role}\n\n"
                            "请接收 Reviewer 报告，"
                            "并说明下一步进入哪个角色。"
                        ),
                    }
                ]
            }
        )

        instruction = get_last_reply(result)

        print("\n=== Main Agent Node：确定 Reviewer 下一站 ===")
        print(instruction)

        return {
            "main_instruction": instruction,
            "review_repair_count": review_repair_count,
            "next_role": next_role,
            "phase": next_phase,
            "status": next_status,
        }

    def test_main_node(state: MultiAgentState) -> dict[str, Any]:
        """接收 TesterReport，确定测试阶段下一站。"""

        tester_report = state.get("tester_report")

        if tester_report is None:
            raise ValueError("Test Main 没有收到 TesterReport。")

        tester_repair_count = state.get("tester_repair_count", 0)
        max_repairs = state.get("max_tester_repairs", 0)

        if tester_report.passed:
            next_role = "verifier"
            next_phase = "verifying"
            next_status = "running"

        elif tester_repair_count >= max_repairs:
            next_role = None
            next_phase = "failed"
            next_status = "failed"

        else:
            tester_repair_count += 1
            next_role = "implementer"
            next_phase = "implementing"
            next_status = "running"

        report_json = tester_report.model_dump_json(indent=2,ensure_ascii=False)

        result = main_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            f"[当前代码版本]\n"
                            f"{state['artifact_revision']}\n\n"
                            f"[TesterReport]\n"
                            f"{report_json}\n\n"
                            f"[修复次数]\n"
                            f"{tester_repair_count}/{max_repairs}\n\n"
                            f"[Python 已确定的下一站]\n"
                            f"{next_role}\n\n"
                            "请接收 Tester 报告，"
                            "并说明下一步进入哪个角色。"
                        ),
                    }
                ]
            }
        )

        instruction = get_last_reply(result)

        print("\n=== Main Agent Node：确定 Tester 下一站 ===")
        print(instruction)

        return {
            "main_instruction": instruction,
            "tester_repair_count": tester_repair_count,
            "next_role": next_role,
            "phase": next_phase,
            "status": next_status,
        }

    def verifier_main_node(state: MultiAgentState) -> dict[str, Any]:
        """接收 VerifierReport，确定最终核验阶段下一站。"""

        verifier_report = state.get("verifier_report")

        if verifier_report is None:
            raise ValueError("Verifier Main 没有收到 VerifierReport。")

        verifier_repair_count = state.get("verifier_repair_count", 0)
        max_repairs = state.get("max_verifier_repairs", 0)

        if verifier_report.passed:
            next_role = None
            next_phase = "completed"
            next_status = "completed"
        elif verifier_repair_count >= max_repairs:
            next_role = None
            next_phase = "failed"
            next_status = "failed"
        else:
            verifier_repair_count += 1
            next_role = "implementer"
            next_phase = "implementing"
            next_status = "running"

        report_json = verifier_report.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )

        result = main_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            f"[当前代码版本]\n"
                            f"{state['artifact_revision']}\n\n"
                            f"[VerifierReport]\n"
                            f"{report_json}\n\n"
                            f"[修复次数]\n"
                            f"{verifier_repair_count}/{max_repairs}\n\n"
                            f"[Python 已确定的下一站]\n"
                            f"{next_role}\n\n"
                            "请接收 Verifier 报告，并说明任务完成、"
                            "返回 Implementer，还是达到上限后失败。"
                        ),
                    }
                ]
            }
        )

        instruction = get_last_reply(result)

        print("\n=== Main Agent Node：确定 Verifier 下一站 ===")
        print(instruction)

        return {
            "main_instruction": instruction,
            "verifier_repair_count": verifier_repair_count,
            "next_role": next_role,
            "phase": next_phase,
            "status": next_status,
        }

    return {
        "planning_main_node": planning_main_node,
        "review_main_node": review_main_node,
        "test_main_node": test_main_node,
        "verifier_main_node": verifier_main_node,
    }
