#!/usr/bin/env python3
"""
Build test set from Prometheus Feedback-Collection.

Outputs two files:
  test_prometheus.jsonl       — one pair per unique criteria (for AUROC)
  test_prometheus_full.jsonl  — all (criteria, orig_score) tuples (for Spearman)

Usage:
  python prep_test_set.py \
    --model ~/online1/models/Qwen2.5-VL-7B-Instruct \
    --output-dir data/ \
    --n-criteria 500
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def load_prometheus_grouped(n_criteria=500, seed=42, local_jsonl=None):
    """
    Returns:
      criteria_samples: dict[criteria_text -> list[{instruction, orig_score}]]
    Samples n_criteria unique criteria from the dataset.
    """
    if local_jsonl and Path(local_jsonl).exists():
        raw = []
        with open(local_jsonl, encoding="utf-8") as f:
            for line in f:
                raw.append(json.loads(line))
        print(f"Loaded {len(raw)} rows from {local_jsonl}")
    else:
        from datasets import load_dataset
        print("Loading prometheus-eval/Feedback-Collection ...")
        ds = load_dataset("prometheus-eval/Feedback-Collection", split="train")
        raw = list(ds)
        print(f"Total rows: {len(raw)}")

    # Group by criteria
    by_criteria = defaultdict(list)
    for row in raw:
        criteria = row.get("orig_criteria", "").strip()
        instruction = row.get("orig_instruction", "").strip()
        score = row.get("orig_score")
        if not criteria or not instruction or score is None:
            continue
        by_criteria[criteria].append({
            "instruction": instruction,
            "orig_score": int(score),
        })

    # Sample n_criteria diverse ones (prefer criteria with score variance)
    random.seed(seed)
    import numpy as np
    scored_criteria = []
    for criteria, samples in by_criteria.items():
        scores = [s["orig_score"] for s in samples]
        variance = float(np.var(scores)) if len(scores) > 1 else 0.0
        scored_criteria.append((criteria, samples, variance))

    # Sort by variance desc, then sample evenly to get diversity
    scored_criteria.sort(key=lambda x: -x[2])
    selected = scored_criteria[:n_criteria]
    random.shuffle(selected)

    result = {c: samples for c, samples, _ in selected}
    print(f"Selected {len(result)} unique criteria")
    return result


def generate_llm_rubrics_for_criteria(criteria_samples, model_path, batch_size=4):
    """Generate one LLM rubric per unique criteria."""
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    PROMPT = ("You are an evaluation assistant. Given the instruction below, "
              "write 4-6 evaluation criteria as Yes/No questions starting with 'Does the'.\n\n"
              "Instruction: {instruction}\n\nCriteria:")

    print(f"Loading {model_path} ...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    device = next(model.parameters()).device

    criteria_list = list(criteria_samples.keys())
    # Use the first instruction for each criteria as the generation prompt
    instructions = [criteria_samples[c][0]["instruction"] for c in criteria_list]

    rubrics = []
    for i in range(0, len(instructions), batch_size):
        batch_inst = instructions[i:i + batch_size]
        raw_prompts = [PROMPT.format(instruction=inst) for inst in batch_inst]
        # Apply chat template for Qwen3 models
        formatted = []
        for p in raw_prompts:
            messages = [{"role": "user", "content": p}]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            formatted.append(text)
        inputs = tokenizer(
            formatted, return_tensors="pt", padding=True,
            truncation=True, max_length=1024,
        ).to(device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs, max_new_tokens=200, do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        input_len = inputs["input_ids"].shape[1]
        for out in outputs:
            text = tokenizer.decode(out[input_len:], skip_special_tokens=True).strip()
            rubrics.append(text)
        if (i // batch_size + 1) % 20 == 0:
            print(f"  {min(i+batch_size, len(instructions))}/{len(instructions)}")

    return {c: r for c, r in zip(criteria_list, rubrics)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="/online1/sc100123/sc100123/data/Qwen3-4B")
    parser.add_argument("--output-dir", default="data/")
    parser.add_argument("--local-prometheus", default=None,
                        help="Local JSONL if HF is unavailable")
    parser.add_argument("--n-criteria", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()

    import torch
    model_path = str(Path(args.model).expanduser())
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # ── Load & group Prometheus ───────────────────────────────────────────
    criteria_samples = load_prometheus_grouped(
        n_criteria=args.n_criteria,
        local_jsonl=args.local_prometheus,
    )

    # ── Generate LLM rubrics (one per criteria) ───────────────────────────
    print(f"Generating LLM rubrics for {len(criteria_samples)} criteria ...")
    llm_rubrics = generate_llm_rubrics_for_criteria(
        criteria_samples, model_path, batch_size=args.batch_size
    )

    # ── Write test_prometheus.jsonl (one pair per criteria, for AUROC) ────
    auroc_path = Path(args.output_dir) / "test_prometheus.jsonl"
    with open(auroc_path, "w", encoding="utf-8") as f:
        for criteria, samples in criteria_samples.items():
            record = {
                "instruction":  samples[0]["instruction"],
                "human_rubric": criteria,
                "llm_rubric":   llm_rubrics[criteria],
                "orig_score":   samples[0]["orig_score"],
                "source":       "prometheus",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"AUROC test set: {auroc_path} ({len(criteria_samples)} pairs)")

    # ── Write test_prometheus_full.jsonl (all scores per criteria, for Spearman) ──
    full_path = Path(args.output_dir) / "test_prometheus_full.jsonl"
    total = 0
    with open(full_path, "w", encoding="utf-8") as f:
        for criteria, samples in criteria_samples.items():
            for s in samples:
                record = {
                    "instruction":  s["instruction"],
                    "human_rubric": criteria,
                    "llm_rubric":   llm_rubrics[criteria],
                    "orig_score":   s["orig_score"],
                    "source":       "prometheus",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total += 1
    print(f"Full Spearman set: {full_path} ({total} rows, "
          f"~{total//len(criteria_samples)} per criteria)")


if __name__ == "__main__":
    main()
