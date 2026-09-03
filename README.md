# 第九阶段：应用级 Multi-Agent Harness + Stage 9 Plus

状态：已完成

```text
第九阶段：[■■■■■]
最终检查点：核心 Harness、连续聊天、Checkpoint、滚动摘要、多项目管理、本地 Tool 自动发现、ToolRegistry、Exa 远程 MCP 和按角色最小权限注入均已完成真实验收
```

这一阶段学习的不是如何使用 Codex 插件，而是如何在自己的 Python 应用中真正实现一套 Multi-Agent 系统：Main Agent 负责协调，多个专业 Agent 分工处理任务，Pydantic 契约负责交接，Python 负责文件、测试和路由等确定性操作。

## 本阶段要解决什么问题

单个 Agent 同时规划、读项目、写代码、审查和测试时，很容易职责混乱，也容易越权执行副作用。本项目把工作拆成明确角色：

```text
Main Agent（项目经理）
├── Planner（制定计划）
├── Explorer（调查项目事实）
├── Implementer（提出文件修改）
├── Reviewer（静态代码审查）
├── Tester（运行受控功能测试，已接入 Graph）
└── Verifier（最终核验，已接入 Graph）
```

Main Agent 加上六个专业 Subagent，一共是七个 Agent。七个角色已经接入项目级 LangGraph；Reviewer、Tester、Verifier 三个质量门通过后，Verifier Main 会把状态置为 `completed`，Main Agent 再输出最终汇总。

所有 Agent 共用真实 `qwen-plus`，但拥有不同的 System Prompt、职责和输入上下文。它们不会自动共享前面发生的事情；当前由 `langgraph_main.py` 启动项目级 LangGraph，通过 `MultiAgentState` 显式传递计划、报告、代码版本和项目快照。

## 目标完整工作流

本项目最终采用“三个串行质量门，每个后续质量门失败后都从 Reviewer 重新开始”的流程。

```text
用户任务
→ Main Agent
→ Planner
→ Main Agent
→ Explorer
→ Main Agent
→ Implementer
→ Python 受控写入

→ Reviewer 质量门
   ├─ 失败：Reviewer 报告 Main
   │        → Main 委派 Implementer 修复
   │        → 修复后重新进入 Reviewer
   │        → 循环直到 Reviewer 通过
   └─ 通过：Main 保留 Reviewer 报告
            → 进入 Tester

→ Tester 质量门
   ├─ 失败：Tester 报告 Main
   │        → Main 委派 Implementer 修复
   │        → 从 Reviewer 重新开始
   │        → Reviewer 通过后再次进入 Tester
   └─ 通过：Main 保留 Tester 报告
            → 进入 Verifier

→ Verifier 质量门
   ├─ 失败：Verifier 报告 Main
   │        → Main 委派 Implementer 修复
   │        → 从 Reviewer 重新开始
   │        → 依次重新通过 Reviewer、Tester、Verifier
   └─ 通过：Main 汇总 Reviewer、Tester、Verifier 三份报告
            → 编写最终报告
            → 项目结束
```

这张图已经同时是当前成功主线的实际架构。规划阶段有限重规划、Reviewer 有限修复、Tester 失败回退，以及 Reviewer → Tester → Verifier → Main → `completed` 的完整成功路线都已有真实运行证据。后续自定义需求的最终状态还记录了 `tester_repair_count=1` 和 `verifier_repair_count=1`，最终仍收敛到 `completed`。

## 当前已经跑通的流程

先前的聚焦质量门验收真实触发过 Tester 失败路线：

```text
Reviewer 通过
→ Tester 调用 python_project_tests
→ 项目没有 tests/test_*.py
→ Runner 返回 exit_code=2
→ TesterReport.passed=false
→ test_main 返回 Implementer，tester_repair_count=1/3
→ Implementer 创建并修复 tests/test_todo.py
→ Reviewer 再次通过
→ Tester 真实执行 15 个 unittest
→ TesterReport.passed=true
→ test_main 将下一站设为 Verifier
```

随后最新一次完整真实入口跑通了成功主线：

```text
Planner 第 1 版计划通过
→ Explorer 批准
→ Implementer 受控写入
→ ReviewerReport.passed=true
→ Tester 实际执行 17 项 unittest，全部通过
→ Verifier 逐项确认新增、查看和完成三个需求
→ VerifierReport.passed=true
→ Main Agent 输出最终汇总
→ phase=completed
→ status=completed
→ next_role=None
→ verifier_passed=True
```

