---
name: experiment
description: 实验执行层唯一入口。覆盖从目标理解到最终报告的完整生命周期，通过状态机驱动，支持跨 session 恢复、异步等待、多轮迭代。替代原 experiment-plan / experiment-environment / experiment-flow / experiment-errors / experiment-code / experiment-report 等全部子 skill。
---

# 实验执行

## 入口：读取当前状态

**每次进入此 skill，第一步必须读 `EXPERIMENT_TRACKER.md`。**

| 状态 | 动作 |
|------|------|
| 文件不存在 | 检查 `project.json` 是否存在；不存在则停止，提示用户先运行 `init` skill；存在则进入 [PLAN](#plan) |
| `phase: PLAN` | → [PLAN](#plan) |
| `phase: ENVIRONMENT` | → [ENVIRONMENT](#environment) |
| `phase: DESIGN` | → [DESIGN](#design) |
| `phase: EXECUTING` | → [EXECUTING](#executing) |
| `phase: WAITING` | → [WAITING](#waiting) |
| `phase: ANALYZING` | → [ANALYZING](#analyzing) |
| `phase: REPORTING` | → [REPORTING](#reporting) |
| `phase: DONE` | 告知用户实验已完成，展示 `reports/report.md` 路径 |

---

## PLAN

**目标**：从用户输入中提取清晰的 Claims 和成功标准，创建 TRACKER。

### Step 1：识别输入类型

用户输入可能是以下类型之一：

- **自然语言 idea** → 直接提取目标和假设
- **论文链接 / arxiv URL** → 获取论文内容，理解方法，提炼可验证的实验 Claims
- **已有实验结果，想继续** → 读取现有 `rounds/`，在此基础上提出下一步 Claims
- **已有 `EXPERIMENT_PLAN.md`** → 直接读取，提取 Claims，跳过分析
- **组合输入**（如论文 + 已有结果）→ 分别处理后合并 Claims，注意依赖关系
- **模糊描述**（目标不清晰、缺少成功标准）→ 最小化追问，见下方

### Step 2：目标不清晰时的追问原则

只追问以下三件事，不多问：

1. **最终想证明什么**（Claim 是什么）
2. **怎么算成功**（指标 + 阈值，或定性标准）
3. **有多少计算资源**（影响实验规模设计）

若追问后仍无法提取可验证的 Claim → 停止，告知用户需要更明确的目标描述。

其余设计决策（模型选择、超参、数据处理方式）由 agent 自主决定，在 DESIGN 阶段执行。

### Step 3：提取 Claims

每个 Claim 包含：

- 一句话描述（要验证的假设）
- 成功标准（可判断 ANSWERED / FAILED 的条件）
- 依赖关系（哪些 Claim 需要先完成）

### Step 4：创建 Artifacts

- 创建 `EXPERIMENT_TRACKER.md`，所有 Claim 状态为 `PENDING`
- 创建 `EXPERIMENT_LOG.md`，写入实验开始记录（输入来源、提取的 Claims）
- 若用户输入是论文或 idea，同步生成 `EXPERIMENT_PLAN.md` 作为参考文档

展示提取的 Claims 给用户——**用户有任何回复即视为确认，立即进入下一阶段，不等待显式"开始"指令**。用户若要修改，会在回复中明确说明。

**更新 TRACKER：`phase → ENVIRONMENT`。**

---

## ENVIRONMENT

**若 `env_handle.json` 已存在且 `status: ready`**，跳过此阶段，直接进入 DESIGN。

### Step 1：确认平台类型

先判断或询问远端环境属于哪类平台：

- **AutoDL** → ref: `references/servers/autodl.md`
- **云厂商 GPU 主机**（阿里云 ECS、腾讯云 CVM、AWS EC2 等）→ ref: `references/servers/cloud_gpu.md`
- **学校 / 实验室服务器**（SSH 直连，无调度系统）→ ref: `references/servers/lab_server.md`
- **公司内网服务器** → ref: `references/servers/intranet.md`
- **堡垒机 / 跳板机环境** → ref: `references/servers/bastion_host.md`
- **Slurm 集群** → ref: `references/servers/slurm.md`
- **Kubernetes / 容器平台** → ref: `references/servers/kubernetes.md`
- **本地机器** → 跳过 Step 2，直接进入 Step 3
- **其他 / 未知** → 最小化追问：能否 SSH 直连？有无调度系统？

> 用户已明确说明平台时，直接进入 Step 2，不重复询问。

查阅对应 `references/servers/<platform>.md`，按其要求向用户索取必要的连接信息，不多问。

### Step 2：建立持久化连接

本地和远端各建一层 tmux 会话，防止连接中断导致任务丢失。重连后优先恢复已有会话，不重复启动。

→ ref: `references/servers/connection.md`

### Step 3：确认执行环境

- **Docker 容器** → ref: `references/envs/docker.md`
- **Conda 环境**（集群限制 Docker，如 Slurm）→ ref: `references/envs/conda.md`
- **Singularity / Apptainer**（HPC 常见）→ ref: `references/envs/singularity.md`
- **已有现成环境** → 跳过安装，直接进入 Step 4 验证

### Step 4：GPU 可用性决策

**必须启用 GPU**：任务为训练 / 推理 / 评测等深度学习任务，或代码依赖 GPU 加速。

**可不启用 GPU**：仅做代码修改、配置整理、数据准备，或用户要求先做 CPU 最小验证。

GPU 不可用时：明确指出是哪一层不可用（宿主无 GPU / 驱动异常 / 权限不足 / 环境不兼容），不伪装可运行。

各执行环境下的 GPU 启用与验证方式 → ref: `references/envs/gpu.md`

### Step 5：验证依赖

- 框架与核心依赖可正常加载（含 GPU 库）
- 数据路径、模型路径可访问
- 外部服务可达性（数据源、模型仓库等）
  - 不可达 → 在 `env_handle.json` 中标记离线标志，DESIGN 阶段据此切换离线路径

**写入 `env_handle.json`，更新 TRACKER：`phase → DESIGN`。**

→ env_handle.json 格式 ref: `references/artifacts/env-handle.md`

---

## DESIGN

**步骤**：

1. 读 TRACKER，找到当前第一个 `PENDING` Claim
2. 读 `env_handle.json`，若有离线标志则在后续设计中使用本地路径替代外部服务
3. 读现有代码，理解已有基础
4. 设计本轮实验方案（模型 / 超参 / 数据处理 / 评测方式）
5. 写或更新代码

代码编写规范 → ref: `references/code.md`

**代码写完后，提交一次 commit**，message 简述本轮针对哪个 Claim 做了什么改动。每个 Claim 迭代对应一次 commit，git log 即为完整的代码演进历史。

**异常处理**：

发现设计假设不成立时（数据 schema 不符、模型不可用、依赖缺失等），判断影响范围：

- **仅影响实现方式，不影响 Claim 本身** → 自主调整，记录到 `EXPERIMENT_LOG.md`，继续
- **影响 Claim 的成功标准或可行性** → 停下来告知用户，不得静默修改 Claim

**更新 TRACKER：`phase → EXECUTING`。**

---

## EXECUTING

### 提交方式决策

根据执行环境选择提交方式：

- **Slurm** → ref: `references/servers/slurm.md`
- **Docker** → ref: `references/envs/docker.md`
- **tmux 直接运行** → ref: `references/servers/connection.md`
- **Kubernetes** → ref: `references/servers/kubernetes.md`

提交前检查：

- 输出目录是否存在
- 数据路径、模型路径是否正确
- 是否有同名 job / 容器已在运行（避免重复提交）

**提交前，检查工作区是否干净（无未提交的改动）。若有未提交改动，停止提交，要求先完成 commit 再继续。**

提交失败（job 未进入队列 / 容器未启动）→ 诊断提交层错误，修复后重试，不进入 WAITING。

**提交成功后，记录当前 git commit hash，更新 TRACKER：**

```
phase: WAITING
job_id: <id>
git_hash: <commit hash>
submitted_at: <timestamp>
retry_count: 0
expected_outputs:
  - <path>
```

记录到 `EXPERIMENT_LOG.md`，明确告知用户 job 已提交，可断开 session，有结果再回来。

---

## WAITING

读取 TRACKER 中的 job_id，检查 job 状态：

| 状态 | 处理 |
|------|------|
| 运行中 | 读最新日志，汇报进度，保持 WAITING |
| 完成 | 更新 TRACKER：`phase → ANALYZING` |
| 失败 | 进入错误处理 |
| 消失（队列中找不到且无输出）| 视为异常失败，进入错误处理 |

### 错误处理决策

- **环境错误**（缺库、运行时依赖不兼容）→ 修复执行环境或 job script，重新提交
- **代码错误**（程序异常退出）→ 修复代码，重新提交
- **资源错误**（内存不足、超时）→ 调整资源配置，重新提交
- **数据错误**（文件不存在、格式不对）→ 修复数据路径或格式，重新提交
- **原因不明 / 影响 goal** → 记录到 `EXPERIMENT_LOG.md`，停下来告知用户

**重试规则**：每次重新提交，TRACKER 中 `retry_count` +1。`retry_count` 达到 3 次后，无论错误类型，停下来告知用户，不再自动重试。

重新提交前：修复代码或配置后必须先 commit，再检查工作区干净，方可提交。

重新提交后：更新 TRACKER `job_id` 和 `git_hash`，`phase` 保持 `WAITING`，记录修复内容到 `EXPERIMENT_LOG.md`。

---

## ANALYZING

→ ref: `references/phases/analyzing.md`

**迭代决策**：

| 情况 | 处理 |
|------|------|
| 有 PENDING Claim | 重置 TRACKER `retry_count: 0`，`phase → DESIGN`，继续下一轮 |
| 全部 ANSWERED | 更新 TRACKER：`phase → REPORTING` |
| 结果揭示 Claim 设计有问题 | 停下来告知用户，讨论是否修改 Claim |
| 结果远好于预期，无需继续 | 告知用户，确认是否跳过剩余 Claim 直接 REPORTING |

---

## REPORTING

→ ref: `references/phases/reporting.md`

---

## Artifact 规范

| 文件 | 职责 | 写入规则 |
|------|------|---------|
| `EXPERIMENT_TRACKER.md` | 当前状态，agent 恢复执行依据 | 每个阶段结束时更新，不保留历史 |
| `EXPERIMENT_LOG.md` | 决策叙事，跨 session | append-only，不得修改已有记录 |
| `rounds/<run_id>.json` | 每轮数字结果，含 git_hash | 只写入，不得覆盖或修改已有文件 |
| `env_handle.json` | 环境能力描述 | ENVIRONMENT 阶段写入；环境变化时重新运行 ENVIRONMENT |
| `session-trace.json` | per-session 调试工具 | 自动，不跨 session |

### EXPERIMENT_TRACKER.md 格式

```
phase: <当前阶段>
updated_at: <timestamp>
retry_count: <数字>

job_id: <id>               # 仅 WAITING 阶段有效
submitted_at: <timestamp>  # 仅 WAITING 阶段有效
expected_outputs:          # 仅 WAITING 阶段有效
  - <path>

claims:
  - id: 1
    desc: <描述>
    status: PENDING | ANSWERED | FAILED
    criteria: <成功标准>
    result: <结果摘要>  # ANSWERED / FAILED 后填写

next: <下次进入时 agent 应该做什么的一句话说明>
```

### EXPERIMENT_LOG.md 格式

→ ref: `references/artifacts/experiment-log.md`
