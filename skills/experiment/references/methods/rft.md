# 强化微调（RFT / RLHF）工具规范

> 参考：[VeRL 官方文档](https://verl.readthedocs.io/en/latest/) | [VeRL GitHub](https://github.com/volcengine/verl)

## 默认工具

**VeRL，算法优先选 GRPO**

VeRL（Volcano Engine RL for LLMs）是当前最主流的开源 LLM 强化训练框架，支持 FSDP + vLLM/SGLang 混合并行，actor 训练与 rollout 分离，显存效率和吞吐量均优于单一框架方案。

GRPO 无需独立 critic 模型，显存占用低于 PPO，稳定性更好，是当前 LLM RFT 的首选算法。

```bash
# 以 GRPO 为例
python -m verl.trainer.main_ppo \
    algorithm=grpo \
    data.train_files=data/train.parquet \
    actor_rollout_ref.model.path=/path/to/model \
    trainer.total_epochs=1
```

**算法选择优先级：GRPO → DPO（有偏好数据时）→ PPO（需要复杂 value 估计时）**

## 禁止用法

- **不能用 transformers generate 做 rollout**：必须用 vLLM 或 SGLang，否则训练吞吐不可接受
- **不能跳过 KL divergence 监控**：KL 失控会导致模型崩溃，训练时必须记录
