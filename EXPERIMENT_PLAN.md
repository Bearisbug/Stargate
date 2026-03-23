# EBM for Rubric Quality Discrimination — v3

## 背景

训练 EBM 区分 human-written rubric（低能量）vs LLM-generated rubric（高能量）。

**训练集**：RubricBench（`DonJoey/rubricbench`，1147 instructions，human rubric 作正样本）

**负样本策略（两类）**：
1. **Style negatives**：Qwen3-4B 用 5 种 prompt 变体生成的 rubric（与人工 rubric 文风不同）
2. **Hard negatives**：跨 instruction 错配的 human rubric（同 domain 但不同 instruction，结构上合法但语义上不匹配）

**测试集**：Prometheus Feedback-Collection（`prometheus-eval/Feedback-Collection`，500条采样，`orig_criteria` 作正样本，Qwen3-4B 生成负样本）

**方法**：Group-level Bradley-Terry loss（对 EORM 方法的适配）
```
Group Y_n: 1 human rubric (Y₊) × (5 style + 1 hard) LLM rubrics (Y₋)
L = (1/6) Σ_k log(1 + exp(E(human) - E(neg_k)))
```

**负样本生成模型**：Qwen3-4B（`/online1/sc100123/sc100123/data/Qwen3-4B`）
- 使用 chat template（`apply_chat_template` + `enable_thinking=False`）
- 同时用于 RubricBench 负样本生成和 Prometheus 测试集负样本生成

**代码文件**：
- `gen_llm_rubrics.py` — Qwen3-4B 5种 prompt 生成多样化负样本（含 chat template）
- `prep_test_set.py` — 构建 Prometheus 测试集（Qwen3-4B 负样本，含 chat template）
- `data_prep.py` — 合并 rubric，构建 group-level splits（`--hard-negatives` 启用交叉 instruction 硬负样本）
- `models.py` — EBM 架构（4种）
- `train_ebm.py` — 训练入口（group-level BT loss，支持 adaptive）
- `eval_ebm.py` — 评估 + 多模型对比
- `run_all.sh` — 一键跑全流程（Qwen3-4B，含 hard negatives）

---

## Claim 1：数据管道正确，训练对覆盖全量指令

**假设**：生成 5735 个 Qwen3-4B style-negative rubric + 1147 个 hard-negative rubric，构造后 train/val/test 覆盖全部 1147 instructions，无数据泄露。

### Run 1.0 — sanity
- 命令: `python code/gen_llm_rubrics.py --model /online1/sc100123/sc100123/data/Qwen3-4B --input data/rubricbench_raw.jsonl --output data/llm_rubrics.jsonl --n-per-instruction 1 --batch-size 8`
- 成功条件: 1147 条 llm_rubrics 生成无报错，每条 rubric 长度合理（>20 字符），`llm_system` 字段显示 `qwen3-4b-v1`
- GPU budget: 0.3h

### Run 1.1 — full
- 命令: `python code/gen_llm_rubrics.py --n-per-instruction 5 --resume && python code/prep_test_set.py --n-criteria 500 && python code/data_prep.py --stats --hard-negatives && python code/data_prep.py --hard-negatives`
- 成功条件: `data/llm_rubrics.jsonl` 有 ≥5000 条，`train_groups.jsonl` ≥800 groups，`test_prometheus.jsonl` ≥400 对，hard negatives ≥ 900 条
- GPU budget: 1h

---

## Claim 2：模型对比——4种 encoder × 3种 LR × 标准/自适应 loss

**假设**：至少 1 个模型配置在 val AUROC ≥ 0.72（含 hard negatives，任务更难），即 EBM 能在 RubricBench held-out 上区分 human vs mixed-negative rubric。

对比矩阵（共 16 个 run）：

| 模型 | 参数量 | LR 候选 |
|------|--------|---------|
| gpt2 | 117M | 1e-5, 2e-5, 5e-5 |
| bert-base | 110M | 1e-5, 2e-5, 5e-5 |
| roberta-base | 125M | 1e-5, 2e-5, 5e-5 |
| deberta-v3-small | 44M | 1e-5, 2e-5, 5e-5 |

每个模型在 LR=2e-5 时额外跑一次 adaptive BT loss。

### Run 2.0 — sanity
- 命令: `python code/train_ebm.py --model bert-base --lr 2e-5 --n-neg 5 --epochs 1 --max-steps 50 --output-dir runs/sanity`
- 成功条件: loss 下降（50步后 < 0.693），无 nan
- GPU budget: 0.1h

### Run 2.1 — full
- 命令: `bash code/run_all.sh` (Step 4)
- 成功条件: 最优配置 val AUROC ≥ 0.72
- 输出目录: `/online1/sc100123/sc100123/ebm_rubirc/runs/`
- GPU budget: 6h

---

## Claim 3：n_neg 消融 + Prometheus 跨域泛化

**假设**：最优模型在 Prometheus 测试集（完全不同 domain 和 instruction 来源）上 AUROC ≥ 0.70，验证 EBM 学到通用 rubric 质量信号而非 RubricBench-specific 特征。

额外消融：n_neg=1 vs 3 vs 5 的影响。

### Run 3.0 — sanity
- 命令: `python code/eval_ebm.py --model-dir runs/sanity --model-key bert-base --data data/test_prometheus.jsonl`
- 成功条件: 脚本无报错，输出 auroc 值（哪怕随机水平也可）
- GPU budget: 0.1h

### Run 3.1 — full
- 命令: `bash code/run_all.sh` (Step 5-6，在 Claim 2 完成后自动执行)
- 成功条件: Prometheus 测试集 AUROC ≥ 0.70，energy_gap > 0（human < llm 能量）
- 验收命令: `python code/eval_ebm.py --compare runs/*/ --data data/test_prometheus.jsonl`
- GPU budget: 0.5h

---

## GPU Budget 汇总

| Claim | Sanity | Full | 合计 |
|-------|--------|------|------|
| 1 (数据生成) | 0.3h | 1h | 1.3h |
| 2 (16个模型) | 0.1h | 6h | 6.1h |
| 3 (消融+泛化) | 0.1h | 0.5h | 0.6h |
| **总计** | | | **~8h** |

单卡 H20 可完成全部实验。`run_all.sh` 串行执行所有步骤。

---

## 变更日志

| 版本 | 变更内容 |
|------|---------|
| v1 | 初始设计，Qwen2.5-7B，仅 style negatives |
| v2 | 改用 group-level BT loss，添加 Prometheus 测试集 |
| v3 | 切换至 Qwen3-4B（chat template），添加 hard negatives（跨 instruction 错配），AUROC 阈值调整为 0.72 |
