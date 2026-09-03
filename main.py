from agents import (
    build_main_agent, 
    build_planner_agent,
    build_explorer_agent,
    build_implementer_agent,
    extract_file_change,
    build_reviewer_agent,
    extract_reviewer_report,
    build_tester_agent,
    extract_tester_report,
    build_verifier_agent,
    extract_verifier_report,
)
from llm import create_llm
from pathlib import Path
from safety import apply_file_change,build_test_runner_tool
from workflow.node_handlers.common import build_python_project_snapshot



def get_last_reply(result:dict)->str:
    """取出 Agent 返回的最后一条消息。"""
    return result["messages"][-1].content

def build_source_snapshot(sandbox_root:Path)->str:
    """读取练习沙箱当前的 Python 源码。"""
    return build_python_project_snapshot(sandbox_root)


def main()->None:
    model = create_llm()

    sandbox_root = Path(__file__).resolve().parent / "practice_sandbox"

    main_agent = build_main_agent(model)
    planner_agent = build_planner_agent(model)
    explorer_agent = build_explorer_agent(model)
    implementer_agent = build_implementer_agent(model)
    reviewer_agent = build_reviewer_agent(model)
    tester_agent = build_tester_agent(
        model=model,
        tester_runner_tool=build_test_runner_tool(sandbox_root),
    )
    verifier_agent = build_verifier_agent(model)

    user_task = "开发一个支持新增、查看和完成待办事项的 Python 程序。"
    print("=== 1. 用户任务 ===")
    print(user_task)

    main_result = main_agent.invoke(
        {
            "messages":[
                {"role":"user", 
                 "content":(
                        f"[原始用户任务]\n{user_task}\n\n"
                        "请整理成给 Planner 的任务说明。"),
                }
            ]
        }
    )

    planner_task = get_last_reply(main_result)
    print("\n=== 2. Main Agent 给 Planner 的任务说明 ===")
    print(planner_task)

    planner_result = planner_agent.invoke(
        {
            "messages":[
                {"role":"user", 
                 "content":planner_task,
                }
            ]
        }
    )

    planner_report = get_last_reply(planner_result)
    print("\n=== 3. Planner Agent 给 Main Agent 的计划报告 ===")
    print(planner_report)

    planner_acceptance_result = main_agent.invoke(
        {
            "messages":[
                {"role":"user", 
                 "content":(
                        f"[原始用户任务]\n{user_task}\n\n"
                        f"[Planner 报告]\n{planner_report}\n\n"
                        "请接收这份报告，并说明下一步交给谁。"),
                }
            ]
        }
    )

    planner_acceptance = get_last_reply(planner_acceptance_result)

    print("\n=== 4. Main Agent 接收报告 ===")
    print(planner_acceptance)

    # 当前还没有 safe_reader。
    # Python 先把确定的项目事实作为快照交给 Explorer。
    
    project_snapshot = (
        "项目类型：练习项目\n"
        "练习目录：practice_sandbox\n"
        f"[当前源码]\n{build_source_snapshot(sandbox_root)}\n\n"
        "现有测试：无\n"
        "现有依赖配置：无"
    )

    explorer_result = explorer_agent.invoke(
        {
            "messages":[
                {"role":"user", 
                 "content":(
                        f"[Main Agent 指示]\n{planner_acceptance}\n\n"
                        f"[原始用户任务]\n{user_task}\n\n"
                        f"[Planner 报告]\n{planner_report}\n\n"
                        f"[项目快照]\n{project_snapshot}\n\n"
                        "请调查当前项目状态并返回事实报告。"),
                }
            ]
        }
    )

    explorer_report = get_last_reply(explorer_result)
    print("\n=== 5. Explorer Agent 给 Main Agent 的调查报告 ===")
    print(explorer_report)

    explorer_acceptance_result = main_agent.invoke(
        {
            "messages":[
                {"role":"user", 
                 "content":(
                        f"[原始用户任务]\n{user_task}\n\n"
                        f"[Explorer 报告]\n{explorer_report}\n\n"
                        "请接收 Explorer 报告并说明下一步。"),
                }
            ]
        }
    )
    implementer_task = get_last_reply(explorer_acceptance_result)
    print("\n=== 6. Main Agent 接收 Explorer 报告 ===")
    print(implementer_task)

    implementer_result = implementer_agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": (
                    f"[Main Agent 实现任务]\n"
                    f"{implementer_task}\n\n"
                    f"[原始用户任务]\n{user_task}\n\n"
                    f"[Planner 报告]\n{planner_report}\n\n"
                    f"[Explorer 报告]\n{explorer_report}\n\n"
                    "本轮只生成一个完整 FileChange。\n"
                    "如果目标路径已经存在，operation 必须使用 replace；"
                    "只有新路径才能使用 create。"
                ),
            }
        ]
    }
    )
    file_change = extract_file_change(implementer_result)

    print("\n=== 7. Implementer Agent 给 Main Agent 的 FileChange ===")
    print(file_change.model_dump_json(indent=2, ensure_ascii=False))

    print(f"\n=== 8. {file_change.relative_path} 内容预览：尚未写入 ===")
    print(file_change.content)

    written_path = apply_file_change(file_change, sandbox_root)

    print("\n=== 9. Python 受控写入完成 ===")
    print(written_path)

    artifact_revision=1
    current_source_snapshot = build_source_snapshot(sandbox_root)
    reviewer_result=reviewer_agent.invoke(
        {
            "messages":[
                {
                    "role": "user",
                    "content": (
                        "[Main Agent 审查任务]\n"
                        f"请审查 artifact revision "
                        f"{artifact_revision}。\n\n"
                        f"[原始用户任务]\n"
                        f"{user_task}\n\n"
                        f"[Planner 报告]\n"
                        f"{planner_report}\n\n"
                        f"[Explorer 报告]\n"
                        f"{explorer_report}\n\n"
                        f"[本轮 FileChange]\n"
                        f"{file_change.model_dump_json(
                            indent=2,
                            ensure_ascii=False,
                        )}\n\n"
                        f"[当前项目源码]\n"
                        f"{current_source_snapshot}\n\n"
                        "请只进行代码审查，"
                        "不能声称已经运行测试。"
                    ),                    
                }
            ]
        }
    )

    reviewer_report=extract_reviewer_report(reviewer_result)
    reviewer_report_json=(
        reviewer_report.model_dump_json(indent=2,ensure_ascii=False)
    )
    print("\n=== 10. Reviewer Agent 给 Main Agent 的报告 ===")    
    print(reviewer_report_json)


    reviewer_acceptance_result = main_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"[原始用户任务]\n"
                        f"{user_task}\n\n"
                        f"[Reviewer 报告]\n"
                        f"{reviewer_report_json}\n\n"
                        "请接收 Reviewer 报告。\n"
                        "如果 passed 为 true，"
                        "说明保存报告并进入 Tester。\n"
                        "如果 passed 为 false，"
                        "根据 blocking findings 生成"
                        "给 Implementer 的修复任务。\n"
                        "不能声称修复已经执行。"
                    ),
                }
            ]
        }
    )

    reviewer_next_instruction = get_last_reply(
        reviewer_acceptance_result
    )

    print("\n=== 11. Main Agent 接收 Reviewer 报告 ===")
    print(reviewer_next_instruction)

    print("\n=== 12. Python 确定下一站 ===")

    if not reviewer_report.passed:
        print("Reviewer 报告不通过，进入 Implementer 修复阶段。")
        return
    print("Reviewer 报告通过，进入 Tester 阶段。")
    tester_result = tester_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                            "[Main Agent 测试任务]\n"
                            f"请测试 artifact revision "
                            f"{artifact_revision}。\n\n"
                            f"[原始用户任务]\n"
                            f"{user_task}\n\n"
                            "[本次允许的受控测试]\n"
                            "- python_project_tests：递归检查项目语法，"
                            "并自动运行 tests/test_*.py。\n\n"
                            "必须先调用 run_allowed_test，"
                            "test_id 只能使用 python_project_tests。\n"
                            "获得真实执行结果后，再调用 "
                            "submit_tester_report 提交报告。"
                            ),
                }
            ]
        }
    )
    tester_report = extract_tester_report(tester_result)
    tester_report_json = tester_report.model_dump_json(indent=2, ensure_ascii=False)


    print("\n=== 13. Tester Agent 给 Main Agent 的报告 ===")
    print(tester_report_json)
    tester_acceptance_result = main_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"[原始用户任务]\n"
                        f"{user_task}\n\n"
                        f"[Tester 报告]\n"
                        f"{tester_report_json}\n\n"
                        "请接收 Tester 报告。\n"
                        "如果 passed 为 true，"
                        "说明保存报告并进入 Verifier。\n"
                        "如果 passed 为 false，"
                        "根据 blocking findings 生成"
                        "给 Implementer 的修复任务。\n"
                        "不能声称修复已经执行。"
                    ),
                }
            ]
        }
    )
    tester_next_instruction = get_last_reply(tester_acceptance_result)
    print("\n=== 14. Main Agent 接收 Tester 报告 ===")
    print(tester_next_instruction)

    print("\n=== 15. Python 确定下一站 ===")
    if not tester_report.passed:
        print("Tester 报告不通过，进入 Implementer 修复阶段。")
        return

    print("Tester 报告通过，进入 Verifier 阶段。")
    verifier_result = verifier_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"[Main Agent 最终核验任务]\n"
                        f"{tester_next_instruction}\n\n"
                        f"[原始用户任务]\n"
                        f"{user_task}\n\n"
                        f"[当前 artifact revision]\n"
                        f"{artifact_revision}\n\n"
                        f"[当前项目源码]\n"
                        f"{current_source_snapshot}\n\n"
                        f"[Reviewer 报告]\n"
                        f"{reviewer_report_json}\n\n"
                        f"[Tester 报告]\n"
                        f"{tester_report_json}\n\n"
                        "请逐项核对用户需求及现有证据，"
                        "然后提交 VerifierReport。"
                    ),
                }
            ]
        }
    )
    verifier_report = extract_verifier_report(verifier_result)
    verifier_report_json = verifier_report.model_dump_json(indent=2, ensure_ascii=False)

    print("\n=== 16. Verifier Agent 给 Main Agent 的报告 ===")
    print(verifier_report_json)
    verifier_acceptance_result = main_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"[原始用户任务]\n"
                        f"{user_task}\n\n"
                        f"[Verifier 报告]\n"
                        f"{verifier_report_json}\n\n"
                        "请接收 Verifier 报告。"
                        "如果 passed 为 true，说明任务完成；"
                        "如果 passed 为 false，只说明需要返回 "
                        "Implementer，不能声称已经修复。"
                    ),
                }
            ]
        }
    )    

    print("\n=== 17. Main Agent 接收 Verifier 报告 ===")
    print(get_last_reply(verifier_acceptance_result))

    print("\n=== 18. Python 确定最终状态 ===")

    if verifier_report.passed:
        print("Verifier 报告通过，任务完成。")
    else:
        print(
            "Verifier 报告不通过，"
            "后续由 LangGraph 返回 Implementer。"
        )


if __name__ == "__main__":
    main()
