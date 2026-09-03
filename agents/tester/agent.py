from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import ToolMessage

from contracts import GateFinding,TestRunResult,TesterReport
from .prompt import TESTER_SYSTEM_PROMPT

from collections.abc import Sequence
from langchain_core.tools import BaseTool

@tool(args_schema=TesterReport,return_direct=False,response_format="content_and_artifact",)
def submit_tester_report(
    passed: bool,
    revision: int,
    test_results: list[TestRunResult],
    findings: list[GateFinding],

) -> tuple[str,dict[str, Any]]:
    """提交 Tester 生成的一份结构化测试报告。"""
    report = TesterReport(
        passed=passed,
        revision=revision,
        test_results=test_results,
        findings=findings,
    )

    return (
        "TesterReport 提交成功。"
        "请不要再次调用工具，直接结束任务。",
        report.model_dump(),
    )

def build_tester_agent(
        model: BaseChatModel,
        tester_runner_tool: BaseTool | None = None,
        *,
        tools: Sequence[BaseTool] | None = None,
):
    """创建真正的 Tester Agent。"""

    if (
        tester_runner_tool is not None
        and tools is not None
    ):
        raise ValueError(
            "tester_runner_tool 和 tools "
            "不能同时传入。"
        )

    if tools is not None:
        selected_tools = list(tools)
    elif tester_runner_tool is not None:
        selected_tools = [
            tester_runner_tool,
            submit_tester_report,
        ]
    else:
        raise ValueError(
            "Tester 必须接收 tester_runner_tool "
            "或 tools。"
        )

    return create_agent(
        model=model,
        system_prompt=TESTER_SYSTEM_PROMPT,
        tools=selected_tools,
        name="Tester",
    )


def extract_tester_report(result:dict[str, Any]) -> TesterReport:
    """从 Tester Agent 的输出中提取 TesterReport 对象。"""
    matching_calls=[]

    for message in result.get("messages", []):
        if not isinstance(message, ToolMessage):
            continue
        if message.name != "submit_tester_report":
            continue

        if (
            message.status != "success"
            or message.artifact is None
        ):
            continue

        matching_calls.append(
            TesterReport.model_validate(
                message.artifact
            )
        )

    if len(matching_calls) != 1:
        raise ValueError(
            "Tester 必须且只能成功提交一次 TesterReport。"
        )
    return matching_calls[0]