from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import ToolMessage

from contracts import GateFinding,VerificationCheck,VerifierReport
from .prompt import VERIFIER_SYSTEM_PROMPT

from collections.abc import Sequence
from langchain_core.tools import BaseTool

@tool(args_schema=VerifierReport,return_direct=False,response_format="content_and_artifact",)
def submit_verifier_report(
    passed: bool,
    revision: int,
    checks: list[VerificationCheck],
    findings: list[GateFinding],

) -> tuple[str,dict[str, Any]]:
    """提交 Verifier 生成的一份结构化核验报告。"""
    report = VerifierReport(
        passed=passed,
        revision=revision,
        checks=checks,
        findings=findings,
    )

    return (
        "VerifierReport 提交成功。"
        "请不要再次调用工具，直接结束任务。",
        report.model_dump(),
    )

def build_verifier_agent(
    model: BaseChatModel,
    tools: Sequence[BaseTool] | None = None,
):
    """创建真正的 Verifier Agent。"""
    selected_tools = (
        [submit_verifier_report]
        if tools is None
        else list(tools)
    )
    return create_agent(
        model=model,
        system_prompt=VERIFIER_SYSTEM_PROMPT,
        tools=selected_tools,
        name="Verifier",
    )

def extract_verifier_report(result:dict[str, Any]) -> VerifierReport:
    """从 Verifier Agent 的输出中提取 VerifierReport 对象。"""
    matching_calls=[]

    for message in result.get("messages", []):
        if not isinstance(message, ToolMessage):
            continue
        if message.name != "submit_verifier_report":
            continue

        if (
            message.status != "success"
            or message.artifact is None
        ):
            continue

        matching_calls.append(
            VerifierReport.model_validate(message.artifact)
        )

    if len(matching_calls) != 1:
        raise ValueError(
            "Verifier 必须且只能成功提交一次 VerifierReport。"
        )

    return matching_calls[0]