from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel

from collections.abc import Sequence

from langchain_core.tools import BaseTool

from .prompt import PLANNER_SYSTEM_PROMPT

def build_planner_agent(
    model: BaseChatModel,
    tools: Sequence[BaseTool] | None = None):
    """使用指定模型创建 Planner Agent。"""

    selected_tools = (
        []
        if tools is None
        else list(tools)
    )
    return create_agent(
        model=model,
        tools=selected_tools,
        system_prompt=PLANNER_SYSTEM_PROMPT,
    )



