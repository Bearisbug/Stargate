# EBM Project — 决策记忆

## 最终目标（重要）

**两阶段流程**：
1. **阶段1（当前）**：训练 EBM 作为 rubric 质量 reward model
2. **阶段2（后续）**：用 EBM 分数训练高质量 rubric 生成器（RLHF/DPO/RFT）

**EBM 的定位**：通用 rubric 质量评分器，不只是"人工 vs LLM"分类器。

**双测试集逻辑**：
- RubricBench test：测 human-expert vs Qwen-7B（最强区分度，验证基础能力）
- Prometheus test：测 GPT-4 级别 vs Qwen-7B（质量分级，更接近 reward model 真实使用场景）

两个都高分 → EBM 可以作为阶段2的 reward model。

---

## 项目配置（project-init）

- **服务器**: `sc100123@174.0.250.88`，SSH 公钥认证已验证
- **工作目录**: `~/online1/ebm_rubirc`
- **可观测性**: Langfuse 暂未启用，使用 `session-trace.json` 本地记录

---

## 实验设计（experiment-plan · from-paper）

### 任务定义
训练 Energy-Based Model 区分 human-written rubric（低能量）vs LLM-generated rubric（高能量）

### 数据来源
- **RubricBench** (`DonJoey/rubricbench`)：1147 条样本，5 个 domain，含 human_rubric + 5 种 LLM 系统生成的 rubric

### 方法适配
- 原文 EORM 做 CoT 解题对比（正确 vs 错误）→ 适配为 rubric 质量对比（人类 vs LLM）
- 架构不变：DeBERTa-v3-base → [CLS] → LayerNorm → MLP → scalar energy
- 损失不变：Bradley-Terry pairwise loss

### 关键决策
| 决策点 | 选择 | 原因 |
|--------|------|------|
| Base model | microsoft/deberta-v3-base (183M) | 更适合文本分类/排序，优于原文 55M 小模型 |
| 正样本 | human_rubric | 低能量 = 高质量，与用户目标一致 |
| 负样本 | 5 种 LLM 系统 rubric | RubricBench 现成标注，全部用于配对 |
| Claim 1 | 数据管道验证 (CPU) | 先确认数据格式正确，不浪费 GPU |
| Claim 2 | AUROC ≥ 0.75 | 合理基线，random=0.5，strong=0.9 |
| Claim 3 | 留一法跨系统泛化 | 验证通用性，避免过拟合特定 LLM 系统 |

---

## 环境探测（experiment-environment · in_progress）

| 项目 | 结果 |
|------|------|
| exec_type | `slurm-singularity`（Apptainer via module） |
| Slurm partition | `q_intel_gpu_nvidia_h20_10` |
| GPU | H20 × 8/节点，96GB VRAM |
| 容器方案 | `module load amd/apptainer/1.2.5` |
| Conda | `/online1/public/support/amd/miniconda3/latest/bin/conda` |
| Python | 3.12.7 |
| **状态** | **待完成**: 确认镜像，写 env_handle.json |

---

## 实验代码（experiment-code · completed）

生成并上传到 `~/online1/ebm_rubirc/code/`:
- `data_prep.py` — 下载 RubricBench，构造训练对
- `train.py` — EBM 训练（Bradley-Terry loss）
- `eval.py` — AUROC 评估 / LOO 结果汇总
- `loo_eval.py` — 留一法 5 折评估

## 实验设计 v2（已解决数据集问题）

**关键发现**：RubricBench 只有 human rubric，无 LLM 版本。参考 EORM 的 group-level 训练思路：
- 每条 instruction = 1 个 group：1 human rubric（正）× 5 LLM rubric（负，5种 prompt 变体生成）
- 1147 instructions → 5735 对，group-level BT loss
- 测试集：Prometheus Feedback-Collection（500条，orig_criteria 作正样本）

**模型对比**：gpt2(117M) / bert-base(110M) / roberta-base(125M) / deberta-v3-small(44M)，各3种 LR + 标准/自适应 loss

**当前状态**：Job 1254604 已提交，run_all.sh（数据生成→训练→评估全流程），预计 ~8h

## 数据集问题（已解决）

**发现**：`DonJoey/rubricbench` 只有 `rubrics`（人工标注）字段，无 LLM 生成 rubric。

**影响**：训练对 (human_rubric, llm_rubric) 无法直接构造。

**待决策**：
- **选项 A**（推荐）：用 Qwen2.5-7B（已在服务器 `~/online1/models/`）生成 LLM rubric 作为负样本，需加 `gen_llm_rubrics.py` 步骤
- **选项 B**：改为奖励模型任务，正=(instruction, rubric, preferred_response)，负=(instruction, rubric, rejected_response)，数据即开即用

**其他问题**：
- HuggingFace 被服务器代理拦截，需本地下载后 scp 上传
- Slurm job 1254585 仍在 PENDING，GPU 节点全忙
- 数据集 split 名为 `train`（非 `test`），需修正 `data_prep.py`

---

*最后更新: 2026-03-22 · session-trace.json 有完整结构化记录*
