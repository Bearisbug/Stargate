# Manager 自动重试

## 触发条件

full run（或 sanity run）失败，且该 Claim 的 `retry_count < max_retries`（默认 3）。

## Manager 可以自主调整的范围

| 可以调整 | 不可以调整 |
|---------|-----------|
| 命令行超参（--lr, --batch-size, --epochs, --warmup 等） | 成功条件 |
| 增减 flags（--mixed-precision, --grad-clip 等） | 实验方法/算法本身 |
| 数据路径/split（如有多个可选） | GPU budget 上限 |
| sanity run 的规模（--epochs 1 → --steps 10） | 跨 Claim 的依赖关系 |

超出上述范围时，直接 escalate，不强行生成新 run。

## 生成新 run 的步骤

1. 读取失败 run 的 `rounds/<run_id>.json`，分析 `errors` 和 artifacts
2. 推断调整方向（见下方策略）
3. 在 EXPERIMENT_TRACKER.md 中追加新 run：

```markdown
### Run 1.2 — full [auto-retry #1]
- 命令: python train.py --epochs 50 --lr 5e-4  ← 调整点
- 成功条件: val acc 超过 baseline 0.80，提升不低于 2%  ← 与原 run 相同
- GPU budget: 4h
- 状态: pending
- 重试原因: Run 1.1 val acc=0.73，低于阈值；尝试降低 lr
```

4. 更新 Claim 的 `retry_count`（写入 tracker 汇总表）

## 调整策略

| 失败模式 | 优先尝试 |
|---------|---------|
| 指标接近但未达标（差距 < 5%） | 调整 lr（×0.5 或 ×2）、增加 epochs |
| 指标远未达标（差距 > 10%） | 检查命令是否有明显参数问题；若无，escalate |
| loss 不收敛 / nan | 降低 lr（×0.1）、减小 batch-size |
| sanity 报错 | 修复错误（缺参数、路径问题）；若是逻辑错误，escalate |
| 速度/显存问题 | 减小 batch-size（由 experiment-errors 处理，不计入 retry） |

## retry_count 计数规则

- 每个 Claim 独立计数
- 每次 Manager 主动生成新 run 时 +1
- experiment-errors 触发的自动修复（OOM、依赖等）**不计入** retry_count
- retry_count 写入 tracker 汇总表，格式：`重试: 1/3`

## escalate 消息格式

停止时输出：

```
[ESCALATE] Claim <N>: <Claim 描述>

已重试 <N> 次，均未通过成功条件：
- Run X.1: <结果摘要>
- Run X.2 (auto-retry #1, 调整: lr 5e-4): <结果摘要>
- Run X.3 (auto-retry #2, 调整: epochs 80): <结果摘要>

Manager 分析: <失败原因推断>

需要人工决策:
- [ ] 调整实验设计
- [ ] 放宽成功条件
- [ ] 提供更多计算资源
- [ ] 终止该 Claim
```
