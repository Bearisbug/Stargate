---
name: experiment-report
description: 生成实验报告：整理文字报告、记录每轮 insight、上传 SwanLab 可视化。每个 Claim 完成后记录 insight；实验结束后生成完整报告。
---

# 实验报告

## 触发时机

| 时机 | 动作 |
|------|------|
| 每个 Claim 完成（passed / failed / escalate） | 记录 insight → [references/insight-memory.md](references/insight-memory.md) |
| 实验整体结束（done / escalate） | 生成文字报告 + 可视化 Dashboard |

Manager 在 running-loop 中负责调用，不需要用户手动触发。

## 输入

| 来源 | 内容 |
|------|------|
| `rounds/<run_id>.json` | 所有 run 的结果、状态、命令 |
| `EXPERIMENT_TRACKER.md` | Claim 列表和汇总状态 |
| `rounds/insights/claim_<N>.md` | 已记录的 per-Claim insight |
| 训练日志 | stdout/stderr，路径来自 run_id.json 的 `log_path` 字段 |

## 输出

| 文件 | 何时生成 |
|------|---------|
| `rounds/insights/claim_<N>.md` | 每个 Claim 完成时 |
| `reports/report.md` | 实验结束时 |
| SwanLab dashboard | 实验结束时（需 SwanLab 可用） |

## 详细说明

→ 文字报告格式：[references/text-report.md](references/text-report.md)
→ 可视化 Dashboard：[references/visualization.md](references/visualization.md)
→ Insight 记录与 memory：[references/insight-memory.md](references/insight-memory.md)
