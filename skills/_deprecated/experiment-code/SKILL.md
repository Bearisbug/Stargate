---
name: experiment-code
description: 为实验计划生成或规范代码框架。在有 EXPERIMENT_PLAN.md 但代码尚未存在，或需要检查代码是否符合可复现性规范时使用。
---

# 实验代码

## 使用时机

- `EXPERIMENT_PLAN.md` 中标注了 `[需要 experiment-code]`
- 用户提供了论文/idea，但没有对应代码
- 检查已有代码是否满足可复现性要求

## 三种任务类型的规范

| 任务类型 | 参考 |
|---------|------|
| SFT（监督微调） | [references/sft.md](references/sft.md) |
| RFT / GRPO / PPO（强化微调） | [references/rft.md](references/rft.md) |
| 通用 DL 训练（分类、检测等） | [references/dl.md](references/dl.md) |

## 代码组织规范（所有任务通用）

```
<experiment_dir>/
  train.py          # 训练入口，支持命令行参数
  eval.py           # 评测入口（可选，若验收命令需要）
  config/
    default.yaml    # 默认超参配置
  src/
    model.py        # 模型定义
    data.py         # 数据加载
    trainer.py      # 训练逻辑
  requirements.txt  # 依赖列表
  README.md         # 复现说明
```

## 可复现性检查清单

生成或检查代码时，确保满足：

- [ ] 随机种子固定（`--seed` 参数，影响 torch / numpy / random）
- [ ] 所有超参通过命令行传入，不硬编码在代码里
- [ ] 训练日志输出到 stdout（格式含 `step=N loss=X`，供 viz.py 解析）
- [ ] 模型 checkpoint 按 epoch/step 保存，路径可配置
- [ ] eval 脚本接受 checkpoint 路径，独立于训练可运行
- [ ] `requirements.txt` 固定版本号

## 代码缺失时的处理

若任务是"从零生成代码框架"：
1. 根据 EXPERIMENT_PLAN.md 的命令格式，反推需要哪些参数
2. 按对应任务类型的规范生成 `train.py` 骨架
3. 标注所有 `TODO` 和 `<PLACEHOLDER>` 供用户填写
4. 生成 `requirements.txt`（基于推断的依赖）