这次固定任务运行中 `plan_revision=1`、`replan_count=0`，Reviewer、Tester、Verifier 三类修复计数均为 `0`。它证明 Verifier Node、Verifier Main、最终状态和成功出口实际执行过，而不是只存在于 Graph 定义中。

随后，终端输入的自定义需求也真实跑通：

```text
plan_revision: 3
replan_count: 2
plan_approved: True
phase: completed
status: completed
next_role: None
review_repair_count: 0
tester_repair_count: 1
max_tester_repairs: 3
verifier_repair_count: 1
max_verifier_repairs: 3
verifier_passed: True
```

这份结果证明动态输入不是只通过语法检查，而是已经进入真实 Multi-Agent Graph；任务经历重新规划、Tester 返工和 Verifier 返工后，最终通过全部质量门。第九阶段 Harness 随后从阶段目录运行本地回归测试，`10` 项全部通过。2026-08-29 的离线复查中，`practice_sandbox` 内待办和记账项目共 `32` 项功能测试通过。

Reviewer、Tester、Verifier 报告既保留在 Graph State 中，也会按 `project_id + thread_id` 写入独立磁盘目录；Graph 状态和会话历史由项目自己的 SQLite Checkpoint 持久化。

## 当前目录结构

```text
hands_on/09_multi_agent_harness/
├── .env                         # 本地 DASHSCOPE_API_KEY，不提交 Git
├── README.md                    # 第九阶段学习记录
├── llm.py                       # 创建所有 Agent 共用的 qwen-plus
├── main.py                      # 早期普通 Python 顺序编排入口
├── langgraph_main.py            # 终端动态输入与项目级 LangGraph 运行入口
├── chat_cli.py                  # 选择 project_id、thread_id 并连续输入任务
├── checkpoint_reader.py         # 按项目和会话读取 SQLite 存档
├── project_manager.py           # 项目目录、ID 校验和进程锁
├── report_store.py              # 三份质量报告持久化
├── pyproject.toml               # 阶段独立依赖
├── uv.lock                      # 锁定依赖
├── agents/
│   ├── main_agent/              # Main Agent
│   ├── planner/                 # Planner Agent
│   ├── explorer/                # Explorer Agent
│   ├── implementer/             # Implementer Agent
│   ├── reviewer/                # Reviewer Agent
│   ├── tester/                  # Tester Agent，已接入 Graph
│   └── verifier/                # Verifier Agent，已接入 Graph
├── contracts/
│   ├── __init__.py
│   ├── file_change.py           # FileChange 结构化写入契约
│   ├── explorer_report.py       # ExplorerReport
│   └── quality_report.py        # 三个质量门的结构化报告
├── safety/
│   ├── __init__.py
│   ├── reader.py                # 受控项目读取
│   ├── route_guard.py           # 沙箱路径边界校验
│   ├── writer.py                # create / replace 受控写入
│   ├── test_runner.py           # Tester 白名单测试工具入口
│   └── project_test_harness.py  # 通用 Python 项目测试协议
├── workflow/
│   ├── __init__.py
│   ├── state.py                 # MultiAgentState
│   ├── nodes.py                 # Node 构造与依赖注入入口
│   ├── node_handlers/           # 按角色拆分的 Node 实现
│   │   ├── common.py            # 递归生成项目快照
│   │   ├── planner.py
│   │   ├── explorer.py
│   │   ├── implementer.py
│   │   ├── reviewer.py
│   │   ├── tester.py
│   │   ├── verifier.py
│   │   └── main.py              # planning/review/test/verifier 四个 Main Node
│   ├── routes.py                # 路由模块预留
│   └── graph.py                 # StateGraph、条件边和循环出口
├── tests/
│   ├── test_main_nodes.py
│   ├── test_planning_loop.py
│   ├── test_project_snapshot.py
│   ├── test_quality_gate_routing.py
│   ├── test_safe_reader.py
│   ├── test_test_runner.py
│   ├── test_tester_prompt.py
│   ├── test_implementer_prompt.py
│   ├── test_conversation_history.py
│   ├── test_conversation_summary.py
│   ├── test_project_manager.py
│   ├── test_project_runtime.py
│   └── test_report_store.py
└── practice_sandbox/
    ├── projects/<project_id>/   # 各项目独立源码目录，运行时按需创建
    ├── data/projects/<project_id>/
    │   ├── checkpoint.db        # 项目自己的任务档案
    │   └── reports/<thread_id>/ # 当前会话的三份质量报告
    └── ...                      # 早期单项目练习产物
```

