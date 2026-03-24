#!/usr/bin/env python3
"""
SST-2 数据集转换：HuggingFace → LLaMA-Factory Alpaca 格式
输出：data/sst2_train.json, data/sst2_val.json
"""
import json
import os
from datasets import load_dataset

LABEL_MAP = {0: "negative", 1: "positive"}
INSTRUCTION = "Classify the sentiment of the following movie review as positive or negative."


def convert_split(split_data, out_path: str) -> None:
    records = []
    for item in split_data:
        label = LABEL_MAP[item["label"]]
        records.append({
            "instruction": INSTRUCTION,
            "input": item["sentence"],
            "output": label,
        })
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  saved {len(records)} records → {out_path}")


def main():
    print("Loading SST-2 from HuggingFace (glue/sst2)...")
    ds = load_dataset("glue", "sst2")

    print("Converting train split...")
    convert_split(ds["train"], "data/sst2_train.json")

    print("Converting validation split...")
    convert_split(ds["validation"], "data/sst2_val.json")

    print("Done.")


if __name__ == "__main__":
    main()
