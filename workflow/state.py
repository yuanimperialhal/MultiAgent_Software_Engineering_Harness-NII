from operator import add
from typing import Literal,TypedDict,Annotated

from contracts import FileChange, ReviewerReport,TesterReport, VerifierReport


Phase = Literal[
    "planning",
    "exploring",
    "implementing",
    "reviewing",
    "testing",
    "verifying",
    "completed",
    "failed",
]

Status = Literal[
    "running",
    "completed",
    "failed",

]

RoleName = Literal[
    "main_agent",
    "planner",
    "explorer",
    "implementer",
    "reviewer",
    "tester",
    "verifier",
]

class MultiAgentState(TypedDict):
    """整个 Multi-Agent 工作流共享的任务状态。"""
    task_id: str
    project_id: str
    user_request: str

    conversation_history: Annotated[list[str],add]#这是一个列表，存储了整个 Multi-Agent 工作流中所有角色的对话历史记录。
    conversation_summary: str
    summarized_request_count: int
    
    phase: Phase
    status: Status
    next_role: RoleName | None

    sandbox_root: str
    project_snapshot: str

    artifact_revision: int
    changed_files: list[str]
    pending_file_changes: FileChange | None

    plan: str
    plan_revision: int
    plan_approved: bool | None
    replan_feedback: list[str]
    replan_count: int
    max_replans: int

    review_repair_count: int
    max_review_repairs: int


    explorer_report: str
    main_instruction: str
    
    reviewer_report: ReviewerReport | None
    tester_report: TesterReport | None
    tester_repair_count: int
    max_tester_repairs: int

    verifier_report: VerifierReport | None
    verifier_repair_count: int
    max_verifier_repairs: int