Tester、Verifier、白名单 Runner、通用 Python 测试协议和三个质量门都已接入当前 Graph。Tester 通过后进入 Verifier；Verifier 通过后由 `verifier_main` 写入 `completed`，失败时按有限计数返回 Implementer 或进入明确失败出口。

## 分层架构

项目不是让大模型直接控制一切，而是分成四层：

```text
Agent 层
  负责理解任务、规划、调查、生成修改和语义审查

Contract 层
  把 Agent 的关键输出约束成可校验的 Pydantic 对象

Safety 层
  校验路径与操作类型，执行真正的文件系统副作用

Workflow 层
  决定 Agent 顺序、质量门、回退路线和结束条件
```

当前 Agent、Contract、受控写入、受控测试和 Workflow 已接通到 Verifier 与最终 Main 汇总。`workflow/graph.py` 使用 `StateGraph` 注册节点和条件边，`workflow/state.py` 保存跨节点状态，`workflow/node_handlers/` 按角色实现节点行为，`workflow/nodes.py` 负责组装节点，`langgraph_main.py` 负责接收终端需求、构造初始状态并启动工作流。

Node 工程化拆分和成功主线已经完成。当前重点不再是增加 Agent，而是补齐 Verifier 失败路线的真实验收、修复旧回归测试，并逐步增加动态交互、记忆、项目隔离和统一能力库。

## Agent 职责与边界

| 角色 | 当前职责 | 输出方式 | 禁止事项 |
| --- | --- | --- | --- |
| Main Agent | 整理委派说明、接收报告、表达下一站 | 普通消息 | 不直接写业务代码或文件 |
| Planner | 把目标拆成三个可执行步骤 | 普通消息 | 不读取项目、不写代码、不改文件 |
| Explorer | 根据 Python 提供的快照报告现状与缺失 | 普通消息 | 不猜测快照外事实、不代替 Planner |
| Implementer | 每轮提出一项完整文件修改 | `FileChange` Tool 参数 | 不直接访问文件系统、不删除文件 |
| Reviewer | 根据目标、报告、修改和最新源码做静态审查 | `ReviewerReport` Tool artifact | 不修改文件、不伪称测试通过 |
| Tester | 选择并运行预先允许的项目测试，再结合真实输出判断需求是否被覆盖 | `TesterReport` Tool artifact | 不能运行任意命令，不能把“零测试”判为通过 |
| Verifier | 最终核对目标、最新代码和前两份质量报告 | `VerifierReport` Tool artifact | 不能跳过 Reviewer、Tester，也不能脱离证据宣称需求满足 |

Main Agent 负责“理解和委派”，但当前真正调用各 Agent、执行写入以及判断 `passed` 分支的是确定性的 Python 主控代码。这种分工让模型负责语义判断，让 Python 负责可验证的控制和副作用。

## 上下文如何交接

这些 Agent 没有自动共享记忆。当前各个 Graph Node 会从 `MultiAgentState` 读取所需信息，再明确拼装下一个 Agent 需要的上下文：

```text
原始用户任务
＋ Planner 报告
＋ Explorer 报告
＋ 本轮 FileChange
＋ 写入后的当前源码快照
→ 交给对应 Agent
```

这体现了 Multi-Agent 的一个核心知识：Subagent 不应该默认知道其他 Agent 做过什么；主控程序必须决定传递哪些事实，避免上下文遗漏，也避免把无关内容全部塞给每个 Agent。

## 结构化交接契约

### `FileChange`

Implementer 不返回一段模糊的“我改好了”，而是提交：

| 字段 | 含义 |
| --- | --- |
| `relative_path` | 相对于 `practice_sandbox` 的目标路径 |
| `operation` | 只能是 `create` 或 `replace` |
| `content` | 目标文件的完整内容 |
| `rationale` | 本次修改理由 |

数据流：

