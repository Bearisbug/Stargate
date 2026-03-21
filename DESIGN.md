# Stargate — 实验平台设计文档

> 版本 v0.3 · 草稿

| 模块 | 状态 |
|------|------|
| **执行模块 (Execution)** | 详细设计 |
| 环境模块 (Environment) | 接口草图，待展开 |
| 检测模块 (Monitor) | 接口草图，待展开 |

---

## 1. 项目概述

Stargate 是面向 ML 科研的**实验执行平台**，定位是**实验开展者**：接收上游给定的实验计划，自主完成环境准备、代码执行、结果监控的完整闭环。

**不在本系统范围内**：idea 发现、文献调研、论文写作。这些由上游系统（如 ARIS 等）负责，Stargate 的入口是 `ExperimentPlan`。

---

## 2. 执行流程与输入输出总览

### 2.1 顶层数据流

```
┌─────────────────────────────────────────────────────────────────┐
│  输入                                                            │
│    ExperimentPlan.md   ← 来自上游（人工 / idea agent）           │
│    EnvSpec             ← 从 Plan 中提取                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │     Environment 环境层       │
              │  EnvSpec → 拉镜像 → 启容器   │
              └──────────────┬──────────────┘
                             │ EnvHandle
              ┌──────────────▼──────────────┐
              │      Execution 执行层        │
              │   Plan + Handle → 循环执行   │──▶ ExperimentEvent stream
              └──────────────┬──────────────┘
                             │ ExperimentResult
              ┌──────────────▼──────────────┐
              │       Monitor 检测层         │
              │   事件流 → 可视化 + 报告     │
              └─────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  输出                                                            │
│    artifacts/          ← 模型 checkpoint、指标文件               │
│    EXPERIMENT_TRACKER.md ← 每轮执行状态                         │
│    experiment_report   ← HTML/PDF 实验报告                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 执行层内部循环

```
ExperimentPlan + EnvHandle
         │
         ▼
  ┌──── Round Loop ────────────────────────────────────────────┐
  │                                                            │
  │  Planner ──▶ 选下一个 run                                  │
  │      │                                                     │
  │      ▼                                                     │
  │  Executor(AgentBackend) ──▶ 写代码 / 跑脚本                │
  │      │                                                     │
  │      ▼                                                     │
  │  ResultVerifier ──▶ shell check + metric parse             │
  │      │                                                     │
  │      ▼                                                     │
  │  Manager(AgentBackend) ──▶ done / continue / blocked       │
  │      │                                                     │
  │      ▼                                                     │
  │  Tracker.update + EventEmitter.emit                        │
  │      │                                                     │
  │      └──▶ [停止？] ──是──▶ ExperimentResult               │
  │               │                                            │
  │              否                                            │
  │               └──▶ 下一轮                                  │
  └────────────────────────────────────────────────────────────┘
