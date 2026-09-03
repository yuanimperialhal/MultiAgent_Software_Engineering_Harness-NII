from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from safety import build_test_runner_tool
from capabilities import build_tool_registry

from llm import create_llm
from workflow import (
    build_planning_nodes,
    build_planning_graph,
)
from workflow.node_handlers.common import build_python_project_snapshot


from project_manager import (
    project_lock,
    resolve_project_context,
    validate_thread_id,
)
from report_store import save_quality_reports



def build_project_snapshot(
        sandbox_root: Path,
)->str:
    return build_python_project_snapshot(sandbox_root)

def read_user_request()->str:
    user_request = input("请输入您的需求: ").strip()

    if not user_request:
        raise ValueError("用户需求不能为空。")

    return user_request



def run_task(user_request: str, project_id: str = "default-project", thread_id: str = "stage9-main-thread") -> None:
    stage_root = Path(__file__).parent

    managed_sandbox = stage_root / "practice_sandbox"
    validate_thread_id(thread_id)
    project_context = resolve_project_context(
        managed_sandbox=managed_sandbox,
        project_id=project_id,
    )
    sandbox_root = project_context.sandbox_root

    thread_config = {"configurable": {"thread_id": thread_id}}
    run_config = {**thread_config,"recursion_limit": 40,}  # recursion_limit 是指在工作流中}
        # 允许的最大递归深度。它限制了状态图中节点之间的调用层级，防止无限循环或过深的嵌套调用。



    checkpoint_path = project_context.checkpoint_path
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    thread_config = {"configurable":{"thread_id":thread_id}}



    model = create_llm()
    tool_registry = build_tool_registry(sandbox_root)
    planning_nodes = build_planning_nodes(model, tool_registry=tool_registry)

    with project_lock(project_context):
        with SqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
            app = build_planning_graph(**planning_nodes, checkpointer=checkpointer)

            result = app.invoke(
                {
                    "task_id": "planning-demo-001",
                    "project_id": project_id,
                    "user_request": user_request,
                    "conversation_history":[user_request],
                    "phase": "planning",
                    "status": "running",
                    "next_role": "planner",
                    "sandbox_root": str(sandbox_root),
                    "project_snapshot": build_project_snapshot(
                        sandbox_root
                    ),
                    "plan": "",
                    "plan_revision": 0,
                    "plan_approved": None,
                    "replan_feedback": [],
                    "replan_count": 0,
                    "max_replans": 3,
                    "review_repair_count": 0,
                    "max_review_repairs": 3,

                    "artifact_revision": 0,
                    "changed_files": [],
                    "pending_file_changes": None,
                    "explorer_report": "",
                    "main_instruction": "",
                    "reviewer_report": None,

                    "tester_report": None,
                    "tester_repair_count": 0,
                    "max_tester_repairs": 3,

                    "verifier_report": None,
                    "verifier_repair_count": 0,
                    "max_verifier_repairs": 3,


                },
                config=run_config,
            )
            snapshot = app.get_state(thread_config)

        save_quality_reports(
            reports_root=project_context.reports_root,
            thread_id=thread_id,
            result=result,
        )

    """
    进入 with → 档案室开门
    app.invoke() → 执行任务并保存档案
    app.get_state() → 读取档案
    离开 with → 档案室关门
    """


    print("\n=== LangGraph 规划阶段最终状态 ===")
    print(f"project_id: {project_id}")
    print(f"project_sandbox_root: {sandbox_root}")    
    print(f"plan_revision: {result['plan_revision']}")
    print(f"replan_count: {result['replan_count']}")
    print(f"plan_approved: {result['plan_approved']}")
    print(f"phase: {result['phase']}")
    print(f"status: {result['status']}")
    print(f"next_role: {result.get('next_role')}")
    print(f"review_repair_count: "f"{result['review_repair_count']}")
    print(f"tester_repair_count: {result['tester_repair_count']}")
    print(f"max_tester_repairs: {result['max_tester_repairs']}")
    print(f"verifier_repair_count: {result['verifier_repair_count']}")
    print(f"max_verifier_repairs: {result['max_verifier_repairs']}")
    print(f"checkpoint_thread_id: {thread_id}")
    print(f"checkpoint_status: {snapshot.values.get('status')}")



    verifier_report = result.get("verifier_report")

    print(
        "verifier_passed: "
        f"{verifier_report.passed if verifier_report is not None else None}"
    )

def main() -> None:
    try:
        user_request = read_user_request()
    except ValueError as exc:
        print(f"\n输入错误：{exc}")
        return
    except (EOFError, KeyboardInterrupt):
        print("\n已取消本次任务。")
        return
    run_task(user_request,thread_id="stage9-main-thread",project_id="default-project")


if __name__ == "__main__":
    main()
