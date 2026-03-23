# 从已有结果规划下一步实验

## 输入

优先读取（按优先级）：
1. `reports/report.md`（已有实验报告，含 Manager 分析和建议）
2. `rounds/insights/claim_N.md`（per-Claim 分析）
3. `rounds/final_summary.md`（执行层汇总）
4. 用户的补充说明

## 分析框架

读取已有结果后，按以下维度分析：

| 维度 | 问题 |
|------|------|
| 成功的 Claim | 结果是否足够有力？是否需要更大规模验证？ |
| 失败的 Claim | 失败原因是什么？调参能解决，还是方法假设有问题？ |
| Escalate 的 Claim | Manager 的建议是什么？继续、调整、还是放弃？ |
| 空白区域 | 哪些变量还没被探索？（不同数据集、不同规模、不同超参） |

## 生成规则

- **继续验证方向**：在成功 Claim 的基础上增加 scale-up run 或 ablation
- **修复失败方向**：根据 Manager 分析生成针对性 retry 实验
- **放弃方向**：在计划中注明"基于 <日期> 实验结果，放弃该方向，原因：..."
- **新方向**：若已有结果提示了新假设，作为新 Claim 追加

## 输出格式

生成新的 `EXPERIMENT_PLAN.md`，并在文件开头加上：

```markdown
# 实验计划（基于 <日期> 结果的后续实验）

> 前置结果：reports/report.md（<实验名>，结论：done/escalate）
> 本次目标：<一句话说明本轮实验要解决的问题>
```

之后按标准格式列 Claim 和 Run。
