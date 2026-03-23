# 文字报告生成

输出路径：`reports/report.md`

## 报告结构

```markdown
# Experiment Report
**实验名称**: <从 EXPERIMENT_TRACKER.md 第一行提取，或用对话中的任务描述>
**完成时间**: <ISO8601>
**结论**: done ✅ | escalate ⚠️
**总 GPU 消耗**: <Xh>

---

## 摘要

<2-4 句话：做了什么，整体结果如何，最关键的发现>

---

## Claim 结果

| Claim | 结论 | 关键指标 | 重试次数 |
|-------|------|----------|---------|
| Claim 1: ... | ✅ passed | val acc=0.847 (+4.7%) | 0 |
| Claim 2: ... | ❌ escalate | pass@1=0.54，未达 0.58 | 3 |

---

## 详细结果

### Claim 1 — ✅ passed

**假设**: <Claim 描述>
**结论**: <一句话总结>

| Run | 类型 | 状态 | 关键指标 | 耗时 |
|-----|------|------|---------|------|
| 1.0 | sanity | passed | 无报错 | 0.08h |
| 1.1 | full | passed | val acc=0.847 | 4.2h |

**Insight**: <Manager 对该 Claim 的分析，为什么成功，有什么值得注意的>

### Claim 2 — ❌ escalate

**假设**: <Claim 描述>
**结论**: <失败分析>

| Run | 类型 | 状态 | 关键指标 | 耗时 |
|-----|------|------|---------|------|
| 2.0 | sanity | passed | 无报错 | 0.09h |
| 2.1 | full | failed | pass@1=0.54 | 3.8h |
| 2.2 | auto-retry #1 | failed | pass@1=0.55 | 3.9h |
| 2.3 | auto-retry #2 | failed | pass@1=0.54 | 4.0h |

**Insight**: <失败分析，建议人工介入方向>

---

## 累积 Insight

<从 rounds/insights/ 汇总所有 Claim 的 insight，提炼跨 Claim 的规律和建议>

---

## 下一步建议

- <针对 escalate 的 Claim 的具体建议>
- <跨 Claim 的系统性发现>
```

## 生成原则

- **数据优先**：所有指标从 `rounds/*.json` 和训练日志中读取，不推断数字
- **有什么写什么**：日志里没有的指标不填占位符，留空或注明"日志未包含"
- **Insight 来自 claim_N.md**：不在报告生成阶段重新分析，直接引用已记录的 insight
