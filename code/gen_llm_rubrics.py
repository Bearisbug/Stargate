#!/usr/bin/env python3
"""
Generate diverse LLM rubrics for each instruction using a local model.
Each instruction gets N rubrics from different prompts (diversity via prompt variation).
These become negative samples for EBM training.

Usage:
  python gen_llm_rubrics.py \
    --model ~/online1/models/Qwen2.5-VL-7B-Instruct \
    --input data/rubricbench_raw.jsonl \
    --output data/llm_rubrics.jsonl \
    --n-per-instruction 5
"""
import argparse
import json
from pathlib import Path

# 5 prompt variants that produce rubrics with different failure modes:
# 1) generic (not tailored to instruction)  2) minimal/lazy  3) surface-level
# 4) template-mechanical  5) negative framing
PROMPT_VARIANTS = [
    # V1: Standard — should produce somewhat reasonable but generic rubric
    "You are an evaluation assistant. Given the instruction below, write 4-6 evaluation criteria as Yes/No questions starting with 'Does the'.\n\nInstruction: {instruction}\n\nCriteria:",

    # V2: Minimal — produces short, lazy rubric
    "List 3 simple yes/no checks for evaluating a response to this instruction.\n\nInstruction: {instruction}\n\nChecks:",

    # V3: Surface-level — focuses on form over content
    "What surface-level features should a good response to the following instruction have? Write as checklist items.\n\nInstruction: {instruction}\n\nChecklist:",

    # V4: Template-mechanical — generic template, ignores specifics
    "Evaluate the response on: Clarity, Accuracy, Completeness, Helpfulness, and Tone. Write one Yes/No criterion for each.\n\nInstruction: {instruction}\n\nCriteria:",

    # V5: Negative framing — focuses on mistakes rather than criteria
    "What common mistakes should a response to the following instruction avoid? Write as 4-5 Yes/No questions about the absence of mistakes.\n\nInstruction: {instruction}\n\nCriteria:",
]


def load_data(path):
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    print(f"Loaded {len(items)} items from {path}")
    return items


def generate_batch(model, tokenizer, prompts, max_new_tokens=200, device="cuda"):
    import torch
    # Apply chat template for Qwen3 models (required for correct formatting)
    formatted = []
    for p in prompts:
        messages = [{"role": "user", "content": p}]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        formatted.append(text)
    inputs = tokenizer(formatted, return_tensors="pt", padding=True, truncation=True, max_length=1024).to(device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    results = []
    input_len = inputs["input_ids"].shape[1]
    for out in outputs:
        text = tokenizer.decode(out[input_len:], skip_special_tokens=True).strip()
        results.append(text)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="/online1/sc100123/sc100123/data/Qwen3-30B-A3B")
    parser.add_argument("--input", default="data/rubricbench_raw.jsonl")
    parser.add_argument("--output", default="data/llm_rubrics.jsonl")
    parser.add_argument("--n-per-instruction", type=int, default=5,
                        help="Number of LLM rubric variants per instruction (max 5)")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    model_path = str(Path(args.model).expanduser())
    n_variants = min(args.n_per_instruction, len(PROMPT_VARIANTS))

    items = load_data(args.input)

    # Resume: skip already-done (case_id, variant_idx) pairs
    done = set()
    if args.resume and Path(args.output).exists():
        with open(args.output, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                done.add((r["case_id"], r["variant_idx"]))
        print(f"Resuming: {len(done)} already done")

    print(f"Loading model {model_path} ...")
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.bfloat16, device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    device = next(model.parameters()).device

    out_file = open(args.output, "a", encoding="utf-8")
    total_written = 0

    for v_idx in range(n_variants):
        prompt_template = PROMPT_VARIANTS[v_idx]
        print(f"\n=== Variant {v_idx+1}/{n_variants} ===")

        todo = [item for item in items if (item["case_id"], v_idx) not in done]
        print(f"  {len(todo)} instructions to process")

        for i in range(0, len(todo), args.batch_size):
            batch = todo[i:i + args.batch_size]
            prompts = [prompt_template.format(instruction=it["instruction"]) for it in batch]
            rubrics = generate_batch(model, tokenizer, prompts, device=device)

            for item, rubric in zip(batch, rubrics):
                model_tag = Path(args.model).name.lower().replace("-instruct", "")
                record = {
                    "case_id": item["case_id"],
                    "llm_rubric": rubric,
                    "llm_system": f"{model_tag}-v{v_idx+1}",
                    "variant_idx": v_idx,
                }
                out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_file.flush()
                total_written += 1

            if (i // args.batch_size + 1) % 20 == 0:
                done_count = i + len(batch)
                print(f"  {done_count}/{len(todo)} done")

    out_file.close()
    total = sum(1 for _ in open(args.output))
    print(f"\nDone. {args.output}: {total} records total ({total_written} new)")


if __name__ == "__main__":
    main()
