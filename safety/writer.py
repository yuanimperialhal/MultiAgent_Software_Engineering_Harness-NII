from pathlib import Path

from contracts.file_change import FileChange
from .route_guard import resolve_sandbox_path

def apply_file_change(change: FileChange, sandbox_root: Path) -> Path:
    """校验并执行一项 FileChange。"""

    target= resolve_sandbox_path(sandbox_root, change.relative_path,)#使用 resolve_sandbox_path 函数将相对路径解析为沙箱内的安全绝对路径。

    if change.operation == "create" and target.exists():
        raise FileExistsError(f"FileChange 创建操作失败：目标文件 {target} 已存在。")

    if change.operation == "replace" and not target.is_file():
        raise FileNotFoundError(f"FileChange 替换操作失败：目标文件 {target} 不存在或不是一个文件。")

    target.parent.mkdir(parents=True, exist_ok=True)#确保目标文件的父目录存在，如果不存在则创建它们。
    target.write_text(change.content, encoding="utf-8")#将 FileChange 的内容写入目标文件。
    return target
        