# 实验执行循环

## 循环结构

```
while tracker 中还有 pending run:
    执行下一个 run（experiment-flow skill）
    Manager 读取所有已完成 run 的结果，判断：
        done    → 停止，输出 final_summary.md
        retry   → 生成新 run 加入 tracker，继续循环
        continue → 继续下一个 pending run
        escalate → 请求 human in loop，停止等待
```

## Claim 完成条件

| Claim 状态 | 条件 |
|-----------|------|
| `passed` | 该 Claim 下至少一个 **full run** 通过成功条件（sanity 不计入） |
| `failed` | 该 Claim 下所有 full run 均失败，且已达 `max_retries` |
| `blocked` | 任意 run 遇到无法自动修复的执行错误 |

sanity run 失败时，跳过同 Claim 的所有 full run，直接进入 retry 流程（sanity 也计入 retry_count）。

## Manager 判断依据

```
done     ← 所有 Claim 均 passed
continue ← 存在 pending run，无需 retry，无 blocked
retry    ← 某 Claim 的 run failed，且 retry_count < max_retries
escalate ← 任意 Claim 的 retry_count >= max_retries
         ← 任意 run blocked（执行层错误）
         ← 超出总 GPU budget
         ← 达到 max_rounds（默认 20）
```

`retry` 时 Manager 分析失败原因，生成新 run 写入 tracker，继续循环。
→ 详见 [references/manager-retry.md](manager-retry.md)

## 停止条件

| 条件 | 结果 |
|------|------|
| 所有 Claim passed | `done` |
| 任意 Claim retry_count >= max_retries | `escalate` |
| 任意 run `blocked`（执行错误） | `escalate` |
| 超出总 GPU budget | `escalate: budget_exceeded` |
| 达到 max_rounds（默认 20） | `escalate: max_rounds` |

## final_summary.md 格式

路径：`rounds/final_summary.md`，在 `done` 或 `escalate` 时输出。

```markdown
# Experiment Summary

**结论**: done | escalate
**完成时间**: <ISO8601>
**总耗时**: <Xh>
**GPU 消耗**: <Xh>

## Claim 结果

| Claim | 状态 | 关键指标 | 通过 Run |
|-------|------|----------|---------|
| Claim 1: 方法 X 比 baseline 高 2% | passed | val acc=0.847 (+4.7%) | Run 1.1 |
| Claim 2: 方法 X 在数据集 Z 有效 | escalate | 3 次重试均未达标 | — |

## 详细结果

### Claim 1 — passed
- Run 1.0 (sanity): passed，耗时 0.08h
- Run 1.1 (full): passed，val acc=0.847，耗时 4.2h

### Claim 2 — escalate（需要人工介入）
- Run 2.0 (sanity): passed
- Run 2.1 (full): failed，val acc=0.71
- Run 2.2 (auto-retry, lr=5e-4): failed，val acc=0.72
- Run 2.3 (auto-retry, epochs=80): failed，val acc=0.73
- **Manager 分析**: 指标持续偏低，可能是数据集 Z 的分布与方法假设不符，建议人工检查数据预处理

## 下一步建议

<Manager 针对 escalate 的 Claim 给出分析和具体建议>
```
