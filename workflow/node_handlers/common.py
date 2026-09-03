from pathlib import Path
from langchain_core.messages import ToolMessage

def get_last_reply(result:dict)->str:
    """读取普通消息 Agent 的最后一条回复。"""
    return result["messages"][-1].content

def get_executed_tool_names(
    result: dict,
) -> list[str]:
    """返回 Agent 本轮真正执行过的工具名称。"""

    return [
        message.name
        for message in result.get("messages", [])
        if (
            isinstance(message, ToolMessage)
            and isinstance(message.name, str)
        )
    ]


def build_python_project_snapshot(project_root: Path) -> str:
    """递归读取项目中的源码，供各 Agent 共享。"""

    root = project_root.resolve()
    excluded_directories = {
        ".git",
        ".venv",
        "__pycache__",
        "venv",
    }

    language_by_suffix = {
        ".py": "python",
        ".html": "html",
        ".css": "css",
        ".js": "javascript",
    }

    sections: list[str] = []

    for source_path in sorted(root.rglob("*")):
        if not source_path.is_file():
            continue

        relative_path = source_path.relative_to(root)
        if any(
            part in excluded_directories
            for part in relative_path.parts
        ):
            continue

        language = language_by_suffix.get(source_path.suffix.lower())

        if language is None:
            continue

        source_code = source_path.read_text(encoding="utf-8")
        sections.append(
            f"### {relative_path.as_posix()}\n\n"
            f"```{language}\n"
            f"{source_code}\n"
            f"```\n"
        )

    return "\n\n".join(sections)