```

### 2.3 各阶段输入输出

| 阶段 | 输入 | 输出 |
|------|------|------|
| **环境层** | `EnvSpec`（framework、cuda、packages、GPU 数） | `EnvHandle`（容器 exec 入口 + 挂载路径） |
| **Planner** | `EXPERIMENT_TRACKER.md`（当前状态） | 下一个待执行 `RunConfig` |
| **Executor** | `RunConfig` + `EnvHandle` + operator messages | `AgentRunResult`（exit status、修改的文件、stdout） |
| **ResultVerifier** | `AgentRunResult` + acceptance check 命令 | `VerifyResult`（pass/fail + 从文件 parse 的实际 metric） |
| **Manager** | `VerifyResult` + 当轮摘要 | `Decision`（done / continue / blocked + reason） |
| **Tracker** | `Decision` + `VerifyResult` | 更新 `EXPERIMENT_TRACKER.md` + `round_N.json` |
| **Monitor** | `ExperimentEvent` 流 | 实时可视化 + 实验报告 |

### 2.4 停止条件

| 条件 | Manager 决策 | 说明 |
|------|-------------|------|
| 所有 claim 的 checks 全部通过 | `done` | 正常结束 |
| 无法继续（环境崩溃/代码根本性错误） | `blocked` | 需人工介入 |
| 连续 N 轮无文件变动 | — | stall detection，自动触发 blocked |
| 超出总 GPU budget | — | 强制停止 |
| 达到 `max_rounds` | — | 强制停止 |

---

## 3. 系统架构

系统分为三个相互解耦的模块，加一个横切所有模块的 AgentBackend 抽象层：

```
┌──────────────────────────────────────────────────────┐
│                       Stargate                        │
│                                                      │
│  ┌─────────────┐   ┌─────────────┐   ┌────────────┐ │
│  │ Environment  │──▶│  Execution  │──▶│  Monitor   │ │
│  │  (环境层)    │   │  (执行层)   │   │  (检测层)  │ │
│  └─────────────┘   └─────────────┘   └────────────┘ │
│                                                      │
│  └──────────────── AgentBackend (抽象层) ───────────┘ │
└──────────────────────────────────────────────────────┘
```

各模块职责严格单一，通过结构化接口（事件流 + 文件状态）通信，可独立开发和替换。

---

## 4. Agent Backend 抽象层

### 2.1 为什么需要这一层

执行层的核心操作（读写文件、执行命令、调用 LLM 推理）在不同 agent 平台上实现方式不同：

| 平台 | 执行方式 | 工具调用 | 会话模型 |
|------|---------|---------|---------|
| **Claude Code** | CLI 子进程 | 内置 bash/read/write | 单次对话，无持久 thread |
| **Codex CLI** | CLI 子进程 | 内置 shell | 持久 thread，可恢复 session |
| **OpenClaw** | Python SDK | 可扩展工具集 | 可配置 |
| **直接 API** | HTTP 调用 | 手动定义 function call | 无状态 |

如果执行层直接依赖某个平台，换平台就需要重写核心逻辑。抽象层解决这个问题。

### 2.2 AgentBackend 接口

```python
class AgentBackend(Protocol):
    """执行层与具体 agent 平台之间的统一接口"""

    @property
    def name(self) -> str:
        """后端标识，如 "claude-code", "codex", "openclaw" """

    def run(
        self,
        prompt: str,
        context: AgentContext,        # 当前轮的上下文（tracker、上轮结果等）
        tools: list[ToolSpec],         # 允许使用的工具列表
        session_id: str | None = None, # 支持会话恢复的后端使用此字段
    ) -> AgentRunResult:
        """触发一次 agent 执行，返回结构化结果"""

    def inject(self, session_id: str, message: str) -> None:
        """向进行中的 session 注入 operator 消息（不支持则 raise NotImplementedError）"""

    def is_session_resumable(self) -> bool:
        """该后端是否支持跨轮 session 恢复"""
```

```python
@dataclass
class AgentRunResult:
    exit_status: Literal["completed", "failed", "blocked"]
    summary: str                     # agent 自述完成了什么
    artifacts_modified: list[str]    # 修改过的文件路径
    stdout: str
    raw_events: list[dict]           # 后端原始事件流（调试用）
    session_id: str | None           # 供下一轮恢复使用
```

### 2.3 各后端特性对比

| 特性 | ClaudeCodeBackend | CodexBackend | OpenClawBackend | DirectAPIBackend |
|------|:-----------------:|:------------:|:---------------:|:----------------:|
| 会话恢复 | ✗ | ✓ | ✓ | ✗ |
| 本地文件操作 | ✓ | ✓ | ✓ | 需手动实现 |
| 无网络运行 | ✓（本地模型） | ✗ | 取决于部署 | ✗ |
| 工具可扩展 | 受限 | 受限 | ✓ | ✓ |
| 推荐场景 | 代码执行为主 | 长任务，需恢复 | 工具密集型任务 | 轻量推理 |

### 2.4 后端配置

后端通过配置文件指定，执行层运行时不感知具体平台：

所有 agent 角色（Executor、Manager、Planner）均通过 AgentBackend 统一接口调用，无特例。

```yaml
# stargate.yaml
agent_backend:
  executor:
    backend: "claude-code"
    model: "claude-sonnet-4-6"
  manager:
    backend: "direct-api"        # Manager 只需轻量推理，无需文件操作能力
    model: "claude-haiku-4-5"
  planner:
    backend: "direct-api"
    model: "claude-haiku-4-5"
