from pydantic import BaseModel, Field,model_validator

class ExplorerReport(BaseModel):
    """Explorer 对当前计划的结构化检查报告。"""
    plan_approved:bool
    plan_revision:int = Field(ge=1)
    observations:list[str]=Field(min_length=1)
    replan_feedback:list[str]=Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan_result(self)->"ExplorerReport":
        """验证计划结果的合理性。"""
        if self.plan_approved and self.replan_feedback:
            raise ValueError("如果计划被批准，则 replan_feedback 应为空。")

        if not self.plan_approved and not self.replan_feedback:
            raise ValueError("如果计划未被批准，则 replan_feedback 不能为空。") 
        return self