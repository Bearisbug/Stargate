# 监督微调（SFT）工具规范

## 默认工具

**LLaMA-Factory**

配置驱动，支持 LoRA / QLoRA / 全量微调，覆盖主流模型，开箱即用。

```bash
llamafactory-cli train examples/train_lora/llama3_lora_sft.yaml
```

## 替代条件

| 替代工具 | 何时使用 | 必须说明原因 |
|---------|---------|------------|
| Axolotl | 训练逻辑需要深度定制，LLaMA-Factory 配置无法覆盖 | ✅ |
| HF Trainer（直接） | 需要完全自定义训练循环（自定义 loss、特殊数据流） | ✅ |
| torchtune | 追求极简依赖，PyTorch 原生生态 | ✅ |

## 禁止用法

- **不能直接用原始 HF Trainer 做 LoRA**：peft 集成细节容易踩坑（梯度、保存格式），LLaMA-Factory 已封装好
- **不能在未确认 chat template 正确的情况下开始训练**：不同模型的 template 差异会导致静默训练错误
- **不能跳过 val loss 监控**：SFT 容易过拟合，必须设 eval_steps
