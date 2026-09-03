from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.tools import tool
from langchain_core.messages import ToolMessage

from contracts import GateFinding, ReviewerReport
from .prompt import REVIEWER_SYSTEM_PROMPT

from collections.abc import Sequence
from langchain_core.tools import BaseTool

@tool(args_schema=ReviewerReport,return_direct=False,response_format="content_and_artifact",)
def submit_reviewer_report(
    revision: int,
    passed: bool,
    findings: list[GateFinding],
)-> tuple[str, dict[str, Any]]:
    """提交 Reviewer 生成的一项结构化审查报告。"""

    report = ReviewerReport(
        passed=passed,
        revision=revision,
        findings=findings,
    )

    return (
        "ReviewerReport 提交成功。"
        "请不要再次调用工具，直接结束任务。",
        report.model_dump(),
    )

def build_reviewer_agent(
        model: BaseChatModel,
        tools: Sequence[BaseTool] | None = None):
    """创建真正的 Reviewer Agent。"""
    selected_tools = (
        [submit_reviewer_report]
        if tools is None
        else list(tools)
    )
    return create_agent(
        model=model,
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        tools=selected_tools,
        name="Reviewer",
    )

def extract_reviewer_report(result:dict[str, Any]) -> ReviewerReport:
    """从 Reviewer Agent 的输出中提取 ReviewerReport 对象。"""
    matching_calls=[]

    for message in result.get("messages", []):
        if not isinstance(message, ToolMessage):
            continue
        if message.name != "submit_reviewer_report":
            continue

        if (
            message.status != "success"
            or message.artifact is None
        ):
            continue

        matching_calls.append(
            ReviewerReport.model_validate(
                message.artifact
            )
        )

    if len(matching_calls) != 1:
        raise ValueError(
            "Reviewer 必须且只能成功提交一次 "
            "ReviewerReport。"
        )

    return matching_calls[0]