# EXPERIMENT_TRACKER.md 格式

## Run 配置块

```markdown
## Run 1.1
- 命令: torchrun --nproc_per_node=4 train.py --lr 1e-3 --epochs 50
- 成功条件: val acc 超过 baseline 0.80，且提升不低于 2%
- 验收命令 (可选): python eval.py --threshold 0.82
- 输出目录 (可选): /workspace/runs/exp1
- 镜像 (可选): base-pytorch-cu121
- GPU budget: 4h
- 状态: pending
```

## 状态汇总表（执行后追加/更新）

```markdown
| Run | 状态 | 结果 | 耗时 | 日期 |
|-----|------|------|------|------|
| Run 1.0 | passed | sanity ok | 0.1h | 2026-03-20 |
| Run 1.1 | passed | val acc=0.847 (+4.7%) | 4.2h | 2026-03-21 |
```

## 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| 命令 | ✅ | 任意 shell 命令 |
| 成功条件 | ✅ | 自然语言，LLM 判断 |
| 验收命令 | 可选 | shell 命令，exit code 作为硬门控 |
| 输出目录 | 可选 | artifact 收集路径；未填时从命令参数推断 |
| 镜像 | 可选 | 容器未就绪时用于拉取 |
| GPU budget | ✅ | 0h 表示 CPU only |
