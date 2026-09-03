import json
from pathlib import Path
from typing import Any

from project_manager import validate_thread_id


REPORT_FIELDS = {
    "reviewer.json": "reviewer_report",
    "tester.json": "tester_report",
    "verifier.json": "verifier_report",
}


def serialize_report(
    report: Any,
) -> Any:
    """把质量报告转换成可以写入 JSON 的数据。"""

    if report is None:
        return None

    if hasattr(report, "model_dump"):
        return report.model_dump(mode="json")

    if isinstance(report, dict):
        return report

    raise TypeError(
        f"不支持的质量报告类型：{type(report).__name__}"
    )


def save_quality_reports(
    reports_root: Path,
    thread_id: str,
    result: dict[str, object],
) -> None:
    """保存当前线程最新的三份质量报告。"""

    validate_thread_id(thread_id)

    safe_reports_root = reports_root.resolve()
    thread_reports_root = (
        safe_reports_root
        / thread_id
    ).resolve()

    if not thread_reports_root.is_relative_to(
        safe_reports_root
    ):
        raise ValueError(
            "质量报告目录不能离开项目沙箱。"
        )

    thread_reports_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    for filename, state_field in REPORT_FIELDS.items():
        report = result.get(state_field)
        report_data = serialize_report(report)

        report_path = (
            thread_reports_root
            / filename
        )

        report_path.write_text(
            json.dumps(
                report_data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )