from collections.abc import Callable
from typing import Literal

from langgraph.graph import START,END,StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver


from .state import MultiAgentState

GraphNode = Callable[[MultiAgentState], dict[str, object]]

PlanningRoute = Literal["planner", "ready", "failed"]

ReviewRoute = Literal["repair", "tester_ready", "failed"]

TestRoute = Literal["repair", "Verifier_ready", "failed"]

VerifierRoute = Literal["repair", "completed", "failed"]



def route_after_planning_main(state: MultiAgentState) -> PlanningRoute:
    """根据主 Agent 的状态，决定下一步的规划路线。"""


    if state.get("plan_approved") is True:
        return "ready"

    replan_count = state.get("replan_count", 0)
    max_replans = state.get("max_replans", 0)

    if replan_count >= max_replans:
        return "failed"

    return "planner"

def route_after_review_main(state: MultiAgentState) -> ReviewRoute:
    """根据 Reviewer 结果控制修复循环。"""

    if state.get("status") == "failed":
        return "failed"

    if state.get("next_role") == "implementer":
        return "repair"

    if state.get("next_role") == "tester":
        return "tester_ready"

    return "failed"

def route_after_test_main(state: MultiAgentState) -> TestRoute:
    """根据 Tester 结果控制修复循环。"""

    if state.get("status") == "failed":
        return "failed"

    if state.get("next_role") == "implementer":
        return "repair"

    if state.get("next_role") == "verifier":
        return "Verifier_ready"

    return "failed"


def route_after_verifier_main(state: MultiAgentState) -> VerifierRoute:
    """根据 Verifier 结果控制最终修复循环或结束工作流。"""

    if state.get("status") == "completed":
        return "completed"

    if state.get("status") == "failed":
        return "failed"

    if state.get("next_role") == "implementer":
        return "repair"

    return "failed"

def enter_implementer_node(state: MultiAgentState) -> dict[str, object]:
    """进入 Implementer 节点时的状态更新。"""
    return {
        "phase": "implementing",
        "status": "running",
        "next_role": "implementer",
    }


def planning_failed_node(state: MultiAgentState) -> dict[str, object]:
    """重新规划次数耗尽，结束工作流。"""
    return {
        "phase": "failed",
        "status": "failed",
        "next_role": None,
    }

def build_planning_graph(
    * ,
    planner_node: GraphNode,
    explorer_node: GraphNode,
    implementer_node: GraphNode,
    reviewer_node: GraphNode,
    tester_node: GraphNode,
    verifier_node: GraphNode,
    planning_main_node: GraphNode,
    review_main_node: GraphNode,
    test_main_node: GraphNode,
    verifier_main_node: GraphNode,
    checkpointer: BaseCheckpointSaver | None = None,


) -> StateGraph[MultiAgentState]:
    """构建 Multi-Agent 工作流的规划阶段状态图。"""
    """创建 Planner、Explorer、Main 的有限循环。"""

    builder = StateGraph(MultiAgentState)

    builder.add_node("planner", planner_node)
    builder.add_node("explorer", explorer_node)
    builder.add_node("implementer", implementer_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("planning_main", planning_main_node)
    builder.add_node("review_main", review_main_node)
    builder.add_node("tester", tester_node)  # 添加 Tester 节点，实际实现应替换 None
    builder.add_node("verifier", verifier_node)
    builder.add_node("verifier_main", verifier_main_node)
    builder.add_node("test_main", test_main_node)
    builder.add_node("ready", enter_implementer_node)
    builder.add_node("failed", planning_failed_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "explorer")
    builder.add_edge("explorer", "planning_main")

    builder.add_conditional_edges("planning_main",
    route_after_planning_main, {
        "planner": "planner",
        "ready": "ready",
        "failed": "failed",

    })

    builder.add_edge("ready", "implementer")
    builder.add_edge("implementer", "reviewer")
    builder.add_edge("reviewer", "review_main")

    # 当前检查点在 Main 接收 Reviewer 报告后结束
    builder.add_edge("failed", END)
    builder.add_conditional_edges("review_main",
        route_after_review_main, {
            "repair": "implementer",
            "tester_ready": "tester",
            "failed": END,
        }
    )
    builder.add_edge("tester", "test_main")
    builder.add_conditional_edges("test_main",
        route_after_test_main, {
            "repair": "implementer",
            "Verifier_ready": "verifier",
            "failed": END,
        }
    )
    builder.add_edge("verifier", "verifier_main")
    builder.add_conditional_edges(
        "verifier_main",
        route_after_verifier_main,
        {
            "repair": "implementer",
            "completed": END,
            "failed": END,
        },
    )


    return builder.compile(checkpointer=checkpointer)

