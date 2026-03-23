# 推理（Inference）工具规范

## 默认工具

**vLLM**

适用于所有需要批量推理的场景（数据生成、打分、评估）。

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/model \
  --dtype bfloat16 \
  --max-model-len 4096
```

## 替代条件

| 替代工具 | 何时使用 | 必须说明原因 |
|---------|---------|------------|
| SGLang | 需要 prefix caching（多轮对话、shared system prompt 占比高） | ✅ |
| transformers | 模型架构 vLLM 不支持（查 vLLM 支持列表后确认） | ✅ |
| llama.cpp | 本地 CPU 推理，无 GPU 环境 | ✅ |

## 禁止用法

- **不能用 transformers 做 batch inference**：吞吐量比 vLLM 低 5-10x，显存利用率差
- **不能在 vLLM 支持该模型时选 transformers**，理由"transformers 更熟悉"不成立
- **不能用 for 循环逐条推理**：必须批量，单条推理只用于调试
