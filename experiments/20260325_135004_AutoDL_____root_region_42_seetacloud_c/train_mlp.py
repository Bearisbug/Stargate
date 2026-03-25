"""
Claim-1: 两层 MLP 在随机生成的二分类数据上正常训练 100 steps
- train_loss 持续下降（最终 < 初始）
- accuracy > 50%
- 每 step 均记录 train_loss 和 accuracy
"""
import argparse
import json
import time
import torch
import torch.nn as nn


def main(num_steps: int, out_json: str):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] device={device}", flush=True)

    # --- data ---
    torch.manual_seed(42)
    n_samples, n_features = 256, 20
    X = torch.randn(n_samples, n_features, device=device)
    # linearly separable: label = sign(sum of first 5 features)
    y = (X[:, :5].sum(dim=1) > 0).long()

    # --- model: input -> 64 -> 2 ---
    model = nn.Sequential(
        nn.Linear(n_features, 64),
        nn.ReLU(),
        nn.Linear(64, 2),
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    records = []
    t0 = time.time()
    for step in range(1, num_steps + 1):
        # random mini-batch of 64
        idx = torch.randint(0, n_samples, (64,))
        xb, yb = X[idx], y[idx]

        logits = model(xb)
        loss = criterion(logits, yb)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        with torch.no_grad():
            preds = logits.argmax(dim=1)
            acc = (preds == yb).float().mean().item()

        records.append({"step": step, "train_loss": round(loss.item(), 6), "accuracy": round(acc, 4)})
        if step % 10 == 0 or step == 1:
            print(f"step={step:3d}  loss={loss.item():.4f}  acc={acc:.4f}", flush=True)

    elapsed = time.time() - t0
    result = {
        "claim_id": 1,
        "num_steps": num_steps,
        "elapsed_sec": round(elapsed, 2),
        "initial_loss": records[0]["train_loss"],
        "final_loss": records[-1]["train_loss"],
        "final_accuracy": records[-1]["accuracy"],
        "records": records,
    }

    # criteria checks
    result["pass_loss_decrease"] = result["final_loss"] < result["initial_loss"]
    result["pass_accuracy"] = result["final_accuracy"] > 0.50
    result["pass_all"] = result["pass_loss_decrease"] and result["pass_accuracy"]

    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n[RESULT] initial_loss={result['initial_loss']}  final_loss={result['final_loss']}  final_acc={result['final_accuracy']}")
    print(f"[RESULT] pass_loss_decrease={result['pass_loss_decrease']}  pass_accuracy={result['pass_accuracy']}  pass_all={result['pass_all']}")
    print(f"[RESULT] saved to {out_json}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--out", type=str, default="/root/autodl-tmp/claim1_result.json")
    args = parser.parse_args()
    main(args.steps, args.out)
