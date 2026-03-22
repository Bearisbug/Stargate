# 从实验计划生成 Tracker

## 输入：EXPERIMENT_PLAN.md 字段规范

### Claim 块（必填）

```markdown
## Claim <N>: <一句话描述待验证的假设>
```

| 字段 | 必填 | 说明 |
|------|:----:|------|
| Claim 编号 | ✅ | 整数，从 1 开始 |
| Claim 描述 | ✅ | 自然语言，说明"什么条件下，什么指标达到什么水平" |

### Run 块（每个 Claim 至少一个 full run）

```markdown
### Run <N.M> — <sanity|full>
- 命令: <shell 命令>
- 成功条件: <自然语言>
- 验收命令 (可选): <shell 命令，exit code 为判断依据>
- 输出目录 (可选): <路径>
- 镜像 (可选): <image_tag>
- GPU budget: <Xh>
```

| 字段 | 必填 | 说明 |
|------|:----:|------|
| Run 编号 | ✅ | `<Claim编号>.<序号>`，从 0 开始；0 为 sanity，≥1 为 full |
| 类型标签 | ✅ | `sanity` 或 `full` |
| 命令 | ✅ | 任意 shell 命令 |
| 成功条件 | ✅ | 自然语言描述期望结果 |
| GPU budget | ✅ | `0h` 表示 CPU only |

### 完整示例

```markdown
## Claim 1: 方法 X 在数据集 Y 上比 baseline 高 2%

### Run 1.0 — sanity
- 命令: python train.py --epochs 1 --batch-size 32
- 成功条件: 无报错，loss 合理（不为 nan）
- GPU budget: 0.1h

### Run 1.1 — full
- 命令: python train.py --epochs 50 --batch-size 32
- 成功条件: val acc 超过 baseline 0.80，提升不低于 2%
- 验收命令: python eval.py --threshold 0.82
- 输出目录: /workspace/runs/exp1
- GPU budget: 4h

## Claim 2: 方法 X 在数据集 Z 上同样有效

### Run 2.0 — sanity
- 命令: python train.py --dataset Z --epochs 1
- 成功条件: 无报错
- GPU budget: 0.1h

### Run 2.1 — full
- 命令: python train.py --dataset Z --epochs 50
- 成功条件: val acc 超过 Z 的 baseline 0.75
- GPU budget: 4h
```

## 转换规则

1. 按 Claim 分组，每个 Claim 下的 run **严格顺序**执行（sanity 通过后才执行 full）
2. 不同 Claim 的 run 可并行（如有多 GPU）
3. 生成 EXPERIMENT_TRACKER.md，所有 run 初始状态为 `pending`

## 跳过 PLAN 直接写 TRACKER

不需要验证假设、只想跑一组命令时，可跳过 EXPERIMENT_PLAN.md，直接按
[tracker-format.md](tracker-format.md) 手写 EXPERIMENT_TRACKER.md。
