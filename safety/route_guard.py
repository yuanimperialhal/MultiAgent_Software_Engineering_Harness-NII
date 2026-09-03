from pathlib import Path

def resolve_sandbox_path(sandbox_root: Path,relative_path: str,)->Path:
    """把相对路径解析为沙箱内的安全绝对路径。"""

    root = sandbox_root.resolve()#将sandbox_root路径解析为绝对路径，确保它是一个有效的路径对象。resolve()方法会处理符号链接、相对路径等，使得返回的路径是一个标准化的绝对路径。
    requested_path = Path(relative_path)#将相对路径转换为 Path 对象。

    if requested_path.is_absolute() or requested_path.drive:
        raise ValueError("FileChange 路径必须是相对路径。")

    target = (root / requested_path).resolve()#将相对路径与沙箱根路径组合，得到目标文件的绝对路径，并使用 resolve() 方法确保路径是标准化的。

    try:
        target.relative_to(root)#检查目标路径是否在沙箱根路径下。如果不是，则会引发 ValueError 异常。
    except ValueError as exc:
        raise ValueError("FileChange 路径必须在沙箱根路径下。") from exc

    if target==root:
        raise ValueError("FileChange 路径不能是沙箱根路径本身。")

    return target