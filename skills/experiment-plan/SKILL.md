---
name: experiment-plan
description: 将 idea、论文或已有实验结果转化为可执行的 EXPERIMENT_PLAN.md。在有新研究方向、想复现论文、或基于已有结果规划下一步实验时使用。
---

# 实验规划

## 三种输入模式

| 输入 | 典型场景 | 参考 |
|------|---------|------|
| 自然语言 idea | "想验证 X 方法在 Y 任务上是否有效" | [references/from-idea.md](references/from-idea.md) |
| 论文 / 论文链接 | 复现已有工作，或扩展 baseline | [references/from-paper.md](references/from-paper.md) |
| 已有实验结果 | 基于 `reports/report.md` 或 `rounds/` 规划后续实验 | [references/from-results.md](references/from-results.md) |

输入不明确时优先检查当前目录是否有 `reports/report.md`（已有结果）或用户是否提到论文，再决定模式。

## 输出

生成 `EXPERIMENT_PLAN.md`，格式见 [experiment-flow/references/preparing-experiment.md](../experiment-flow/references/preparing-experiment.md)。

生成后展示给用户确认；有任何回复即视为确认，直接移交 `experiment-flow` 执行。

## 规划原则

- 每个 Claim 必须是**可证伪的假设**，有明确的成功指标
- 每个 Claim 必须有 sanity run（快速验证代码/环境是否正常）
- GPU budget 按任务规模估算并标注，供用户审查
- 若代码尚不存在，标注 `[需要 experiment-code]`，执行前先生成代码框架
