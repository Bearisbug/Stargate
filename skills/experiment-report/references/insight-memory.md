# Insight 记录与 Memory

借鉴 ARIS 的"每轮 what happened 注释"和 ArgusBot 的"round-NNN.md 按轮存档"。

## 两级存储

| 级别 | 路径 | 作用 |
|------|------|------|
| 短期（项目内） | `rounds/insights/claim_<N>.md` | 当前实验的每个 Claim 分析，供报告引用 |
| 长期（跨实验） | Claude memory system | 跨实验可复用的规律和经验 |

## 何时记录

每个 Claim 完成时（passed / failed / escalate），Manager 触发 experiment-report skill 写入 `rounds/insights/claim_<N>.md`。

## claim_N.md 格式

```markdown
# Insight: Claim <N>

**状态**: passed | failed | escalate
**时间**: <ISO8601>
**Claim**: <Claim 描述>

## 结果摘要
<关键指标数字，从 rounds/*.json 读取>

## What Happened
<本 Claim 的实验过程叙述：做了什么，遇到什么问题，怎么解决的>

## 关键发现
- <发现 1：具体、可量化>
- <发现 2>

## 对后续实验的建议
- <如果继续做，下一步应该尝试什么>
- <有哪些超参值得探索>

## 失败分析（仅 failed / escalate 时）
**推测原因**: <数据问题 / 超参不合适 / 方法假设不成立 / 其他>
**已尝试**: <列出所有 auto-retry 的调整和结果>
**建议人工介入方向**: <具体>
```

## 长期 Memory 写入规则

Claim 完成后，判断是否有值得跨实验保留的内容：

**写入 memory 的条件（满足任一）：**
- 发现了某个超参范围在该任务类型上普遍有效（如"SFT 的 lr 在 1e-5 ~ 5e-5 之间稳定"）
- 某个错误模式和解决方案有通用性（如"GRPO 初期 reward nan，调低 kl_coef 可解决"）
- 某个数据集 / 模型组合有特殊行为需要注意

**不写入 memory 的内容：**
- 针对当前实验的一次性发现
- 已在代码/配置中修复的 bug
- 数字结果（这些在 report.md 里）

**写入格式**（Claude memory system，类型 `project`）：

```markdown
---
name: insight_<task_type>_<topic>
description: <一行：什么任务类型下，什么经验>
type: project
---

**发现**: <具体经验>

**Why**: 来自实验 <experiment_name>，Claim <N>，<日期>

**How to apply**: 下次做 <task_type> 时，<具体建议>
```

## 累积叙事（NARRATIVE_REPORT.md）

每次实验结束后，向 `NARRATIVE_REPORT.md` 追加一段，记录本次实验在整个研究方向上的位置：

```markdown
## <日期> — <实验名称>

**做了什么**: <一句话>
**结论**: <done / escalate>
**最重要的发现**: <一条>
**对整体研究方向的影响**: <继续 / 调整 / 放弃该方向>
```

这个文件不按 Claim 组织，而是按时间顺序记录整个研究的演进，类似研究日志。
