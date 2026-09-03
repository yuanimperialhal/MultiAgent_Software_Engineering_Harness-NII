from collections.abc import Callable, Sequence
from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Any

from agents.explorer import build_explorer_agent,extract_explorer_report

from workflow.state import MultiAgentState

from .common import get_executed_tool_names

GraphNode=Callable[[MultiAgentState], dict[str,Any]]

def build_explorer_node(
        model: BaseChatModel,
        tools: Sequence[BaseTool] | None = None) -> GraphNode:
    """创建 Explorer Agent 对应的 LangGraph Node。"""
    explorer_agent = build_explorer_agent(model, tools=tools)
    
    def explorer_node(state: MultiAgentState) -> dict[str, Any]:
        result = explorer_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            f"[当前计划版本]\n"
                            f"{state['plan_revision']}\n\n"
                            f"[当前计划]\n"
                            f"{state['plan']}\n\n"
                            f"[项目快照]\n"
                            f"{state['project_snapshot']}\n\n"
                            "请检查计划是否符合项目现状，"
                            "然后提交 ExplorerReport。"
                        ),
                    }
                ]
            }
        )

        executed_tools = get_executed_tool_names(result)

        print(
            "Explorer 工具调用："
            + (
                ", ".join(executed_tools)
                if executed_tools
                else "无"
            )
        )

        report = extract_explorer_report(result)

        if report.plan_revision != state['plan_revision']:
            raise ValueError("ExplorerReport 的 plan_revision 与当前计划版本不一致。")

        print(f"\n=== Explorer Node：检查第{report.plan_revision} 版计划 ===")
        print(report.model_dump_json(indent=2, ensure_ascii=False))

        return {
            "explorer_report": report.model_dump_json(indent=2, ensure_ascii=False),
            "plan_approved": report.plan_approved,
            "replan_feedback": report.replan_feedback,
            "phase":"exploring",
            "next_role": "main_agent",
        }

    return explorer_node