#!/usr/bin/env python3
"""
Merge RubricBench human rubrics with generated LLM rubrics into
group-level JSONL files for train_ebm.py.

Input:
  data/rubricbench_raw.jsonl   — RubricBench samples (case_id, instruction, rubrics, ...)
  data/llm_rubrics.jsonl       — Generated LLM rubrics (case_id, llm_rubric, llm_system, ...)

Output:
  data/train_groups.jsonl
  data/val_groups.jsonl
  data/test_groups.jsonl   (held-out split from RubricBench)

Each output line: {case_id, instruction, human_rubric, llm_rubric, llm_system, domain, split}

Usage:
  python data_prep.py                            # build splits
  python data_prep.py --stats                    # print statistics only
  python data_prep.py --hard-negatives           # include hard negatives (see note below)
  python data_prep.py --tokenize-check --model bert-base-uncased

Hard negatives note:
  RubricBench has pairwise preference labels (which response is preferred). A "hard negative"
  would be a rubric that predicts the *wrong* winner when applied to a pair. However, since
  all rubrics in RubricBench are human-written (positive samples), we cannot use them as
  hard negatives without an oracle scorer that applies each rubric to the response pairs.
  The --hard-negatives flag currently mines cross-instruction rubric mismatches: rubrics
  from other instructions that happen to share the same domain but are semantically wrong
  for this instruction. These are harder than random LLM rubrics but softer than true
  preference-inconsistent rubrics.
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def load_jsonl(path):
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    return items


def mine_hard_negatives(human_by_case, seed=42):
    """
    Mine cross-instruction hard negatives from RubricBench.

    Strategy: for each instruction, take human rubrics from other instructions
    in the same domain. These are "wrong rubric for this instruction" negatives —
    structurally valid rubrics (human-written quality) but semantically mismatched
    to the instruction, making them harder to distinguish than LLM-generated rubrics.

    Returns: list of dicts with keys {case_id, instruction, human_rubric,
             llm_rubric (=mismatched human rubric), llm_system, domain}
    """
    rng = random.Random(seed)

    # Group case_ids by domain
    by_domain = defaultdict(list)
    for cid, item in human_by_case.items():
        domain = item.get("domain", "unknown")
        by_domain[domain].append(cid)

    hard_negs = []
    for cid, item in human_by_case.items():
        domain = item.get("domain", "unknown")
        domain_cases = [c for c in by_domain[domain] if c != cid]
        if not domain_cases:
            # Fall back to any other case if domain is singleton
            domain_cases = [c for c in human_by_case if c != cid]
        if not domain_cases:
            continue

        # Sample one hard negative (mismatched-domain rubric)
        donor_cid = rng.choice(domain_cases)
        donor = human_by_case[donor_cid]
        hard_negs.append({
            "case_id":      cid,
            "instruction":  item["instruction"],
            "human_rubric": item["rubrics"].strip(),
            "llm_rubric":   donor["rubrics"].strip(),
            "llm_system":   "hard-neg-cross-instruction",
            "variant_idx":  -1,
            "domain":       domain,
        })

    print(f"Hard negatives mined: {len(hard_negs)} "
          f"(cross-instruction rubric mismatches from same domain)")
    return hard_negs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rubricbench", default="data/rubricbench_raw.jsonl")
    parser.add_argument("--llm-rubrics", default="data/llm_rubrics.jsonl")
    parser.add_argument("--output-dir", default="data/")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--tokenize-check", action="store_true")
    parser.add_argument("--model", default="bert-base-uncased")
    parser.add_argument("--hard-negatives", action="store_true",
                        help="Add cross-instruction hard negatives from RubricBench "
                             "(human rubrics from same-domain but different instructions)")
    args = parser.parse_args()

    # ── Load ────────────────────────────────────────────────────────────────
    rb = load_jsonl(args.rubricbench)
    human = {item["case_id"]: item for item in rb}
    print(f"RubricBench: {len(human)} instructions")

    llm_raw = load_jsonl(args.llm_rubrics)
    llm_by_case = defaultdict(list)
    for item in llm_raw:
        llm_by_case[item["case_id"]].append(item)
    print(f"LLM rubrics: {len(llm_raw)} total, "
          f"{len(llm_by_case)} instructions covered")

    # ── Build pairs ─────────────────────────────────────────────────────────
    pairs = []
    for cid, h in human.items():
        llm_items = llm_by_case.get(cid, [])
        if not llm_items:
            continue
        human_rubric = h["rubrics"].strip()
        for llm in llm_items:
            pairs.append({
                "case_id":      cid,
                "instruction":  h["instruction"],
                "human_rubric": human_rubric,
                "llm_rubric":   llm["llm_rubric"],
                "llm_system":   llm["llm_system"],
                "variant_idx":  llm.get("variant_idx", 0),
                "domain":       h.get("domain", "unknown"),
            })
    print(f"Style-negative pairs (LLM-generated): {len(pairs)}")

    # ── Hard negatives ───────────────────────────────────────────────────────
    if args.hard_negatives:
        hard_negs = mine_hard_negatives(human, seed=args.seed)
        pairs.extend(hard_negs)
        print(f"Total pairs after adding hard negatives: {len(pairs)}")
    else:
        print(f"Total pairs: {len(pairs)} (use --hard-negatives to add cross-instruction negatives)")

    if args.stats:
        cases_covered = len(set(p["case_id"] for p in pairs))
        neg_per_case = len(pairs) / max(cases_covered, 1)
        domains = defaultdict(int)
        for p in pairs:
            domains[p["domain"]] += 1
        print(f"Cases with pairs: {cases_covered} / {len(human)}")
        print(f"Avg LLM rubrics/case: {neg_per_case:.1f}")
        print("Domain distribution:")
        for d, cnt in sorted(domains.items(), key=lambda x: -x[1])[:10]:
            print(f"  {d}: {cnt}")
        return

    # ── Split by case_id (not by pair) to avoid leakage ────────────────────
    all_cases = sorted(set(p["case_id"] for p in pairs))
    random.seed(args.seed)
    random.shuffle(all_cases)
    n = len(all_cases)
    train_cases = set(all_cases[:int(n * 0.8)])
    val_cases   = set(all_cases[int(n * 0.8):int(n * 0.9)])
    test_cases  = set(all_cases[int(n * 0.9):])

    split_pairs = {"train": [], "val": [], "test": []}
    for p in pairs:
        if p["case_id"] in train_cases:
            split_pairs["train"].append(p)
        elif p["case_id"] in val_cases:
            split_pairs["val"].append(p)
        else:
            split_pairs["test"].append(p)

    # ── Tokenize check ──────────────────────────────────────────────────────
    if args.tokenize_check:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        long = 0
        for p in pairs:
            text = p["instruction"] + " [SEP] " + p["human_rubric"]
            if len(tokenizer(text, truncation=False)["input_ids"]) > 512:
                long += 1
        pct = long / len(pairs) * 100
        print(f"Tokenize check: {long}/{len(pairs)} ({pct:.1f}%) exceed 512 tokens")

    # ── Write ────────────────────────────────────────────────────────────────
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    for split, data in split_pairs.items():
        path = Path(args.output_dir) / f"{split}_groups.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        n_cases = len(set(p["case_id"] for p in data))
        print(f"{split}: {len(data)} pairs, {n_cases} groups → {path}")


if __name__ == "__main__":
    main()