```

---

## 5. 模块一：Environment（环境层）

> 状态：接口草图，详细设计待展开

### 5.1 职责

根据实验配置，在目标服务器上准备好可用的运行容器，对执行层屏蔽所有基础设施细节。

### 5.2 核心流程

```
输入：ExperimentPlan 中的 env_spec
    │
    ▼
① 需求解析
   └─ 提取依赖（framework、cuda 版本、python 包等）
    │
    ▼
② 镜像选择 / 构建
   ├─ 匹配现有基础镜像
   └─ 若无匹配：基于最近镜像生成 Dockerfile 差异层，云端 build
    │
    ▼
③ 镜像分发到目标服务器
   ├─ 有网：docker pull / registry 直接拉取
   └─ 离网：docker save → SSH 传输 → docker load
    │
    ▼
④ 容器启动 & 健康检查
   └─ 挂载工作目录、数据集路径、GPU 分配
    │
    ▼
输出：EnvHandle
```

### 5.3 接口定义

```python
@dataclass
class EnvSpec:
    framework: str
    framework_version: str
    cuda_version: str
    python_packages: list[str]
    gpu_count: int
    data_mounts: dict[str, str]   # {host_path: container_path}

@dataclass
class EnvHandle:
    container_id: str
    exec_fn: Callable[[str], ExecResult]  # 在容器内执行 shell 命令
    work_dir: str
    status: Literal["ready", "failed", "destroyed"]
```

### 5.4 基础镜像清单（初期）

| 标签 | 内容 |
|------|------|
| `base-pytorch-cu121` | Python 3.11 + PyTorch 2.2 + CUDA 12.1 |
| `base-pytorch-cu118` | Python 3.10 + PyTorch 2.0 + CUDA 11.8 |
| `base-jax-cu121`     | Python 3.11 + JAX 0.4 + CUDA 12.1 |
| `base-cpu`           | Python 3.11，无 GPU 依赖 |

---

## 6. 模块二：Execution（执行层）

### 4.1 职责

接收实验计划，通过 AgentBackend 在容器内自主执行实验，由 Manager 控制循环直到验收通过，持续向检测层发送结构化事件。

设计参考：
- **ArgusBot**：Round-based 状态机、loop control manager、shell 验收条件、operator inject 机制
- **ARIS**：Claim-driven 实验规划、sanity-first 部署、防幻觉结果验证、markdown tracker

### 4.2 输入格式

```markdown
# EXPERIMENT_PLAN.md

## Claim 1: 方法 X 在数据集 Y 上比 baseline 高 2%

### Run 1.0 — sanity
- 脚本: train.py --dataset Y --epochs 1 --model X
- 成功条件: exit 0, loss < 10.0
- GPU budget: 0.1h