```text
Implementer 生成工具调用参数
→ Python 提取 AIMessage.tool_calls
→ Pydantic 校验为 FileChange
→ Safety 层决定是否允许写入
```

每轮必须且只能提交一个 `FileChange`，当前也只允许修改一个文件。

### `GateFinding`

Reviewer 的每个问题都必须包含：

- `category`：问题类别。
- `severity`：只能是 `blocking` 或 `advisory`。
- `message`：问题说明。
- `evidence`：来自当前源码的证据。
- `suggested_fix`：建议修复方式。

这些必填字段防止 Reviewer 只给结论却不给证据或修复方向。

### `ReviewerReport`

ReviewerReport 包含：

| 字段 | 含义 |
| --- | --- |
| `passed` | Reviewer 质量门是否通过 |
| `revision` | 当前产物版本，必须大于等于 1 |
| `findings` | `GateFinding` 列表 |

Pydantic 还会检查报告内部是否自相矛盾：

```text
存在 blocking finding
→ passed 不能是 true

passed 是 false
→ 至少必须有一个 blocking finding
```

## `AIMessage` 与 `ToolMessage`

当前两个结构化 Agent 的提取方式不同：

```text
Implementer
→ 模型在 AIMessage.tool_calls 中提出 submit_file_change 参数
→ Python 从工具调用参数构造 FileChange

Reviewer
→ submit_reviewer_report 工具校验并返回 content + artifact
→ LangChain 产生 ToolMessage
→ Python 从成功的 ToolMessage.artifact 构造 ReviewerReport
```

因此 Implementer 提取器检查 `AIMessage`，Reviewer 提取器检查 `ToolMessage`。把 Reviewer 的工具结果误当成 `AIMessage`，会导致明明已经成功调用工具，提取器仍然找到 0 份报告。

## Python 受控写入

Implementer 只能提出 `FileChange`，真正的写入经过下面的确定性边界：

```text
FileChange
→ resolve_sandbox_path()
→ 检查是否为相对路径
→ resolve() 解析最终绝对路径
→ relative_to() 确认仍在 practice_sandbox 内
→ 检查 create / replace 前置条件
→ UTF-8 写入
```

已经实现的规则：

- 拒绝绝对路径和带盘符的路径。
- 拒绝通过 `../` 逃出 `practice_sandbox`。
- 拒绝把沙箱根目录本身当作目标文件。
- `create` 遇到已存在目标时失败，防止静默覆盖。
- `replace` 要求目标必须是已存在的文件。
- 不支持 `delete`。
- Python 校验完成前，Implementer 的内容不会写入磁盘。

这个设计的核心是：模型可以建议副作用，但只有 Python 安全层有权执行副作用。

## Reviewer 质量门

Reviewer 收到的不是单独一段代码，而是完整审查上下文：

```text
原始用户任务
＋ Planner 报告
＋ Explorer 报告
＋ 本轮 FileChange
＋ 写入后的项目源码快照
＋ artifact revision
→ ReviewerReport
```

Reviewer 只做静态审查。它会检查功能缺失、逻辑错误、异常处理和任务越界，并把问题分成：

- `blocking`：影响需求、正确性或安全，质量门不能通过。
- `advisory`：改进建议，不阻止进入下一质量门。

本次真实运行的 ReviewerReport 通过了 Pydantic 校验，`passed=true`，所以 Python 选择 Tester 路线。

## Tester 质量门

Tester 不只是检查 Python 能不能编译，也不只测试某一种待办项目。它面向 Implementer 产出的任意 Python 项目，工作过程是：

```text
原始用户任务 + 已批准计划 + 当前项目快照 + artifact revision
→ Tester 选择固定的 python_project_tests
→ Python Runner 递归编译项目中的 .py 文件
→ 从 tests/test_*.py 发现并执行 unittest
→ Tester 根据真实退出码、输出和需求覆盖情况生成 TesterReport
```

安全边界和通过条件：

- Agent 只能传入白名单 `test_id`，不能拼接 Shell 命令。
- Runner 使用 `shell=False`，在项目沙箱内运行，并设置 `10` 秒超时。
- 任意 Python 文件语法失败返回 `exit_code=3`。
- 没有发现功能测试返回 `exit_code=2`，不能把“零测试”当成通过。
- 测试断言失败返回 `exit_code=1`；全部通过才返回 `exit_code=0`。
- `TesterReport.revision` 必须等于当前 `artifact_revision`；存在失败结果或 `blocking` finding 时，`passed` 不能为 `true`。
- Tester 还要判断测试是否覆盖原始需求。命令成功只证明已执行的测试通过，不自动证明项目所有功能都正确。

