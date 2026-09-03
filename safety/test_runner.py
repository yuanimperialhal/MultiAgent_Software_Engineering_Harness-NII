"""
这个文件的作用：

给 AI（Tester Agent）提供一个"安全的测试执行工具"。

为什么需要"安全"？
因为 AI 不能被允许随便执行任意命令（比如删除文件、访问网络等危险操作）。
所以这里做了一个"白名单机制"：
    - 只允许运行我们提前写死的几条命令；
    - AI 只能通过 test_id 选择预先注册的测试协议；
    - AI 无法自己拼接、修改命令内容。
"""

import subprocess
import sys
from pathlib import Path
from typing import Literal

from langchain.tools import tool
from langchain_core.tools import BaseTool

from contracts import TestRunResult


def build_test_runner_tool(sandbox_root: Path) -> BaseTool:
    """
    创建一个"只能运行白名单里测试"的 LangChain 工具。

    参数：
        sandbox_root: 测试运行时所在的文件夹路径（沙箱目录）。

    返回：
        一个可以被 Agent 调用的工具函数 run_allowed_test。
    """

    # 第一步：确认沙箱目录真实存在，避免后续运行测试时报错
    root = sandbox_root.resolve()

    if not root.is_dir():
        raise ValueError(f"测试沙箱不存在或不是目录：{root}")

    # 第二步：定义"白名单命令"。
    # Runner 执行固定脚本，Agent 不能自行拼接命令。
    harness_path = Path(__file__).with_name(
        "project_test_harness.py"
    ).resolve()

    # 白名单字典：test_id -> 具体要执行的命令
    # 以后如果要新增测试，只需要在这里加一条即可
    allowed_commands = {
        "python_project_tests": [
            sys.executable,
            str(harness_path),
        ],
    }

    # 第三步：定义真正暴露给 Agent 调用的工具函数
    @tool
    def run_allowed_test(
        test_id: Literal["python_project_tests"],
    ) -> str:
        """
        运行白名单中的一项测试，并返回测试结果（JSON 字符串）。

        test_id 只能是 python_project_tests，Agent 不能传入命令。
        """

        # 根据 test_id 查出真正要执行的命令
        command = allowed_commands[test_id]

        try:
            # 执行命令，并限制最多运行 10 秒，防止卡死
            completed = subprocess.run(
                command,
                cwd=root,              # 在沙箱目录下运行
                capture_output=True,   # 捕获输出内容
                text=True,             # 输出按文本处理，不是二进制
                encoding="utf-8",
                errors="replace",      # 遇到无法解码的字符时，用占位符代替，不报错
                timeout=10,            # 超时时间：10 秒
                check=False,           # 命令失败时不抛异常，由我们自己处理返回码
                shell=False,           # 不使用 shell，安全性更高
            )

            # 把执行结果封装成统一的结构体
            result = TestRunResult(
                test_id=test_id,
                command=command,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        except subprocess.TimeoutExpired:
            # 如果命令跑了超过 10 秒，则视为测试失败
            # exit_code=124 是 Linux/Unix 里表示"超时"的常见约定
            result = TestRunResult(
                test_id=test_id,
                command=command,
                exit_code=124,
                stdout="",
                stderr="测试超过 10 秒，已停止。",
            )

        # 把结果转成 JSON 字符串返回给 Agent
        return result.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )

    return run_allowed_test
