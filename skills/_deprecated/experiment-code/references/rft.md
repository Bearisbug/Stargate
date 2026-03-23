# RFT / GRPO / PPO 代码规范

## 推荐框架

| 算法 | 推荐 |
|------|------|
| GRPO | `trl.GRPOTrainer`（trl ≥ 0.9）|
| PPO | `trl.PPOTrainer` |
| 自定义 RL | `verl`（字节跳动开源）|

## 标准命令行接口

```bash
python train.py \
  --model-path  /models/Qwen2.5-7B-SFT \
  --train-data  /data/math/train.jsonl \
  --output-dir  /workspace/runs/grpo-exp1 \
  --steps       2000 \
  --batch-size  16 \
  --lr          1e-6 \
  --kl-coef     0.1 \
  --seed        42
```

## 日志输出格式（供 viz.py 解析）

```
step=100  reward=1.24  kl_div=0.03  policy_loss=-0.12  clip_ratio=0.18
step=200  reward=1.56  kl_div=0.04  policy_loss=-0.09  clip_ratio=0.15
```

关键指标：`reward`（必须）、`kl_div`、`policy_loss`、`clip_ratio`

## 常见问题

| 症状 | 原因 | 处理 |
|------|------|------|
| reward = nan | lr 过大 / reward 函数数值不稳定 | 降低 lr（×0.1），检查 reward 函数 |
| kl_div 持续上升 | kl_coef 过小 | 增大 kl_coef（×2） |
| reward 不收敛 | batch 内 positive reward 过少 | 增大 group size 或降低任务难度 |
| OOM | 同时存多个 model copy | 使用 reference model offload |

## Reward 函数规范

```python
def reward_fn(completions: list[str], references: list[str]) -> list[float]:
    """
    返回 float list，每个元素对应一个 completion 的 reward。
    范围建议 [-1, 1] 或 [0, 1]，避免极端值。
    """
    ...
```

## 镜像

基础镜像：`base-pytorch-cu121`（`<PLACEHOLDER: 镜像仓库地址>/base-pytorch-cu121`）

依赖：`transformers>=4.40`, `trl>=0.9`, `peft>=0.10`, `accelerate>=0.28`
