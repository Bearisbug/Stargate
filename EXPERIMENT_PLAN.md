# Experiment Plan: SST-2 Sentiment Classification Baseline with Qwen3-4B

## Goal
在 SST-2 数据集上用 Qwen3-4B 跑基线情感分类实验，建立 accuracy + loss 基准数值。

## Claims

### Claim 1: SST-2 基线
**假设**：Qwen3-4B 经过 SST-2 微调后，可以在验证集上实现有效的情感分类
**成功标准**：eval_accuracy 和 eval_loss 有明确数值，pipeline 完整跑通
**方法**：使用 HuggingFace transformers + PEFT（LoRA）对 Qwen3-4B 进行 SST-2 序列分类微调
**数据集**：glue/sst2（HuggingFace datasets）
**模型**：Qwen/Qwen3-4B

## 实验设计

- **任务**：二分类（positive / negative）
- **训练集**：SST-2 train（67,349 samples）
- **验证集**：SST-2 validation（872 samples）
- **超参**：
  - batch_size: 16（per device）
  - epochs: 3
  - lr: 2e-4（LoRA），warmup_ratio: 0.1
  - LoRA: r=8, alpha=16, target_modules=["q_proj","v_proj"]
- **输出指标**：eval_accuracy, eval_loss（每 epoch 记录）
