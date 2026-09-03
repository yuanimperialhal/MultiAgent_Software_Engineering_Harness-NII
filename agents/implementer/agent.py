from typing import Any, Literal

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.tools import tool
from langchain_core.messages import AIMessage

from contracts import FileChange
from .prompt import IMPLEMENTER_SYSTEM_PROMPT

from collections.abc import Sequence
from langchain_core.tools import BaseTool


@tool(args_schema=FileChange, return_direct=True)
def submit_file_change(
    relative_path: str,
    operation: Literal["create","replace"],
    content: str,
    rationale: str,
)-> str:
    """提交 Implementer 生成的一项结构化文件修改。"""
    return "FileChange 已提交给 Main Agent。"



def build_implementer_agent(
    model: BaseChatModel,
    tools: Sequence[BaseTool] | None = None,
):
    """创建真正的 Implementer Agent。"""
    selected_tools = (
        [submit_file_change]
        if tools is None
        else list(tools)
    )
    return create_agent(
        model=model,
        system_prompt=IMPLEMENTER_SYSTEM_PROMPT,
        tools=selected_tools,
        name="Implementer",
    )    

def extract_file_change(result:dict[str, Any]) -> FileChange:
    """从 Implementer Agent 的输出中提取 FileChange 对象。"""
    matching_calls=[]

    for message in result.get("messages", []):
        if not isinstance(message, AIMessage):
            continue
        for tool_call in message.tool_calls:
            if tool_call["name"] == "submit_file_change":
                matching_calls.append(tool_call)

    if len(matching_calls) != 1:
        raise ValueError(
            "Implementer 必须且只能调用一次 "
            "submit_file_change。"
        )
    return FileChange.model_validate(matching_calls[0]["args"])