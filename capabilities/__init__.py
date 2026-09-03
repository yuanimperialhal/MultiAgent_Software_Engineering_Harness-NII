"""Stage 9 的统一能力平台。"""

"""
程序扫描 local_tools/
→ 找到 text_stats.py
→ 读取 TOOL_REGISTRATIONS
→ contracts.py 验证登记是否合法
→ registry.py 保存登记
→ 根据 AgentRole 发放工具
→ Agent 调用 text_stats
→ 返回字符、单词和行数
"""
from .contracts import AgentRole, ToolRegistration
from .registry import (
    ToolRegistry,
    build_local_tool_registry,
    discover_local_tool_registrations,
)
from .bootstrap import build_tool_registry
__all__ = [
    "AgentRole",
    "ToolRegistration",
    "ToolRegistry",
    "build_local_tool_registry",
    "discover_local_tool_registrations",
    "build_tool_registry",
    
]