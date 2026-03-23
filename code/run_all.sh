#!/bin/bash
# Master job: data generation → model comparison → final eval
#SBATCH --job-name=ebm_all
#SBATCH -p q_intel_gpu_nvidia_h20_10
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --output=/online1/sc100123/sc100123/ebm_rubirc/logs/run_all_%j.out
#SBATCH --error=/online1/sc100123/sc100123/ebm_rubirc/logs/run_all_%j.err

set -e
cd /online1/sc100123/sc100123/ebm_rubirc

module load amd/cudnn/9.6.0

source /online1/public/support/amd/miniconda3/latest/etc/profile.d/conda.sh
conda activate lf
mkdir -p logs runs data

MODEL_PATH=/online1/sc100123/sc100123/data/Qwen3-30B-A3B

# ── Step 1: Generate Qwen3-30B-A3B rubrics (5 variants × 1147 = 5735 rubrics) ────
echo "===== Step 1: Generate Qwen3-30B-A3B LLM rubrics ====="
python code/gen_llm_rubrics.py \
  --model $MODEL_PATH \
  --input data/rubricbench_raw.jsonl \
  --output data/llm_rubrics.jsonl \
  --n-per-instruction 5 \
  --batch-size 8 \
  --resume

# ── Step 2: Build Prometheus test set (Qwen3-4B negatives) ──────────────────
echo "===== Step 2: Build Prometheus test set (Qwen3-30B-A3B negatives) ====="
python code/prep_test_set.py \
  --model $MODEL_PATH \
  --output-dir data/ \
  --local-prometheus data/prometheus_raw.jsonl \
  --n-criteria 500 \
  --batch-size 8

# ── Step 3: Build training splits (with hard negatives) ──────────────────────
echo "===== Step 3: Build training splits ====="
python code/data_prep.py --stats --hard-negatives
python code/data_prep.py --hard-negatives

# ── Step 4: Model comparison (4 models × 3 LR × 2 loss = 24 runs) ───────────
echo "===== Step 4: Train all models ====="

MODELS=("gpt2" "bert-base" "roberta-base" "deberta-v3-small")
LRS=(1e-5 2e-5 5e-5)
N_NEG=5

for MODEL in "${MODELS[@]}"; do
  for LR in "${LRS[@]}"; do
    # Standard BT loss
    RUN_DIR="runs/${MODEL}_lr${LR}_n${N_NEG}"
    echo "--- Training: $RUN_DIR ---"
    python code/train_ebm.py \
      --model $MODEL \
      --lr $LR \
      --n-neg $N_NEG \
      --epochs 20 \
      --batch-size 16 \
      --output-dir $RUN_DIR

    # Adaptive BT loss (only for 2e-5, best LR candidate)
    if [ "$LR" = "2e-5" ]; then
      RUN_DIR_A="runs/${MODEL}_lr${LR}_n${N_NEG}_adaptive"
      echo "--- Training adaptive: $RUN_DIR_A ---"
      python code/train_ebm.py \
        --model $MODEL \
        --lr $LR \
        --n-neg $N_NEG \
        --epochs 20 \
        --batch-size 16 \
        --adaptive-loss \
        --output-dir $RUN_DIR_A
    fi
  done
done

# ── Step 5: n_neg ablation on best model (estimated: bert-base lr=2e-5) ──────
echo "===== Step 5: n_neg ablation ====="
for N in 1 3 5; do
  RUN_DIR="runs/bert-base_lr2e-5_n${N}"
  [ -d "$RUN_DIR" ] && continue
  python code/train_ebm.py \
    --model bert-base \
    --lr 2e-5 \
    --n-neg $N \
    --epochs 20 \
    --batch-size 16 \
    --output-dir $RUN_DIR
done

# ── Step 6: Final evaluation — both test sets ────────────────────────────────
echo "===== Step 6a: RubricBench test split (human-expert vs Qwen-7B) ====="
python code/eval_ebm.py \
  --compare runs/*/ \
  --data data/test_groups.jsonl

echo "===== Step 6b: Prometheus AUROC (GPT-4-level vs Qwen-7B) ====="
python code/eval_ebm.py \
  --compare runs/*/ \
  --data data/test_prometheus.jsonl \
  --spearman \
  --spearman-data data/test_prometheus_full.jsonl

# ── Step 7: Summary report ────────────────────────────────────────────────────
echo "===== Step 7: Write summary ====="
python - <<'EOF'
import json, glob, numpy as np
from pathlib import Path

results = {}
for cfg_path in sorted(glob.glob("runs/*/config.json")):
    run_dir = str(Path(cfg_path).parent)
    cfg = json.loads(open(cfg_path).read())
    key = f"{cfg['model']} lr={cfg['lr']} n={cfg['n_neg']}" + (" adaptive" if cfg.get("adaptive_loss") else "")
    # Read best val auroc from last checkpoint
    ckpts = sorted(glob.glob(f"{run_dir}/checkpoint_epoch*.pt"))
    if not ckpts:
        continue
    import torch
    last = torch.load(ckpts[-1], map_location="cpu")
    results[key] = {"val_auroc": last.get("val_auroc", 0), "run_dir": run_dir, "model": cfg["model"]}

if results:
    print("\n=== Val AUROC Summary ===")
    for k, v in sorted(results.items(), key=lambda x: -x[1]["val_auroc"])[:10]:
        print(f"  {k:<45} val_auroc={v['val_auroc']:.4f}")
    best_key = max(results, key=lambda k: results[k]["val_auroc"])
    print(f"\nBest model: {best_key}")
    print(f"Run dir: {results[best_key]['run_dir']}")
EOF

echo "===== All done ====="
