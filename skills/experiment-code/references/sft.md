# SFT 代码规范

## 推荐框架

| 场景 | 推荐 |
|------|------|
| HuggingFace 模型 | `transformers` + `trl.SFTTrainer` |
| 大模型 + 显存受限 | `trl` + `peft`（LoRA/QLoRA） |
| 自定义训练循环 | PyTorch + `accelerate` |

## 标准命令行接口

```bash
python train.py \
  --model-path /models/Qwen2.5-7B \
  --train-data /data/train.jsonl \
  --val-data   /data/val.jsonl \
  --output-dir /workspace/runs/exp1 \
  --epochs 3 \
  --batch-size 8 \
  --lr 2e-5 \
  --seed 42
```

## 日志输出格式（供 viz.py 解析）

每个 step 输出一行，含以下字段（key=value 格式）：

```
step=100 loss=0.342 lr=2e-05 epoch=1
step=200 loss=0.298 lr=1.9e-05 epoch=1
step=500 val_loss=0.401 val_acc=0.87  ← 验证集指标单独一行
```

## LoRA 配置参考

```python
from peft import LoraConfig
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
```

## 镜像

基础镜像：`base-pytorch-cu121`（`<PLACEHOLDER: 镜像仓库地址>/base-pytorch-cu121`）

依赖：`transformers>=4.40`, `trl>=0.8`, `peft>=0.10`, `accelerate>=0.28`
