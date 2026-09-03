from collections.abc import Callable,Sequence
from langchain_core.tools import BaseTool
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from agents.verifier import build_verifier_agent, extract_verifier_report

from workflow.state import MultiAgentState


GraphNode = Callable[[MultiAgentState], dict[str, Any]]


def build_verifier_node(
    model: BaseChatModel,
    tools: Sequence[BaseTool] | None = None,
) -> GraphNode:
    """创建 Verifier Agent 对应的 LangGraph Node。"""
    verifier_agent = build_verifier_agent(model, tools=tools)

    def verifier_node(state: MultiAgentState) -> dict[str, Any]:
        reviewer_report = state.get("reviewer_report")
        tester_report = state.get("tester_report")

        if reviewer_report is None:
            raise ValueError("Verifier 没有收到 ReviewerReport。")
        if tester_report is None:
            raise ValueError("Verifier 没有收到 TesterReport。")


        reviewer_report_json = reviewer_report.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )
        tester_report_json = tester_report.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )

        result = verifier_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "[Main Agent 最终核验任务]\n"
                            "请核验当前版本是否真正满足"
                            "用户需求。\n\n"
                            "[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            "[当前代码版本]\n"
                            f"{state['artifact_revision']}\n\n"
                            "[当前项目快照]\n"
                            f"{state['project_snapshot']}\n\n"
                            "[ReviewerReport]\n"
                            f"{reviewer_report_json}\n\n"
                            "[TesterReport]\n"
                            f"{tester_report_json}\n\n"
                            "请逐项检查需求和证据，"
                            "然后提交 VerifierReport。"
                        ),
                    }
                ]
            }
        )

        verifier_report = extract_verifier_report(result)

        if verifier_report.revision != state["artifact_revision"]:
            raise ValueError(
                "VerifierReport 的 revision 与当前代码版本不一致。"
            )

        print("\n=== Verifier Node：最终核验 ===")
        print(verifier_report.model_dump_json(indent=2,ensure_ascii=False))

        return {
            "verifier_report": verifier_report,
            "phase": "verifying",
            "status": "running",
            "next_role": "main_agent",
        }

    return verifier_node
