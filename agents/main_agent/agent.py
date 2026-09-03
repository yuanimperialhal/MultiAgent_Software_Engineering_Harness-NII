from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel

from .prompt import MAIN_AGENT_SYSTEM_PROMPT

from collections.abc import Sequence
from langchain_core.tools import BaseTool


def build_main_agent(model: BaseChatModel, tools: Sequence[BaseTool] | None = None):
    """使用指定模型创建 Main Agent。"""
    selected_tools = (
        []
        if tools is None
        else list(tools)
    )

    return create_agent(
        model=model,
        tools=selected_tools,
        system_prompt=MAIN_AGENT_SYSTEM_PROMPT,
    )
