#!/usr/bin/env python3
"""
评估 Qwen3-4B LoRA checkpoint 在 SST-2 验证集上的 accuracy。
用法：
  python eval_accuracy.py \
    --model /online1/sc100123/sc100123/data/Qwen3-4B \
    --adapter runs/qwen3-4b-lora \
    --data data/sst2_val.json \
    --output results.json
"""
import argparse
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from tqdm import tqdm

LABELS = {"positive", "negative"}
INSTRUCTION = "Classify the sentiment of the following movie review as positive or negative."


def build_prompt(tokenizer, sentence: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"{INSTRUCTION}\n\n{sentence}"},
    ]
    # Qwen3 chat template; disable thinking mode for direct classification output
    try:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,  # Qwen3: skip <think> tokens for classification
        )
    except TypeError:
        # Older tokenizer version without enable_thinking
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    except Exception:
        text = f"### Instruction:\n{INSTRUCTION}\n\n### Input:\n{sentence}\n\n### Response:\n"
    return text


def parse_prediction(output: str) -> str:
    out = output.strip().lower()
    if out.startswith("positive"):
        return "positive"
    if out.startswith("negative"):
        return "negative"
    if "positive" in out:
        return "positive"
    if "negative" in out:
        return "negative"
    return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", default="results.json")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    args = parser.parse_args()

    print(f"Loading tokenizer from {args.model} ...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"Loading base model from {args.model} ...")
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    print(f"Loading LoRA adapter from {args.adapter} ...")
    model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    with open(args.data, encoding="utf-8") as f:
        records = json.load(f)

    prompts = [build_prompt(tokenizer, r["input"]) for r in records]
    labels = [r["output"].strip().lower() for r in records]

    preds = []
    for i in tqdm(range(0, len(prompts), args.batch_size), desc="Evaluating"):
        batch_prompts = prompts[i : i + args.batch_size]
        enc = tokenizer(
            batch_prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        ).to(model.device)
        with torch.no_grad():
            out = model.generate(
                **enc,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )
        for j, out_ids in enumerate(out):
            in_len = enc["input_ids"].shape[1]
            gen = tokenizer.decode(out_ids[in_len:], skip_special_tokens=True)
            preds.append(parse_prediction(gen))

    correct = sum(p == l for p, l in zip(preds, labels))
    accuracy = correct / len(labels)

    print(f"\n=== Evaluation Results ===")
    print(f"Total samples : {len(labels)}")
    print(f"Correct       : {correct}")
    print(f"Accuracy      : {accuracy:.4f} ({accuracy*100:.2f}%)")

    results = {
        "accuracy": accuracy,
        "correct": correct,
        "total": len(labels),
        "model": args.model,
        "adapter": args.adapter,
        "data": args.data,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved → {args.output}")


if __name__ == "__main__":
    main()
