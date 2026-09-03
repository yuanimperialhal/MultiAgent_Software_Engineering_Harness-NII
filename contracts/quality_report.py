from typing import Literal
from pydantic import BaseModel, Field, model_validator

class GateFinding(BaseModel):
    """质量门发现的一个问题。"""
    category: str = Field(min_length=1)    
    severity: Literal["blocking","advisory"]
    message: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    suggested_fix: str = Field(min_length=1)

    """
    GateFinding 模型的字段定义：

    category：问题类别，必须是至少包含 1 个字符的字符串。
    severity：问题严重程度，只允许为 "blocking"（阻塞）或 "advisory"（建议）。
    message：问题的简要说明，不能为空字符串。
    evidence：证明该问题存在的依据或证据，不能为空字符串。
    suggested_fix：建议的修复方案，不能为空字符串。
    """

class ReviewerReport(BaseModel):
    """Reviewer 对某个代码版本的审查报告。"""

    passed: bool
    revision: int = Field(ge=1)
    findings: list[GateFinding] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_passed_status(self)->"ReviewerReport":
        """验证 passed 字段与 findings 列表的一致性。"""
        has_blocking = any(finding.severity == "blocking" for finding in self.findings)
        if self.passed and has_blocking:
            raise ValueError("存在 blocking 问题时不能通过。")
        if not self.passed and not has_blocking:
            raise ValueError("未通过时至少需要一个 blocking 问题。")
        return self


class TestRunResult(BaseModel):
    """Python 受控测试执行器返回的一项真实结果。"""
    test_id: str = Field(min_length=1)#测试的唯一标识符，必须是至少包含 1 个字符的字符串。
    command: list[str] = Field(min_length=1)#执行测试的命令列表，不能为空列表。
    exit_code: int #测试执行的退出代码，整数类型。
    stdout: str = "" #测试执行的标准输出，字符串类型。
    stderr: str = "" #测试执行的标准错误输出，字符串类型。

class TesterReport(BaseModel):
    """Tester 对某个代码版本的测试报告。"""

    passed: bool
    revision: int = Field(ge=1)#测试报告对应的代码版本号，必须是大于等于 1 的整数。
    test_results: list[TestRunResult] = Field(min_length=1)#测试结果列表，默认为空列表。
    findings: list[GateFinding] = Field(default_factory=list)#测试中发现的问题列表，默认为空列表。

    @model_validator(mode="after")
    def validate_passed_status(self)->"TesterReport":
        """验证 passed 字段与 findings 列表的一致性。"""
        has_failed_tests = any(result.exit_code != 0 for result in self.test_results)

        has_blocking = any(finding.severity == "blocking" for finding in self.findings)

        if self.passed and has_failed_tests:
            raise ValueError("存在失败的测试时不能通过。")

        if self.passed and has_blocking:
            raise ValueError("存在 blocking 问题时不能通过。")

        if not self.passed and not has_blocking:
            raise ValueError("Tester 未通过时至少需要一个 blocking 问题。")
        return self

class VerificationCheck(BaseModel):
    """Verifier 对一项用户需求的核验结果。"""
    requirement: str = Field(min_length=1)#用户需求的描述，必须是至少包含 1 个字符的字符串。
    satisfied: bool #该需求是否满足，布尔类型。
    evidence: str = Field(min_length=1)#证明该需求满足或不满足的依据，不能为空字符串。

class VerifierReport(BaseModel):
    """Verifier 对某个代码版本的最终核验报告。"""

    passed: bool
    revision: int = Field(ge=1)#核验报告对应的代码版本号，必须是大于等于 1 的整数。
    checks: list[VerificationCheck] = Field(min_length=1)#核验检查列表，默认为空列表。
    findings: list[GateFinding] = Field(default_factory=list)#核验中发现的问题列表，默认为空列表。

    @model_validator(mode="after")
    def validate_passed_status(self)->"VerifierReport":
        """验证 passed 字段与 findings 列表的一致性。"""
        has_failed_check = any(not check.satisfied for check in self.checks)

        has_blocking = any(finding.severity == "blocking" for finding in self.findings)

        if self.passed and has_failed_check:
            raise ValueError("存在未满足的需求时不能通过。")

        if self.passed and has_blocking:
            raise ValueError("存在 blocking 问题时不能通过。")

        if not self.passed and not has_blocking:
            raise ValueError("Verifier 未通过时至少需要一个 blocking 问题。")

        return self