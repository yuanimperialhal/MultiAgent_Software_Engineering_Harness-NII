from typing import Literal
from pydantic import BaseModel,Field


class FileChange(BaseModel):
    """Implementer 提交的一项文件修改。"""

    relative_path: str = Field(description="相对于 practice_sandbox 的文件路径")
    operation: Literal["create","replace"]= Field(description="文件操作类型：创建、替换")
    content: str = Field(description="需要写入文件的完整内容")
    rationale: str = Field(description="Implementer 提交该文件修改的理由")