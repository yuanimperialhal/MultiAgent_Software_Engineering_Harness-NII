import fcntl
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

PROJECT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")

def validate_project_id(project_id: str) -> None:
    """检查项目编号是否可以安全用于目录名。"""

    if not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("project_id 只能包含字母、数字、下划线和短横线。")

def validate_thread_id(thread_id: str) -> None:
    """检查线程编号是否可以安全用于目录名。"""

    if not PROJECT_ID_PATTERN.fullmatch(thread_id):
        raise ValueError("thread_id 只能包含字母、数字、下划线和短横线。")   



@dataclass
class ProjectContext:
    """一个项目在大沙箱中的全部地址。"""

    project_id: str
    sandbox_root: Path
    checkpoint_path: Path
    reports_root: Path

def resolve_project_context(managed_sandbox: Path,project_id: str,)->ProjectContext:    

    """根据 project_id 创建并返回项目目录。"""
    validate_project_id(project_id)

    managed_root = managed_sandbox.resolve()

    sandbox_root = managed_root / "projects" / project_id
    project_data_root = managed_root / "data" / "projects" / project_id
    checkpoint_path = project_data_root / "checkpoint.db"
    reports_root = project_data_root / "reports"

    if not sandbox_root.is_relative_to(managed_root):
        raise ValueError("项目目录不能离开大沙箱。")

    if not project_data_root.is_relative_to(managed_root):
        raise ValueError("项目数据目录不能离开大沙箱。")

    sandbox_root.mkdir(parents=True, exist_ok=True)
    reports_root.mkdir(parents=True, exist_ok=True)

    return ProjectContext(
        project_id=project_id,
        sandbox_root=sandbox_root,      
        checkpoint_path=checkpoint_path,
        reports_root=reports_root,
    )


@contextmanager
def project_lock(context: ProjectContext) -> Iterator[None]:
    """同一时间只允许一个任务修改当前项目。"""

    lock_path = context.checkpoint_path.parent / ".write.lock"

    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open(mode="w",encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(),fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(),fcntl.LOCK_UN)