from collections.abc import Callable,Sequence
from langchain_core.tools import BaseTool

from langchain_core.language_models.chat_models import BaseChatModel

from agents.planner import build_planner_agent
from workflow.state import MultiAgentState

from .common import get_last_reply,get_executed_tool_names



GraphNode=Callable[[MultiAgentState], dict[str, object]]

def split_history_for_summary(
    conversation_history: list[str],
    summarized_request_count: int,
    summary_trigger_chars: int=1000,
    recent_request_count: int=2,#这个参数指定了在生成摘要时，应该保留的最近用户请求的数量。它确保了在生成摘要时，最近的几个请求不会被压缩，从而保留了最新的上下文信息。
) -> tuple[list[str], list[str], int]:
    # 计算需要压缩的历史请求数量
    previous_requests=conversation_history[:-1]

    history_chars=sum(len(request) for request in previous_requests)

    if(summarized_request_count==0 and history_chars<=summary_trigger_chars):
        return [], previous_requests, 0
    # 需要压缩历史请求

    summary_end=max(summarized_request_count, len(previous_requests)-recent_request_count)
    summary_batch = previous_requests[summarized_request_count:summary_end]
    recent_requests = previous_requests[summary_end:]

    return summary_batch, recent_requests, summary_end


def update_conversation_summary(
    model: BaseChatModel,
    old_summary: str,
    summary_batch: list[str],
) -> str:
    """把新的旧需求合并到已有摘要中。"""
    if not summary_batch:
        return old_summary

    requests_text="\n".join(f"{index}. {request}" for index, request in enumerate(summary_batch, start=1))

    summary_prompt=(
        "请维护一份用户需求摘要。\n\n"
        f"[已有摘要]\n"
        f"{old_summary or '无'}\n\n"
        f"[需要加入摘要的旧需求]\n"
        f"{requests_text}\n\n"
        "请输出合并后的完整中文摘要。"
        "保留目标、限制条件和已经确认的决定，"
        "不要编造信息。"
    )

    summary_reply=model.invoke(
        [
            {
                "role": "user",
                "content": summary_prompt,
            }
        ]
    )

    return str(summary_reply.content)

def format_history_for_planner(
    conversation_summary: str,
    recent_requests: list[str],
)-> str:
    """整理 Planner 能看到的历史内容。"""
    history_sections: list[str] = []

    if conversation_summary:
        history_sections.append(f"[同一会话的历史需求摘要]\n{conversation_summary}")

    if recent_requests:
        recent_text = "\n".join(f"{index}. {request}" for index, request in enumerate(recent_requests, start=1))
        history_sections.append(f"[最近的用户请求]\n{recent_text}")

    if not history_sections:
        return "无历史对话记录。"

    return "\n\n".join(history_sections)


def build_planner_node(
        model: BaseChatModel,
        tools: Sequence[BaseTool] | None = None) -> GraphNode:
    """创建 Planner Agent 对应的 LangGraph Node。"""

    planner_agent = build_planner_agent(model, tools=tools)

    def planner_node(state: MultiAgentState,) -> dict[str, object]:
        """生成第一版计划或根据 Explorer 反馈重新规划。"""


        """
        [:-1] = 排除最后一条，取得以前的历史
        [-1:] = 只取最后一条，也就是本轮任务
        """
        conversation_history = state.get("conversation_history", [])
        (
            summary_batch,
            recent_requests,
            next_summarized_count,
        ) = split_history_for_summary(
            conversation_history=conversation_history,
            summarized_request_count=state.get("summarized_request_count", 0),
        )

        conversation_summary = update_conversation_summary(
            model=model,
            old_summary=state.get("conversation_summary", ""),
            summary_batch=summary_batch,
        )

        history_text = format_history_for_planner(
            conversation_summary=conversation_summary,
            recent_requests=recent_requests,
        )


    
        previous_revision = state.get("plan_revision", 0)
        new_revision = previous_revision + 1
        is_replan = previous_revision > 0

        replan_count = state.get("replan_count", 0)
        if is_replan:
            replan_count += 1

        if is_replan:
            task_content = (
                f"[同一会话的历史需求]\n"
                f"{history_text}\n\n"
                f"[本轮用户任务]\n"
                f"{state['user_request']}\n\n"
                f"[上一版计划]\n"
                f"{state.get('plan', '')}\n\n"
                f"[Explorer 反馈]\n"
                f"{state.get('replan_feedback', [])}\n\n"
                f"请生成第 {new_revision} 版完整计划。"
            )
        else:
            task_content = (
                f"[同一会话的历史需求]\n"
                f"{history_text}\n\n"
                f"[本轮用户任务]\n"
                f"{state['user_request']}\n\n"
                f"请生成第 {new_revision} 版完整计划。"
            )

        result = planner_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": task_content,
                    }
                ]
            }
        )
        executed_tools = get_executed_tool_names(result)

        print(
            "Planner 工具调用："
            + (
                ", ".join(executed_tools)
                if executed_tools
                else "无"
            )
        )

        plan = get_last_reply(result)

        print(f"\n=== Planner Node：生成第 {new_revision} 版计划 ===")
        print(f"计划内容：\n{plan}\n")

        return {
            "plan": plan,
            "plan_revision": new_revision,
            "replan_count": replan_count,
            "plan_approved": None,
            "replan_feedback": [],
            "conversation_summary": conversation_summary,
            "summarized_request_count": next_summarized_count,
            "phase": "exploring",
            "next_role": "explorer",
        }

    return planner_node