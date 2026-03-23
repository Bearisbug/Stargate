# rounds/<run_id>.json 格式规范

> 参考：[JSON Schema Specification (Draft 2020-12)](https://json-schema.org/specification) | [Semantic Versioning 2.0.0](https://semver.org/)

每轮实验完成后，ANALYZING 阶段写入一个 `rounds/<run_id>.json`。**只写入，不覆盖，不修改已有文件。**

---

## 命名规则

```
rounds/<run_id>.json
```

`run_id` 格式：`<claim_id>-<attempt>`，例如：
- `claim1-1`：Claim 1 的第一次运行
- `claim1-2`：Claim 1 的第二次运行（失败重试）
- `claim2-1`：Claim 2 的第一次运行

---

## 完整格式

```json
{
  "run_id": "claim1-1",
  "claim_id": 1,
  "attempt": 1,

  "status": "ANSWERED",

  "git_hash": "abc1234",
  "submitted_at": "2024-01-15T11:15:00Z",
  "completed_at": "2024-01-16T09:00:00Z",

  "job": {
    "job_id": "1255577",
    "exec_type": "slurm",
    "output_dir": "/workspace/ebm_rubric/runs/claim1-1"
  },

  "metrics": {
    "val_auroc": 0.81,
    "best_epoch": 12,
    "train_loss": 0.234
  },

  "criteria": "val_auroc >= 0.72",
  "verdict": "PASS",

  "notes": "Hard negatives 提升了 val AUROC 约 3 个点"
}
```

---

## 字段说明

| 字段 | 必填 | 类型 | 说明 |
|------|:----:|------|------|
| `run_id` | ✅ | string | `<claim_id>-<attempt>`，与文件名一致 |
| `claim_id` | ✅ | int | 对应 TRACKER 中的 Claim id |
| `attempt` | ✅ | int | 本 Claim 的第几次运行，从 1 起 |
| `status` | ✅ | string | `ANSWERED` 或 `FAILED` |
| `git_hash` | ✅ | string | 提交 job 时的 git commit hash（7位缩写即可）|
| `submitted_at` | ✅ | string | ISO 8601 时间戳，job 提交时间 |
| `completed_at` | ✅ | string | ISO 8601 时间戳，job 完成时间 |
| `job.job_id` | ✅ | string | 调度系统分配的 job id（Slurm job id 等）|
| `job.exec_type` | ✅ | string | 执行方式：`slurm` / `docker` / `tmux` |
| `job.output_dir` | ✅ | string | 远端输出目录绝对路径 |
| `metrics` | ✅ | object | 从 `metrics.json` 读取的关键指标 |
| `criteria` | ✅ | string | 原文照抄 TRACKER 中该 Claim 的成功标准 |
| `verdict` | ✅ | string | `PASS`（满足标准）或 `FAIL`（未满足）|
| `notes` | — | string | 值得记录的观察，但不记录 EXPERIMENT_LOG 已有的内容 |

---

## 写入规则

```
ANALYZING 阶段完成后立即写入
│
├── 从远端 output_dir/metrics.json 读取 metrics
├── 对照 criteria 判断 verdict
├── 写入 rounds/<run_id>.json（新文件，不覆盖）
└── 更新 TRACKER claim status 和 result 字段
```

- `run_id` 和文件名必须一致
- `metrics` 字段直接映射 `output_dir/metrics.json` 的内容，不做裁剪
- `git_hash` 必须是提交 job 时工作区的实际 hash，从 TRACKER 中读取

---

## REPORTING 阶段消费格式

REPORTING 阶段读取所有 `rounds/*.json` 生成报告：

```python
import glob, json

rounds = []
for path in glob.glob("rounds/claim*.json"):
    with open(path) as f:
        rounds.append(json.load(f))

# 按 claim_id, attempt 排序
rounds.sort(key=lambda r: (r["claim_id"], r["attempt"]))
```

---

## 示例目录结构

```
rounds/
  claim1-1.json       # Claim 1 第一次运行，ANSWERED
  claim2-1.json       # Claim 2 第一次运行，FAILED（未达阈值）
  claim2-2.json       # Claim 2 第二次运行，ANSWERED（调参后通过）
  insights/
    claim_1.md        # REPORTING 阶段生成的 insight
    claim_2.md
```