## Verifier 质量门

Verifier 是最后一个需求验收角色。它不重新运行任意命令，而是读取原始任务、当前项目快照、代码版本、ReviewerReport 和 TesterReport，再逐项判断需求是否同时具有实现证据和测试证据：

```text
原始用户任务 + 当前项目快照 + artifact revision
＋ ReviewerReport + TesterReport
→ Verifier 逐条核对需求
→ 输出结构化 VerifierReport
→ verifier_main 根据 passed 和修复次数决定完成、返工或失败
```

当前 Python 主控会检查 `VerifierReport.revision` 必须等于最新 `artifact_revision`。成功时写入 `phase=completed`、`status=completed`、`next_role=None`；失败且未达到上限时返回 Implementer，随后重新经过 Reviewer、Tester 和 Verifier；达到上限时进入明确的 `failed` 出口。

最新一次真实成功主线中，Verifier 分别核对了新增、查看和完成三个待办需求，给出 `passed=true`，随后 Main Agent 输出最终汇总。失败返工和上限耗尽虽然已经写入 Graph 与 Python 路由，但尚未用真实 Verifier 失败报告完成验收。

## Workflow State 与当前 Graph

`workflow/state.py` 的 `MultiAgentState` 已经用于当前 LangGraph，主要保存：

- 阶段：`planning`、`exploring`、`implementing`、`reviewing`、`testing`、`verifying`、`completed`、`failed`。
- 角色：Main、Planner、Explorer、Implementer、Reviewer、Tester、Verifier。
- 产物信息：`artifact_revision`、`changed_files`、`pending_file_changes`。
- 当前报告：Explorer、Reviewer、Tester 和 Verifier 报告。
- 循环计数：`replan_count`、`review_repair_count`、`tester_repair_count`、`verifier_repair_count` 及各自上限。

当前 Graph 已接入 `planner`、`explorer`、`planning_main`、`implementer`、`reviewer`、`review_main`、`tester`、`test_main`、`verifier` 和 `verifier_main`。规划失败会有限返回 Planner；Reviewer、Tester 或 Verifier 失败都会有限返回 Implementer，并从 Reviewer 重新经过后续质量门；Verifier 通过后进入 `completed`，所有失败出口最终进入 `END`。

## 本阶段已经学到的知识

- Multi-Agent 的重点不是 Agent 数量，而是职责边界和可靠交接。
- Main Agent 负责协调，不应该亲自包办所有专业工作。
- 每个 Subagent 只接收完成本职工作所需的上下文。
- 普通文本适合计划和事实报告；会驱动副作用或质量路由的输出应结构化。
- Pydantic 不只检查字段类型，还能检查报告内部业务规则。
- 模型负责语义判断，Python 负责路径、写入和分支等确定性控制。
- `AIMessage.tool_calls` 表示模型请求调用工具；`ToolMessage` 表示工具执行后的结果。
- Reviewer 通过只代表静态审查通过，不能替代真实测试。
- Tester 必须依据 Runner 的真实退出码和输出判断，发现零测试时也必须失败。
- Tester 报告是修复证据，不是必须照抄的修改命令；Implementer 要先判断失败来自产品代码还是测试代码，不能为了迁就错误测试随意扩展产品 API。
- 对文件读写功能做测试时，应使用临时目录隔离副作用，不能污染 `practice_sandbox` 的真实数据。
- Verifier 必须逐条核对用户需求、代码和测试证据，不能因为 Reviewer 与 Tester 都通过就自动通过。
- `next_role` 只是 State 中的数据，真正的执行路线必须由 `add_conditional_edges()` 映射到对应 Node。
- 后续质量门失败后从 Reviewer 重跑，可以防止修复一个问题时破坏已经审查过的代码。
- 质量循环必须有最大修复次数和明确失败出口，不能无限调用模型。

## 当前阶段边界

