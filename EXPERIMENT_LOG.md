# Experiment Log

## 2026-03-25 — Session Start

**输入来源**：自然语言 idea
**原始输入**：在 SST-2 数据集上用 Qwen3-4B 跑一个基线情感分类实验，记录 accuracy 和 loss

**提取的 Claims**：
- Claim 1：Qwen3-4B 在 SST-2 上做情感分类微调，目标指标：eval_accuracy + eval_loss
  - 成功标准：pipeline 完整跑通，得到具体数值，无报错退出

**决策**：
- 任务类型：监督微调 SFT（SST-2 二分类，transformers + PEFT/LoRA 或全参微调）
- 平台：Slurm 集群（sc100123@174.0.250.88），conda 运行环境
- 下一步：ENVIRONMENT 阶段，连接服务器，探测 GPU/conda 情况

## 2026-03-25T04:00 — ENVIRONMENT 验证 + WAITING

**ENVIRONMENT 验证结果**：
- SSH 连接正常（174.0.250.88:22，需 ConnectTimeout≥30s）
- conda env `lf` 可用：torch==2.6.0+cu124, llamafactory, peft==0.17.1, datasets
- module load: `amd/cudnn/9.6.0`
- HuggingFace 不可达（已离线），SST-2 数据已预先转换至服务器 `/online1/sc100123/sc100123/sst2_baseline/data/`
- 模型 Qwen3-4B 在 `/online1/sc100123/sc100123/data/Qwen3-4B/`
- GPU 节点：q_intel_gpu_nvidia_h20_10（H20）

**DESIGN+EXECUTING**（上一 session 已完成）：
- 代码：LLaMA-Factory LoRA SFT，`lora_sft.yaml`（r=16, alpha=32, lr=1e-4, epochs=3, bs=16）
- 评测：`eval_accuracy.py`，生成式分类（positive/negative 字符串匹配）
- Job 1264081 于 2026-03-25T01:23:16 提交，状态 PENDING（Priority）
- 预期输出：`runs/qwen3-4b-lora/eval_results.json`

**当前**：WAITING，周期性监控 job 1264081

## 2026-03-25T10:30 — WAITING 轮询

- job 1264081 状态：**PENDING (Priority)**，尚未开始运行
- 继续等待，下次轮询时再检查

## 2026-03-25T11:30 — 错误诊断 + 修复 + 重试（第一次修复）

- job 1264081 状态：**COMPLETING（已结束）**，`eval_results.json` 不存在
- **根因**：系统 gcc 4.8.5 不含 `stdatomic.h`（GCC 4.9 才引入），`triton` import 时编译 `cuda_utils.c` 失败，导致 `deepspeed → trl → llamafactory` 全链路 ImportError
- **修复**：在 SBATCH 脚本添加 `module load intel/gcc_compiler/10.3.0`，commit: 56557e9
- 重新提交：job **1267164**（retry_count: 1）

## 2026-03-25T09:50 — 错误诊断 + 第二次修复

- job 1267164 状态：**FAILED**（ExitCode 1:0）
- gcc 问题已修复，进入训练初始化；但 pyarrow 写数据集缓存时失败
- **根因**：`~/.cache/huggingface/datasets/` 和 `~/.triton/` 均在 home 目录，home 目录 user quota 已满（OSError: [Errno 122] Disk quota exceeded）
- **修复**：在 SBATCH 脚本中设置 `HF_HOME`、`HF_DATASETS_CACHE`、`TRITON_CACHE_DIR`、`TMPDIR` 全部重定向到 `/online1/sc100123/sc100123/cache/`（1.1PB 可用）
- 下一步：commit 后重新提交（retry_count: 2）
