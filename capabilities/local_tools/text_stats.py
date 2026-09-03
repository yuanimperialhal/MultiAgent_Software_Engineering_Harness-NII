"""
以后想加新工具，比如“翻译文本”“计算字数”“读取天气”，
就照着新建一个文件。主系统会自动发现它，不需要去改核心代码。
"""
"""
这整个文件是在新增一个给 AI Agent 使用的“小功能”：
统计一段文字有多少字符、单词和行。
"""
from langchain_core.tools import tool
#导入 @tool 装饰器。它把普通 Python 函数包装成 LangChain 能让 AI 调用的工具。

from pydantic import BaseModel, Field
#用于定义和校验工具的输入格式。比如这里要求输入必须有一个 text 字段。

from ..contracts import AgentRole, ToolRegistration

class TextStatsInput(BaseModel):
    text: str = Field( description="需要统计字符、单词和行数的文本。")

@tool(args_schema=TextStatsInput)
def text_stats(text:str)->dict[str,int]:
    """统计文本的字符数、单词数和行数。"""
    return {
        "characters": len(text),
        "non_whitespace_characters": sum(
            not character.isspace()
            for character in text
        ),
        "words": len(text.split()),
        "lines": len(text.splitlines()),
    }

TOOL_REGISTRATIONS = [
    ToolRegistration(
        tool=text_stats,
        source="local",
        allowed_roles=frozenset(
            {
                AgentRole.PLANNER,
                AgentRole.EXPLORER,
                AgentRole.REVIEWER,
                AgentRole.VERIFIER,
            }
        ),
        timeout_seconds=2.0
    ),
]

"""
是在给这个工具登记“身份证信息”：

tool=text_stats：登记的工具就是刚写的文字统计功能。
source="local"：它是项目本地写的，不来自 MCP 服务或第三方平台。
allowed_roles=...：只有 EXPLORER（探索者）和 IMPLEMENTER（执行/编码者）能用。
timeout_seconds=2.0：最多运行 2 秒。
"""