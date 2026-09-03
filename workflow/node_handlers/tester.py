from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from collections.abc import Callable, Sequence
from typing import Any


from agents.tester import build_tester_agent,extract_tester_report

from workflow.state import MultiAgentState

GraphNode=Callable[[MultiAgentState],dict[str, Any]]

def build_tester_node(model: BaseChatModel,*,tools: Sequence[BaseTool] | None = None) -> GraphNode:
    """创建 Tester Agent 对应的 LangGraph Node。"""

    tester_agent=build_tester_agent(
        model=model,
        tools=tools,
    )


    def tester_node(state: MultiAgentState) -> dict[str, Any]:
        result = tester_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "[Main Agent 测试任务]\n"
                            "请测试当前生成的 Python 项目。\n\n"
                            "[原始用户任务]\n"
                            f"{state['user_request']}\n\n"
                            "[已批准计划]\n"
                            f"{state['plan']}\n\n"
                            "[当前代码版本]\n"
                            f"{state['artifact_revision']}\n\n"
                            "[当前项目快照]\n"
                            f"{state['project_snapshot']}\n\n"
                            "必须先调用系统提供的受控测试工具，"
                            "取得真实测试结果后，再提交 "
                            "TesterReport。"
                        ),
                    }
                ]
            }
        )


        tester_report = extract_tester_report(result)
        if (tester_report.revision!= state["artifact_revision"]):
            raise ValueError("TesterReport 的 revision与当前代码版本不一致。")


        print("\n=== Tester Node：测试当前项目 ===")
        print(tester_report.model_dump_json(indent=2,ensure_ascii=False,))


        return {
            "tester_report": tester_report,
            "phase": "testing",
            "status":"running",
            "next_role": "main_agent",
        }

    return tester_node