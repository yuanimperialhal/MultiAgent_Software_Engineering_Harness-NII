from typing import Any

from langchain.agents import create_agent

from langchain.agents.middleware import wrap_model_call

from langchain.tools import tool
from langchain_core.messages import ToolMessage

from langchain_core.language_models.chat_models import BaseChatModel

from .prompt import EXPLORER_SYSTEM_PROMPT
from contracts import ExplorerReport

from collections.abc import Sequence
from langchain_core.tools import BaseTool

@tool(  args_schema=ExplorerReport,
        return_direct=False,
        response_format="content_and_artifact",)

def submit_explorer_report(
    plan_approved: bool,
    plan_revision: int,
    observations: list[str],

    replan_feedback: list[str]
    ) -> tuple[str, dict[str, Any]]:

    """
    提交 Explorer 对当前计划的结构化检查报告。
    observations(观察/发现)是智能体(Agent)系统里的一个通用概念,
    来自 ReAct 模式(Thought → Action → Observation 循环):
    智能体每执行一次"动作"(比如查看文件、调用工具、检查计划),
    都会产生一个"观察结果",记录它看到了什么、发现了什么问题。
    """

    report = ExplorerReport(
        plan_approved=plan_approved,
        plan_revision=plan_revision,
        observations=observations,
        replan_feedback=replan_feedback,
    )

    return (
        "ExplorerReport 提交成功。"
        "请不要再次调用工具，直接结束任务。",
        report.model_dump(),
    )
    """
    model_dump() 就是"拆包"
    相当于把表格对象拆解成:
    {
    "plan_approved": True,
    "plan_revision": 1,
    "observations": [...],
    "replan_feedback": [],
    }
    变成一个谁都能读、能存、能传的"通用格式"。
    """
EXPLORER_RESEARCH_TOOL_NAMES = frozenset(
    {
        "web_search_exa",
        "web_fetch_exa",
    }
)

MAX_EXPLORER_RESEARCH_CALLS = 3
@wrap_model_call
def force_explorer_report_submission(
    request,
    handler,
):
    """允许有限研究，并保证最终只提交一份报告。"""

    report_submitted = any(
        isinstance(message, ToolMessage)
        and message.name == "submit_explorer_report"
        and message.status == "success"
        and message.artifact is not None
        for message in request.messages
    )

    if report_submitted:
        return handler(
            request.override(tool_choice="none")
        )

    research_call_count = sum(
        1
        for message in request.messages
        if (
            isinstance(message, ToolMessage)
            and message.name
            in EXPLORER_RESEARCH_TOOL_NAMES
        )
    )

    force_report_choice = {
        "type": "function",
        "function": {
            "name": "submit_explorer_report"
        },
    }

    if (
        research_call_count
        >= MAX_EXPLORER_RESEARCH_CALLS
    ):
        return handler(
            request.override(
                tool_choice=force_report_choice
            )
        )

    response = handler(request)

    proposed_tool_calls = (
        response.result[-1].tool_calls
    )

    # 一次只允许一个动作。
    # 如果模型想直接回答或一次调用多个工具，
    # 丢弃该回答并强制提交报告。
    if len(proposed_tool_calls) == 1:
        return response

    return handler(
        request.override(
            tool_choice=force_report_choice
        )
    )



def build_explorer_agent(
        model: BaseChatModel,
        tools: Sequence[BaseTool] | None = None):
    """使用指定模型创建 Explorer Agent。"""
    selected_tools = (
        [submit_explorer_report]
        if tools is None
        else list(tools)
    )    
    return create_agent(
        model=model,
        tools=selected_tools,
        middleware=[force_explorer_report_submission],
        system_prompt=EXPLORER_SYSTEM_PROMPT,
        name="Explorer",
    )


def extract_explorer_report(
    result: dict[str, Any],
) -> ExplorerReport:
    """从 Explorer 输出中提取 ExplorerReport。"""

    matching_reports: list[ExplorerReport] = []
    submit_messages: list[ToolMessage] = []

    messages = result.get("messages", [])

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        if message.name != "submit_explorer_report":
            continue

        submit_messages.append(message)

        if (
            message.status == "success"
            and message.artifact is not None
        ):
            matching_reports.append(
                ExplorerReport.model_validate(
                    message.artifact
                )
            )

    if len(matching_reports) != 1:
        diagnostics = [
            {
                "status": message.status,
                "has_artifact": (
                    message.artifact is not None
                ),
                "content": str(message.content)[:800],
            }
            for message in submit_messages
        ]

        message_types = [
            type(message).__name__
            for message in messages
        ]

        raise ValueError(
            "Explorer 必须且只能成功提交一次 "
            "ExplorerReport。"
            f"成功报告数={len(matching_reports)}；"
            f"消息类型={message_types}；"
            f"submit 工具消息={diagnostics}"
        )

    return matching_reports[0]