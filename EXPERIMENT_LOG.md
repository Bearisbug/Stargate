# Experiment Log

## 2026-03-25 — Session Start

**输入来源**：自然语言 idea
**原始输入**：在 SST-2 数据集上用 Qwen3-4B 跑一个基线情感分类实验，记录 accuracy 和 loss

**提取的 Claims**：
- Claim 1：Qwen3-4B 在 SST-2 上做情感分类微调，目标指标：eval_accuracy + eval_loss
  - 成功标准：pipeline 完整跑通，得到具体数值，无报错退出

**决策**：
- 任务类型：监督微调 SFT（SST-2 二分类，transformers + PEFT/LoRA 或全参微调）
- 平台：Slurm 集群（sc100123@174.0.250.88），conda 运行环境
- 下一步：ENVIRONMENT 阶段，连接服务器，探测 GPU/conda 情况
