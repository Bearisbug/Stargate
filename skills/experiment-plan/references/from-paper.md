# 从论文生成实验计划

## 适用场景
- 复现论文主实验
- 在论文 baseline 基础上做扩展
- 验证论文方法是否泛化到新数据集/任务

## 提取流程

1. **读论文**（或摘要/方法节）：提取核心方法、数据集、主要指标、reported 数字
2. **识别可复现的实验**：哪些实验结果是关键的？哪些可以先跳过？
3. **确定代码来源**：论文是否有官方代码？（GitHub 链接）→ 标注到计划里
4. **生成 Claim**：每个核心 table row 或 ablation 对应一个 Claim

## Claim 设计原则

- **复现实验**：成功条件 = 达到论文报告值的 ±2%（允许合理误差）
- **扩展实验**：成功条件 = 优于论文中对应 baseline
- 如果论文代码不存在，在计划中标注 `[需要 experiment-code: 参考 paper Section X 实现]`

## 示例

**论文**：某 GRPO 方法在 MATH-500 上达到 pass@1=72.4%，baseline（SFT only）为 58.1%

```markdown
## Claim 1: 复现论文 Table 2 主结果 — GRPO 在 MATH-500 上显著优于 SFT baseline

### Run 1.0 — sanity
- 命令: python train.py --method grpo --steps 50
- 成功条件: reward 非 nan，loss 下降，无报错
- GPU budget: 0.2h

### Run 1.1 — full (SFT baseline)
- 命令: python train.py --method sft --epochs 2
- 成功条件: MATH-500 pass@1 接近论文报告 58.1%（±3%）
- GPU budget: 4h

### Run 1.2 — full (GRPO)
- 命令: python train.py --method grpo --steps 2000
- 成功条件: MATH-500 pass@1 ≥ 70%（论文 72.4% ±3%）
- GPU budget: 12h

代码来源: <PLACEHOLDER: 论文 GitHub 链接>
```

## 代码不存在时

在计划末尾追加：
```
[需要 experiment-code]
参考: Paper Section 3.2（方法描述），Section 4（实验设置）
实现要点: <从论文提取的关键超参和架构细节>
```
