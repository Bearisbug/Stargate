# 预训练（Pretraining）工具规范

## 默认工具

**规模决定框架**：

| 规模 | 默认工具 |
|------|---------|
| 单机多卡（≤8 GPU） | DeepSpeed + HF Trainer |
| 多机多卡（中等规模） | DeepSpeed ZeRO-3 |
| 大规模集群（千卡级） | Megatron-LM |

## 替代条件

| 替代工具 | 何时使用 | 必须说明原因 |
|---------|---------|------------|
| NeMo | NVIDIA 集群，需要原生 Megatron 集成 | ✅ |
| nanotron | 快速验证新架构，追求极简代码 | ✅ |
| torchtune | PyTorch 原生，依赖极少 | ✅ |

## 禁止用法

- **不能用 HF Trainer 做真正的预训练**：不支持 Tensor Parallelism，大模型会 OOM 或效率极低
- **不能跳过梯度裁剪（gradient clipping）**：预训练对 loss spike 敏感，必须设 `max_grad_norm`
- **不能在未做 tokenizer 验证的情况下开始长跑**：先跑 100 步确认 loss 正常下降再提交长任务
