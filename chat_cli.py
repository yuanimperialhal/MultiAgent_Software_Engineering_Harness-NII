from langgraph_main import run_task
from project_manager import validate_thread_id,validate_project_id

EXIT_COMMANDS = {"exit", "quit", "退出"}
DEFAULT_THREAD_ID = "stage9-main-thread"
DEFAULT_PROJECT_ID = "default-project"
DEFAULT_THREAD_ID = "stage9-main-thread"


def read_project_id() -> str:
    project_id = input("\n请输入 project_id（直接回车使用 default-project）：").strip()
    return project_id or DEFAULT_PROJECT_ID

def read_thread_id() -> str:
    thread_id = input("\n请输入 thread_id（直接回车使用 stage9-main-thread）：").strip()
    return thread_id or DEFAULT_THREAD_ID


def read_cli_request() -> str | None:
    user_request = input("\n请输入需求（输入 exit、quit 或退出,来结束程序）：").strip()
    if user_request.casefold() in EXIT_COMMANDS:
        return None
    return user_request

def main():
    print("=== Multi-Agent 连续任务 CLI ===")
    try:
        project_id = read_project_id()
        validate_project_id(project_id)

        thread_id = read_thread_id()
        validate_thread_id(thread_id)

    except ValueError as exc:
        print(f"\n输入错误：{exc}")
        return

    except (EOFError, KeyboardInterrupt):
        print(
            "\n已退出 Multi-Agent 连续任务 CLI。"
        )
        return

    print(f"当前项目：{project_id}")
    print(f"当前会话档案号：{thread_id}")
    while True:
        try:
            user_request = read_cli_request()
            if user_request is None:
                print("已退出 Multi-Agent 连续任务 CLI。")
                break

            if not user_request:
                print("输入不能为空，请重新输入。")
                continue

            run_task(user_request, thread_id=thread_id, project_id=project_id)
        except (EOFError, KeyboardInterrupt):
            print("\n已退出 Multi-Agent 连续任务 CLI。")
            break

if __name__ == "__main__":
    main()
