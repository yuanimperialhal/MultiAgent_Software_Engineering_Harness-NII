from collections.abc import Callable, Sequence
from langchain_core.tools import BaseTool
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from agents.implementer import (
    build_implementer_agent,
    extract_file_change,
)
from safety import apply_file_change
from workflow.state import MultiAgentState
from .common import build_python_project_snapshot


GraphNode = Callable[
    [MultiAgentState],
    dict[str, Any],
]


def build_implementer_node(
    model: BaseChatModel,
    tools: Sequence[BaseTool] | None = None,
) -> GraphNode:
    """创建 Implementer Agent 对应的 LangGraph Node。"""

    implementer_agent = build_implementer_agent(model, tools=tools)

    def implementer_node(
        state: MultiAgentState,
    ) -> dict[str, Any]:
        """生成 FileChange，并通过安全 Writer 执行写入。"""

        reviewer_report = state.get("reviewer_report")
        tester_report = state.get("tester_report")
        verifier_report = state.get("verifier_report")

        repair_context = ""

        # Verifier 是最后一道质量门，失败时优先处理最终核验问题。
        if (
            verifier_report is not None
            and not verifier_report.passed
        ):
            report_json = verifier_report.model_dump_json(
                indent=2,
                ensure_ascii=False,
            )

            repair_context = (
                "[需要修复的 VerifierReport]\n"
                f"{report_json}\n\n"
                "这是最终核验失败后的修复阶段。"
                "请根据未满足的 checks 和 blocking findings"
                "精确修复代码。\n\n"
            )

        # 没有 Verifier 失败时，再处理 Tester 的真实测试问题。
        elif (
            tester_report is not None
            and not tester_report.passed
        ):
            report_json = tester_report.model_dump_json(
                indent=2,
                ensure_ascii=False,
            )

            repair_context = (
                "[需要修复的 TesterReport]\n"
                f"{report_json}\n\n"
                "这是测试失败后的修复阶段。"
                "请根据 blocking findings 和真实测试结果"
                "精确修复代码。\n\n"
            )

        # 前两道质量门没有失败时，再处理 Reviewer 的问题。
        elif (
            reviewer_report is not None
            and not reviewer_report.passed
        ):
            report_json = reviewer_report.model_dump_json(
                indent=2,
                ensure_ascii=False,
            )

            repair_context = (
                "[需要修复的 ReviewerReport]\n"
                f"{report_json}\n\n"
                "这是审查失败后的修复阶段。"
                "请根据 blocking findings 精确修复代码。\n\n"
            )

        result = implementer_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            "[已批准计划]\n"
                            f"{state['plan']}\n\n"
                            "[ExplorerReport]\n"
                            f"{state['explorer_report']}\n\n"
                            f"{repair_context}"
                            "[当前项目快照]\n"
                            f"{state['project_snapshot']}\n\n"
                            "请生成一项完整 FileChange。\n"
                            "你只负责生成修改提案，"
                            "不能声称已经写入文件。\n"
                            "如果目标文件已经存在，"
                            "operation 必须使用 replace；"
                            "只有新文件才能使用 create。"
                        ),
                    }
                ]
            }
        )

        file_change = extract_file_change(result)

        print("\n=== Implementer：生成 FileChange ===")
        print(
            file_change.model_dump_json(
                indent=2,
                ensure_ascii=False,
            )
        )

        sandbox_root = Path(
            state["sandbox_root"]
        ).resolve()

        written_path = apply_file_change(
            file_change,
            sandbox_root,
        )

        relative_path = written_path.relative_to(
            sandbox_root
        ).as_posix()

        changed_files = list(
            state.get("changed_files", [])
        )

        if relative_path not in changed_files:
            changed_files.append(relative_path)

        project_snapshot = build_python_project_snapshot(
            sandbox_root
        )

        artifact_revision = (
            state.get("artifact_revision", 0) + 1
        )

        print("\n=== Implementer：安全写入完成 ===")
        print(f"写入路径：{written_path}")
        print(
            "artifact_revision："
            f"{artifact_revision}"
        )

        return {
            "pending_file_changes": None,

            # 新版本已经产生，旧质量报告不能继续作为当前版本证据。
            "tester_report": None,
            "verifier_report": None,

            "artifact_revision": artifact_revision,
            "changed_files": changed_files,
            "project_snapshot": project_snapshot,
            "phase": "reviewing",
            "status": "running",
            "next_role": "reviewer",
        }

    return implementer_node
