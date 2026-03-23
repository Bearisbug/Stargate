# 从 Idea 生成实验计划

## 提取流程

1. **识别核心假设**：用户的 idea 里什么是可验证的？提炼成"如果 X，则 Y 指标会达到 Z"的形式
2. **确定基线**：这个假设要和什么比较？（之前的方法、vanilla baseline、论文中的结果）
3. **确定评测方式**：用什么数据集/指标衡量成功？阈值是多少？
4. **拆分 run**：一个 Claim 通常有 1 个 sanity + 1-2 个 full run

## 信息缺失时的处理

| 缺失信息 | 处理方式 |
|---------|---------|
| 代码路径 | 标注 `[需要 experiment-code]`，在计划末尾说明 |
| 数据集路径 | 用 `<PLACEHOLDER: 数据集路径>` 占位，提示用户填写 |
| 成功阈值 | 若用户未指定，使用"优于 baseline X%"或"无报错"作为默认 |
| 模型路径 | 用 `<PLACEHOLDER: 模型路径>` 占位 |

## 示例转换

**用户输入：**
> 想试试在 LLaMA-3 上加 LoRA 做代码生成，看看能不能超过全量 finetune 的效果

**提取结果：**
```markdown
## Claim 1: LoRA SFT 在代码生成上达到与全量 finetune 相当的效果

### Run 1.0 — sanity
- 命令: python train.py --model <PLACEHOLDER> --method lora --dataset <PLACEHOLDER> --steps 10
- 成功条件: 无报错，loss 下降
- GPU budget: 0.1h

### Run 1.1 — full (LoRA)
- 命令: python train.py --method lora --epochs 3
- 成功条件: HumanEval pass@1 ≥ baseline_full_ft（见 <PLACEHOLDER: baseline 结果>）
- GPU budget: 4h

### Run 1.2 — full (full finetune，作为 baseline)
- 命令: python train.py --method full --epochs 3
- 成功条件: 完成训练，记录 HumanEval pass@1 作为 baseline
- GPU budget: 8h
```