核心 Harness 和 Stage 9 Plus 已经完成全部约定验收：自定义终端需求真实跑到 `completed`，连续聊天、上下文记忆、多项目管理和 MCP/Tool 能力库全部接通。最终完整回归运行 `73` 项并得到 `OK (skipped=1)`，默认跳过的真实 Exa 集成测试随后显式联网运行并 `1 / 1` 通过。

最终补齐：

- 同一 `thread_id` 通过 SQLite Checkpoint 继续原会话，不同 `thread_id` 相互隔离。
- Planner 使用“滚动摘要 + 最近需求 + 结构化 State”，避免长对话一直携带全部原文。
- `project_id` 决定独立的源码目录、Checkpoint 和质量报告目录，所有项目仍位于同一个大 Sandbox 内。
- 同一项目通过进程锁串行执行，避免两个任务同时覆盖项目产物。
- Reviewer、Tester、Verifier 三份报告按 `thread_id` 保存为 JSON。
- 建立 `capabilities/` 专属能力包和中央 `ToolRegistry`，统一登记本地 Tool、现有 Harness Tool 和 MCP Tool，并保存来源、角色权限与超时配置。
- 自动扫描 `capabilities/local_tools/`；以后新增符合插件契约的本地 Tool 时，不需要修改 Agent 或中央注册表源码。
- 使用 `MultiServerMCPClient` 连接 Exa 远程 MCP，只加载白名单 `web_search_exa` 和 `web_fetch_exa`，让 Multi-Agent 能够搜索互联网并读取网页。
- 按 Agent 角色注入最小工具集合，同时保持项目快照、Implementer 安全写入和 Tester 白名单命令的现有 Python 边界，不再重复建设项目文件 MCP。
- Planner 可按需调用 Exa 搜索和读取网页；Explorer 的搜索与网页读取总计最多三次，之后必须提交一份结构化报告。
- 毕业项目 `stage9-exa-graduation` 使用同一 `project_id + thread_id=final` 保留失败现场并继续修复，最终得到 `phase=completed`、`status=completed`、`checkpoint_status=completed` 和 `verifier_passed=True`。

项目级 RAG 保留为后续增强，不阻塞第十阶段；配置、结构化日志、恢复、健康检查和可观测性等生产工程内容进入第十阶段“生产级并发与云部署”。Checkpoint 当前会提示 Pydantic 报告类型尚未注册到严格 msgpack 白名单；它不影响本阶段验收，但应在第十阶段通过保存普通字典或显式白名单完成兼容性处理。

## 环境与依赖

`pyproject.toml` 当前声明：

- Python `>=3.10`
- `dashscope`
- `langchain`
- `langchain-community`
- `langgraph`
- `langgraph-checkpoint-sqlite`
- `python-dotenv`
- `pydantic`

所有 Agent 当前共用：

```python
ChatTongyi(model="qwen-plus", temperature=0)
```

真实密钥只允许写在本阶段的 `.env`：

```dotenv
DASHSCOPE_API_KEY=
```

`.env` 已被仓库 `.gitignore` 忽略。不得把真实 Key 写入 README、Python 文件、终端截图或 Git 历史。

## 运行当前项目

```powershell
cd G:\codextest\LangChain_learning\hands_on\09_multi_agent_harness
.\.venv\Scripts\python.exe .\chat_cli.py
```

程序会调用多个真实模型 Agent，并可能根据 Implementer 结果在 `practice_sandbox` 内创建或替换文件。`VIRTUAL_ENV` 不匹配提示只是环境选择警告；只要程序继续运行并到达预期输出，就不等于执行失败。

启动后程序会先选择项目和会话档案号，再持续接收需求：

```text
请输入 project_id（直接回车使用 default-project）：
请输入 thread_id（直接回车使用 stage9-main-thread）：
请输入需求（输入 exit、quit 或退出,来结束程序）：
```

输入一条任务后，`chat_cli.main()` 会把 `user_request`、`project_id` 和 `thread_id` 交给 `run_task()`。任务完成后程序会重新显示输入提示；空输入会要求重新输入，`exit`、`quit`、`退出`、EOF 或 `Ctrl+C` 会结束程序。同一 `project_id + thread_id` 会在下一轮或程序重启后继续原会话；更换 `thread_id` 会得到独立会话，更换 `project_id` 会同时切换源码、Checkpoint 和报告目录。

