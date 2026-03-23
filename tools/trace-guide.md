# Stargate Tracing Guide

## 层级设计

```
Task ID  ──  整个实验任务（持久，写在 trace-state.json，永远不变）
  └── Conversation A  ──  Claude Code session（提交 job）
        └── Span: experiment-environment
        └── Span: experiment-infrastructure/1.0（sanity，同对话内完成）
  └── Conversation B  ──  Claude Code session（轮询到结果，6小时后）
        └── Span: experiment-infrastructure/1.1（延迟 span，含完整时长）
        └── Event: manager-judge
  └── Conversation C  ──  Codex session（生成 retry run）
        └── Span: manager-retry/1.1
```

**两种 span 模式：**

| 模式 | 命令 | 适用场景 |
|------|------|---------|
| 普通 span | `span-start` / `span-end` | 同对话内完成的操作（环境初始化、验证等） |
| 延迟 span | `span-defer` / `span-end` | 跨对话的异步操作（Slurm job、长时训练） |

`span-defer` 只在本地记录开始时间，不调用 Langfuse。
`span-end` 检测到 pending_spans 时，用历史时间戳补发完整 span，时长准确。

---

## 环境配置（一次性）

```bash
pip install langfuse

export LANGFUSE_PUBLIC_KEY=pk-lf-xxx
export LANGFUSE_SECRET_KEY=sk-lf-xxx
export LANGFUSE_HOST=http://localhost:3000   # 自部署；云端用 https://cloud.langfuse.com
```

自部署：`docker compose up`（使用 Langfuse 官方 docker-compose.yml）

---

## 标准调用流程

### 1. 实验开始时（只做一次）

```bash
python tools/trace.py init --experiment "sft-qwen2.5-alpaca"
```

### 2. 每次 agent session 开始时

```bash
python tools/trace.py conversation --agent claude-code
# 多模型协作时按实际 agent 填写：--agent codex / --agent claude-code
```

conversation 命令会打印当前 pending_spans，提醒有哪些异步操作等待完成。

### 3. 普通操作（同对话内完成）

```bash
python tools/trace.py span-start --name experiment-environment \
  --input '{"host":"user@server","exec_type":"slurm-singularity"}'

# ... 执行初始化 ...

python tools/trace.py span-end --name experiment-environment \
  --output '{"status":"ready"}' --status ok
```

### 4. 异步操作（Slurm job 等）

```bash
# ── Conversation A：提交 job ─────────────────────────────────────────────────
python tools/trace.py span-defer --name experiment-infrastructure --run-id 1.1 \
  --input '{"command":"python train.py ...","exec_type":"slurm-singularity"}'
# 仅写入 trace-state.json，不调用 Langfuse

# ... sbatch 提交，记录 job_id ...

python tools/trace.py event --name job-submitted \
  --data '{"run_id":"1.1","job_id":"12345","partition":"gpu"}'
# 对话结束

# ── Conversation B：轮询到结果（数小时后，可以是任意 agent）───────────────────
python tools/trace.py conversation --agent claude-code
# 输出：pending_spans=['experiment-infrastructure/1.1']  ← 提醒有未完成的异步操作

# ... 检查 job 状态，收集 artifacts ...

python tools/trace.py span-end --name experiment-infrastructure --run-id 1.1 \
  --output '{"exit_code":0,"status":"passed"}' --status ok
# 输出：span-end (deferred)  duration=21480s  ← 从提交到完成的完整时长
```

### 5. Manager 决策和评分

```bash
python tools/trace.py event --name manager-judge \
  --data '{"run_id":"1.1","decision":"continue","reason":"passed"}'

python tools/trace.py score --name run-result --value 1 --comment "val acc=0.847"
# passed=1 / failed=0 / escalate=-1
```

---

## trace-state.json 结构

```json
{
  "experiment":       "sft-qwen2.5-alpaca",
  "task_id":          "task-sft-qwen2.5-alpaca-a1b2c3d4",
  "current_trace_id": "trace-xxxxxxxx",
  "current_agent":    "claude-code",
  "spans":            {},
  "pending_spans": {
    "experiment-infrastructure/1.1": {
      "name":             "experiment-infrastructure",
      "run_id":           "1.1",
      "start_time":       "2026-03-22T10:00:00+00:00",
      "input":            {"command": "..."},
      "started_in_trace": "trace-aaaaaaaa",
      "started_by_agent": "claude-code"
    }
  },
  "created_at": "2026-03-22T10:00:00+00:00"
}
```

| 字段 | 生命周期 |
|------|---------|
| `task_id` | 永久不变 |
| `current_trace_id` | 每次 `conversation` 命令更新 |
| `spans` | 对话内有效，`conversation` 时清空 |
| `pending_spans` | 跨对话持久，`span-end` 补发后删除 |

---

## 多模型协作下的查询

Langfuse session 视图（按 task_id 过滤）：
- 按时间排列所有 conversation，看完整协作链路
- 按 `agent` 字段过滤，单独看 Claude Code 或 Codex 的行动

---

## 不需要 tracing 时

`trace-state.json` 不存在时，所有 skill 正常执行，不产生任何 Langfuse 调用。
tracing 完全可选。