### Run 1.1 — full
- 脚本: train.py --dataset Y --epochs 50 --model X
- 成功条件: `python eval.py --metric acc --threshold 0.82`
- GPU budget: 4h
```

每个 run 必须包含：脚本命令、可执行验收条件（shell command）、资源预算。没有 success criteria 的 run 不接受。

### 4.3 执行状态机

```
┌──────────────────────────────────────────────────────────────────┐
│  ExperimentPlan + EnvHandle                                       │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────── Round Loop ──────────────────────┐ │
│  │                                                             │ │
│  │  1. Planner.next_run()                                      │ │
│  │     └─ 从 tracker 选下一个待执行 run                        │ │
│  │                                                             │ │
│  │  2. AgentBackend(executor).run(run_config)                  │ │
│  │     ├─ sanity run 优先（首次执行 claim 时）                  │ │
│  │     ├─ 并行 run（max_parallel=4，通过 sanity 后）           │ │
│  │     └─ 输出：AgentRunResult                                 │ │
│  │                                                             │ │
│  │  3. ResultVerifier.verify(run_result)                       │ │
│  │     ├─ 执行 acceptance_check shell 命令（硬门控）            │ │
│  │     └─ 从 artifacts_dir parse 实际 metric（防 LLM 幻觉）    │ │
│  │                                                             │ │
│  │  4. Manager.decide(run_result, check_results)               │ │
│  │     ├─ AgentBackend(manager) 独立实例，新鲜上下文            │ │
│  │     └─ 输出：Decision(done|continue|blocked, reason)        │ │
│  │                                                             │ │
│  │  5. Tracker.update(round_result)                           │ │
│  │     ├─ 写 EXPERIMENT_TRACKER.md（人类可读）                 │ │
│  │     └─ 写 round_state.json（程序读取，断点恢复用）           │ │
│  │                                                             │ │
│  │  6. EventEmitter.emit(round_event) ───────────────────────▶ Monitor
│  │                                                             │ │
│  │  停止条件（任意一个）：                                      │ │
│  │    · manager = done AND all checks pass                    │ │
│  │    · manager = blocked                                     │ │
│  │    · 连续 N 轮无进展（stall detection）                     │ │
│  │    · 超出总 GPU budget                                      │ │
│  │    · 达到 max_rounds                                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│       │                                                          │
│       ▼                                                          │
│  ExperimentResult（results_dir + tracker.md + final_summary）   │
└──────────────────────────────────────────────────────────────────┘
```

### 4.4 三个内部角色

| 角色 | 职责 | 推荐后端/模型 | 上下文策略 |
|------|------|-------------|-----------|
| **Executor** | 编写/修改代码，执行 shell 命令 | ClaudeCodeBackend / CodexBackend | 完整历史，支持 session 恢复 |
| **Manager** | 判断 done/continue/blocked，控制循环 | DirectAPIBackend，轻量高推理 | 仅当轮摘要 + checks，新鲜上下文 |
| **Planner** | 从 tracker 状态决定下一个 run | DirectAPIBackend，轻量 | tracker.md |

Manager 每轮新鲜上下文，避免 Executor 的确认偏误影响停止判断。

### 4.5 Operator Inject 接口

执行循环在每轮结束后检查 `operator_messages.md`，支持在轮间注入修正指令：

```bash
echo "[2026-03-21 14:30] 把 learning_rate 改成 1e-4，重跑 Run 1.1" >> operator_messages.md
```

支持 session 恢复的后端（Codex、OpenClaw）可通过 `AgentBackend.inject()` 热注入，无需等到下一轮。

### 4.6 持久化文件结构

```
{experiment_id}/
├── EXPERIMENT_PLAN.md       # 输入
├── EXPERIMENT_TRACKER.md    # 实时状态（人类可读）
├── operator_messages.md     # 注入指令日志
├── rounds/
│   ├── round_001.json
│   └── ...
├── artifacts/
│   ├── run_1_0/             # sanity run 输出
│   └── run_1_1/             # full run 输出
└── final_summary.md         # Manager 最终决策报告
```

---

## 7. 模块三：Monitor（检测层）

> 状态：接口草图，详细设计待展开

### 7.1 职责

消费执行层的事件流，提供：
1. **实时可视化**：metrics、loss curve、GPU 利用率
2. **结构化报告**：实验结束后的 HTML/PDF 报告

设计参考：SwanLab 的 run 对比、metric 追踪、实验报告生成。

### 7.2 事件流格式

```python
@dataclass
class ExperimentEvent:
    experiment_id: str
    round: int
    event_type: Literal[
        "run.started", "run.metrics", "run.completed",
        "manager.decision", "plan.updated", "experiment.finished"
    ]
    timestamp: str
    payload: dict