当前已经验证过的 Tester 失败路线：

```text
Reviewer 报告不通过
→ review_main_node 返回 Implementer 修复
→ 重新写入并再次进入 Reviewer

Reviewer 通过
→ Tester 运行白名单 python_project_tests

没有测试
→ Runner exit_code: 2
→ Tester passed: false
→ test_main 返回 Implementer（tester_repair_count: 1 / 3）

Implementer 补充或修复测试
→ 重新经过 Reviewer
→ Tester 实际执行 15 项 unittest 并全部通过
→ phase: verifying
→ status: running
→ next_role: verifier
```

当前已经验证过的自定义动态需求最终状态：

```text
plan_revision: 3
replan_count: 2
plan_approved: True
phase: completed
status: completed
next_role: None
review_repair_count: 0
tester_repair_count: 1
max_tester_repairs: 3
verifier_repair_count: 1
max_verifier_repairs: 3
verifier_passed: True
```

这次自定义需求运行经历两次重新规划、一次 Tester 返工和一次 Verifier 返工，Main Agent 最后输出完成汇总。第九阶段 Harness 本地回归测试也已经 `10 / 10` 通过。

## Stage 9 Plus 路线

Stage 9 Plus 的四项内容均已在当前 `09_multi_agent_harness` 目录中完成：

```text
[x] 连续聊天
[x] 上下文记忆
[x] 多项目管理
[x] MCP/Tool 毕业项
```

### 1. 连续聊天

在当前 `run_task()` 外建立连续输入循环。一次任务完成后不退出，用户可以继续补充要求、开始新任务或输入退出命令；每一轮仍复用现有质量门，不绕过 Planner、Reviewer、Tester 和 Verifier。

该入口已经在 `chat_cli.py` 中实现并完成真实验收：一轮“每日记账软件”任务经过 Planner、Explorer、Implementer、Reviewer、Tester 和 Verifier 后达到 `completed`，程序随后再次显示输入提示，并能通过 `Ctrl+C` 正常退出。连续输入完成后，跨轮记忆已在下一项中补齐。

### 2. 上下文记忆与压缩

这一项已经完成。程序使用项目级 SQLite Checkpointer 和 `thread_id` 保存对话、Graph 状态、代码版本与质量报告。完整原始记录负责存档，真正传给 Planner 的工作上下文采用“滚动摘要 + 最近需求 + 结构化状态”：

```text
完整历史写入 Checkpoint
→ 计算当前工作上下文大小
→ 未达到阈值：继续使用当前消息
→ 达到阈值：用 qwen-plus 更新 conversation_summary
→ 保留最近若干轮原始消息
→ Agent 接收 summary + recent_messages + 当前结构化 State
```

`user_request`、`project_id`、`sandbox_root`、计划、当前版本、修复计数和最新质量报告继续保留为独立 State 字段，不依赖自然语言摘要驱动 Graph 路由。自动化测试已经覆盖同线程历史累积、不同线程隔离、摘要触发和 Planner 使用摘要与最近需求。

### 3. 多项目管理

这一项已经完成。所有项目都位于 `practice_sandbox` 这个大 Sandbox 中，但每个 `project_id` 分别拥有 `projects/<project_id>` 源码目录和 `data/projects/<project_id>` 数据目录。每个项目使用独立 SQLite Checkpoint、报告目录和进程锁；即使两个项目使用相同 `thread_id`，状态也不会串联。

### 4. MCP/Tool 能力库

这一毕业项已经完成。它没有重复建设沙箱文件读取，而是让当前 Multi-Agent 同时获得“项目内可扩展的本地 Tool”和“来自外部 MCP 服务的联网能力”。模型仍统一由 `llm.py` 创建；所有新能力平台代码集中放入 `capabilities/`：

```text
capabilities/
├── __init__.py
├── bootstrap.py              # 组装本地、Harness 与远程 Tool
├── contracts.py              # AgentRole 与 Tool 注册契约
├── registry.py               # 自动发现、统一登记和按角色发放
├── local_tools/
│   ├── __init__.py
│   └── text_stats.py         # 第一个无副作用本地 Tool 示例
└── remote_tools/
    ├── __init__.py
    └── exa/
        ├── __init__.py
        ├── config.py         # Exa 连接配置与密钥请求头
        ├── policy.py         # 纯参数校验和不可信内容格式化
        ├── client.py         # 白名单远程 Tool 加载
        └── bridge.py         # 异步 MCP Tool 到同步 Graph 的桥接
```

