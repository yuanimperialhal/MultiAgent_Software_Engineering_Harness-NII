from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from capabilities import AgentRole,ToolRegistry

from .node_handlers import (
    build_planner_node,
    build_explorer_node,
    build_implementer_node,
    build_reviewer_node,
    build_main_nodes,
    build_tester_node,
    build_verifier_node,
)


def build_planning_nodes(model:BaseChatModel, tool_registry: ToolRegistry,)->dict:
    """创建规划阶段使用的三个真实 Agent 节点。"""
    planner_node = build_planner_node(model,tools=tool_registry.tools_for(AgentRole.PLANNER))
    explorer_node = build_explorer_node(model,tools=tool_registry.tools_for(AgentRole.EXPLORER))
    implementer_node = build_implementer_node(model,tools=tool_registry.tools_for(AgentRole.IMPLEMENTER))
    reviewer_node = build_reviewer_node(model,tools=tool_registry.tools_for(AgentRole.REVIEWER))
    main_nodes = build_main_nodes(model,tools=tool_registry.tools_for(AgentRole.MAIN_AGENT))
    tester_node = build_tester_node(model=model, tools=tool_registry.tools_for(AgentRole.TESTER))
    verifier_node = build_verifier_node(model,tools=tool_registry.tools_for(AgentRole.VERIFIER))

    return {
        "planner_node": planner_node,
        "explorer_node": explorer_node,
        "implementer_node": implementer_node,
        "reviewer_node": reviewer_node,
        "tester_node": tester_node,
        "verifier_node": verifier_node,
        "planning_main_node": main_nodes["planning_main_node"],
        "review_main_node": main_nodes["review_main_node"],
        "test_main_node": main_nodes["test_main_node"],
        "verifier_main_node": main_nodes["verifier_main_node"],
    }
