from collections.abc import Callable, Sequence
from langchain_core.tools import BaseTool
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from agents.reviewer import build_reviewer_agent, extract_reviewer_report

from workflow.state import MultiAgentState


GraphNode = Callable[[MultiAgentState], dict[str, Any]]

def build_reviewer_node(
    model: BaseChatModel,
    tools: Sequence[BaseTool] | None = None,
) -> GraphNode:
    """创建 Reviewer Agent 对应的 LangGraph Node。"""
    reviewer_agent = build_reviewer_agent(model, tools=tools)

    def reviewer_node(state: MultiAgentState) -> dict[str, Any]:
        """审查当前代码，并返回结构化 ReviewerReport。"""
        result = reviewer_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            f"[已批准计划]\n"
                            f"{state['plan']}\n\n"
                            f"[ExplorerReport]\n"
                            f"{state['explorer_report']}\n\n"
                            f"[当前代码版本]\n"
                            f"{state['artifact_revision']}\n\n"
                            f"[最新项目快照]\n"
                            f"{state['project_snapshot']}\n\n"
                            "请审查当前代码是否符合用户任务和计划，"
                            "并提交 ReviewerReport。\n"
                            "你只能进行代码审查；"
                            "没有执行测试时，不能声称测试已经通过。"
                        ),
                    }
                ]
            }            
        )

        reviewer_report = extract_reviewer_report(result)

        if reviewer_report.revision != state["artifact_revision"]:
            raise ValueError(
                "ReviewerReport 的 artifact_revision "
                "与当前代码版本不一致。"
            )
        print("\n=== Reviewer Node：审查最新代码 ===")
        print(reviewer_report.model_dump_json(indent=2,ensure_ascii=False,))
        return {
            "reviewer_report": reviewer_report,
            "phase": "reviewing",
            "status": "running",
            "next_role": "main_agent",
        }

    return reviewer_node