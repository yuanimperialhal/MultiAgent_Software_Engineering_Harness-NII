from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from project_manager import (
    resolve_project_context,
    validate_thread_id,
)

def main()->None:
    stage_root = Path(__file__).parent
    managed_sandbox = stage_root / "practice_sandbox"
    checkpoint_path = stage_root/"data"/"checkpoint.db"
    project_id=input("请输入 project_id（直接回车使用 default-project）：").strip() or "default-project"
    thread_id=input("请输入 thread_id（直接回车使用 stage9-main-thread）：").strip() or "stage9-main-thread"

    try:
        validate_thread_id(thread_id)

        project_context = (
            resolve_project_context(
                managed_sandbox=managed_sandbox,
                project_id=project_id,
            )
        )
    except ValueError as exc:
        print(f"输入错误：{exc}")
        return

    checkpoint_path = (
        project_context.checkpoint_path
    )    


    if not checkpoint_path.exists():
        print(f"没有找到存档文件：{checkpoint_path}")
        return

    thread_config = {"configurable":{"thread_id":thread_id}}

    with SqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
        saved_checkpoint = checkpointer.get_tuple(thread_config)

    if saved_checkpoint is None:
        print(
            f"项目 {project_id} 中没有找到"
            f"没有找到线程 {thread_id} 的存档。"
            )
        return
    state = saved_checkpoint.checkpoint[
        "channel_values"
    ]

    print("=== 已恢复的任务存档 ===")
    print(f"project_id: {project_id}")
    print(f"thread_id: {thread_id}")
    print(f"phase: {state.get('phase')}")
    print(f"status: {state.get('status')}")
    print(f"artifact_revision: {state.get('artifact_revision')}")
    print(f"review_repair_count: {state.get('review_repair_count')}")
    print(f"sandbox_root: {state.get('sandbox_root')}")
    print(f"conversation_history: {state.get('conversation_history')}")
    print(f"conversation_summary: {state.get('conversation_summary')}")

if __name__ == "__main__":
    main()