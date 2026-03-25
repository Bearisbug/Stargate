#!/bin/bash
#SBATCH --job-name=sst2_baseline
#SBATCH -p q_intel_gpu_nvidia_h20_10
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/online1/sc100123/sc100123/sst2_baseline/logs/%j.out
#SBATCH --error=/online1/sc100123/sc100123/sst2_baseline/logs/%j.err

set -e

WORK_DIR=/online1/sc100123/sc100123/sst2_baseline
MODEL_PATH=/online1/sc100123/sc100123/data/Qwen3-4B
CACHE_BASE=/online1/sc100123/sc100123/cache

# ── 缓存目录重定向（home 目录有 quota 限制）────────────────
export HF_HOME=${CACHE_BASE}/hf_home
export HF_DATASETS_CACHE=${CACHE_BASE}/hf_datasets
export TRITON_CACHE_DIR=${CACHE_BASE}/triton
export TMPDIR=${CACHE_BASE}/tmp
mkdir -p ${HF_HOME} ${HF_DATASETS_CACHE} ${TRITON_CACHE_DIR} ${TMPDIR}

# ── 环境初始化 ────────────────────────────────────────────
module load intel/gcc_compiler/10.3.0
module load amd/cudnn/9.6.0
source /online1/public/support/amd/miniconda3/latest/etc/profile.d/conda.sh
conda activate lf

cd ${WORK_DIR}
mkdir -p logs data runs

# ── Step 1: 验证数据集（已预先上传） ─────────────────────
echo "===== Step 1: Verify SST-2 dataset ====="
ls ${WORK_DIR}/data/sst2_train.json ${WORK_DIR}/data/sst2_val.json ${WORK_DIR}/data/dataset_info.json

# ── Step 2: SFT 微调 ─────────────────────────────────────
echo "===== Step 2: LoRA SFT training ====="
llamafactory-cli train code/lora_sft.yaml

# ── Step 3: 评估 accuracy ─────────────────────────────────
echo "===== Step 3: Evaluate accuracy on SST-2 validation set ====="
python code/eval_accuracy.py \
    --model ${MODEL_PATH} \
    --adapter runs/qwen3-4b-lora \
    --data data/sst2_val.json \
    --output runs/qwen3-4b-lora/eval_results.json \
    --batch-size 32

echo "===== All steps completed ====="
cat runs/qwen3-4b-lora/eval_results.json