每个 `local_tools/*.py` 模块导出 `TOOL_REGISTRATIONS`，其中声明真实 `BaseTool`、来源、允许角色和超时。程序启动时自动扫描这些可信模块；以后只需增加符合契约的新 Tool 文件，重启程序后即可进入注册表，不需要继续修改各个 Agent。

外部能力使用 Exa 的远程 Streamable HTTP MCP：

```text
web_search_exa  → 根据关键词搜索互联网
web_fetch_exa   → 读取指定网页正文
```

`remote_tools/exa/client.py` 只接受这两个白名单工具。若存在 `EXA_API_KEY`，只通过 `x-api-key` 请求头发送；密钥不能进入源码、URL、日志或 Git。远程异步 Tool 会由 `bridge.py` 包装为当前同步 Graph 可以调用的 Tool，并受到明确超时和返回长度限制。

中央注册表按照最小权限发放：

```text
Planner      → 联网搜索、网页读取、允许的本地只读 Tool
Explorer     → 联网搜索、网页读取、本地只读 Tool、提交 ExplorerReport
Implementer  → 提交 FileChange
Reviewer     → 网页读取、本地只读 Tool、提交 ReviewerReport
Tester       → 白名单测试 Runner、提交 TesterReport
Verifier     → 网页读取、本地只读 Tool、提交 VerifierReport
Main Agent   → 无直接工具，只负责协调
```

Explorer 的强制报告中间件已经调整：不需要外部资料时可以直接提交报告；需要研究时最多进行三次搜索或网页读取，之后必须且只能提交一份 ExplorerReport。网页内容始终是不可信外部数据，不能把网页中的指令当成系统命令，也不能借此绕过 Writer、Runner 或角色权限。

验收已经证明：本地 Tool 可以自动发现；新增 Tool 时不修改 Agent 源码也能进入注册表；注册表拒绝重名、空角色和非法超时；各角色拿不到越权工具；Exa 非白名单工具不会进入系统；MCP 连接失败和调用超时会明确报错；当前同步 Graph 能调用远程异步 Tool；真实 Exa MCP 搜索和网页读取 `1 / 1` 通过；完整回归运行 `73` 项并得到 `OK (skipped=1)`。

第九阶段已经结束。第十阶段按根 README 的原计划进入 FastAPI、异步并发、多用户状态生命周期、Docker 和云部署；项目级 RAG 作为后续增强单独安排。

## 第九阶段完成标准

核心 Harness 当前完成情况：

- [x] Main 加六个 Subagent 的职责和输入输出边界全部落地。
- [x] Reviewer、Tester、Verifier 三个质量门在完整真实成功主线中均能通过。
- [x] 文件写入和测试命令受 Python 安全边界控制。
- [x] Main Agent 能接收 Verifier 报告、输出最终汇总并将 Graph 置为 `completed`。
- [x] LangGraph 的节点、条件边、状态和成功结束条件真实运行。
- [x] 自定义终端需求真实运行到 `completed`，并记录重新规划、Tester 返工和 Verifier 返工。
- [x] Harness 本地稳定测试 `10 / 10` 通过。

Stage 9 Plus 完成情况：

- [x] 连续聊天。
- [x] 基于 `thread_id` 的持久化上下文记忆与滚动摘要压缩。
- [x] 基于 `project_id` 的多项目管理、状态隔离、报告落盘与进程锁。
- [x] 本地 Tool 自动发现、Exa 远程 MCP 搜索/网页读取、中央 ToolRegistry 与 Agent 权限。

最终完整回归共运行 `73` 项，覆盖核心 Harness、上下文记忆、多项目管理、本地 Tool 自动发现、角色权限、Exa 策略与客户端、同步桥接、Explorer 研究上限以及 Workflow 工具注入，结果为 `OK (skipped=1)`；默认跳过的真实 Exa 集成测试随后显式联网运行并 `1 / 1` 通过。毕业项目功能测试 `2 / 2` 通过，整个第九阶段标记为“已完成”，下一阶段为原定的“生产级并发与云部署”。
# MultiAgent_Software_Engineering_Harness-NII