```

### 7.3 双层监控

| 层次 | 内容 | 对标 |
|------|------|------|
| **实验指标层** | loss / acc / metric curve，run 对比，GPU 利用率 | SwanLab run 视图 |
| **Agent 行为层** | Manager 历轮决策、stall 检测、blocked 原因分析 | 自研 |

两层数据分开存储，不互相污染。

### 7.4 报告结构

```
实验报告
├── 摘要：目标 / 结论 / 最优 run
├── 实验配置：环境信息 / 超参数表
├── 结果：metric 对比图 / 最优 checkpoint 路径
├── 执行日志：Manager 决策时间线 / 关键事件
└── 附录：完整 tracker.md
```

---

## 8. 模块间接口总览

```
EnvSpec ──────────────▶ Environment ──────────────▶ EnvHandle
                                                        │
ExperimentPlan ──────▶ Execution ◀──────────────────────┘
        ▲                  │
        │                  ├──── ExperimentEvent stream ──▶ Monitor
   AgentBackend            │
   (可替换)                └──── ExperimentResult
```

**原则**：
- Environment → Execution：仅传 `EnvHandle`，执行层不感知容器细节
- Execution → Monitor：单向事件流，检测层不反向控制执行层
- AgentBackend：执行层通过统一接口调用，不直接依赖任何平台 SDK
- 文件系统作为共享状态的最终一致来源

---

## 9. 关键设计决策

### 9.1 为什么要 AgentBackend 抽象层？
不同平台（Claude Code / Codex / OpenClaw）的调用方式、会话模型、工具能力差异较大。抽象层让执行层逻辑与平台解耦，切换后端只需更换配置，不改核心代码。所有 agent 角色（Executor、Manager、Planner）均走统一接口，无特例。

### 9.2 为什么 Manager 和 Executor 是独立角色，且走独立后端配置？
Executor 有完整历史上下文，容易产生确认偏误。Manager 每轮新鲜上下文，只看当轮 check 结果，判断更客观。Manager 不需要文件操作能力，用 direct-api 轻量后端即可，成本低且响应快。

### 7.3 为什么 Claim-driven？
每个 run 必须对应一个 claim，Manager 的 done 判断基于 claim 是否被证明，而非代码是否跑完，避免"跑完但不知道验证了什么"。

### 7.4 为什么双格式状态（markdown + JSON）？
- `EXPERIMENT_TRACKER.md`：LLM 读取高效，人工 debug 直观
- `round_state.json`：程序 parse 可靠，支持断点恢复

### 7.5 为什么 Sanity-first？
GPU 资源昂贵，环境配置问题在 sanity run（1 epoch / 最小数据）暴露，通过后才并行放量。

### 7.6 Shell 验收条件 vs 纯 LLM 判断？
LLM 可以捏造结果，shell 命令不会。`exit 0` + metric threshold 作为硬门控，Manager LLM 作为语义判断，双重保障。

---

## 10. 开发优先级

```
Phase 1（执行层骨架，不含 LLM）
├── ExperimentPlan 格式定义
├── Round-based 状态机
├── Shell 验收 check 执行器
├── EXPERIMENT_TRACKER 读写
└── AgentBackend 接口定义（含 Mock 实现）

Phase 2（环境层）
├── 基础镜像清单
├── EnvHandle 接口实现
└── 有网分发流程

Phase 3（执行层 agent 接入）
├── ClaudeCodeBackend 实现
├── CodexBackend 实现
├── Manager / Planner 接入
└── Operator inject 机制

Phase 4（检测层）
├── 事件流定义 + 消费
├── 实时指标可视化
└── 实验报告生成
```

---

## 11. 待定问题（需要拍板）

1. **离线镜像分发**：SSH + `docker save/load` 还是搭私有 registry？
2. **检测层 UI**：基于 SwanLab 二次开发 还是 自研 + 对接 SwanLab SDK？
3. **多实验并发**：Phase 1 单实验串行，并发调度放 Phase 几？
4. **后端优先级**：Phase 3 先实现哪个后端？（建议 ClaudeCodeBackend 先行）

---

*文档持续更新，以实际实现为准。*
