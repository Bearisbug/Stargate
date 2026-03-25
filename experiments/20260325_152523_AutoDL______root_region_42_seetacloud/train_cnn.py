"""
Claim-1: 3层 CNN 在 MNIST 上训练 5 个 epoch
- 每 epoch 记录 train_loss 和 test_accuracy
- 最终 test_accuracy > 90%
"""
import argparse
import json
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms


class CNN3Layer(nn.Module):
    """3-layer CNN for MNIST classification."""
    def __init__(self):
        super().__init__()
        # Layer 1: 1 -> 32 channels, 3x3, pad=1  -> 28x28; MaxPool -> 14x14
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )
        # Layer 2: 32 -> 64 channels, 3x3, pad=1 -> 14x14; MaxPool -> 7x7
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )
        # Layer 3: 64 -> 128 channels, 3x3, pad=1 -> 7x7
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        # Classifier: 128 * 7 * 7 -> 256 -> 10
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 7 * 7, 256),
            nn.ReLU(),
            nn.Linear(256, 10),
        )

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.fc(x)
        return x


def train_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0.0
    n_batches = 0
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        logits = model(xb)
        loss = criterion(logits, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        n_batches += 1
    return total_loss / n_batches


def eval_epoch(model, loader, device):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            preds = model(xb).argmax(dim=1)
            correct += (preds == yb).sum().item()
            total += yb.size(0)
    return correct / total


def main(epochs: int, data_dir: str, out_json: str, sanity: bool):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] device={device}  epochs={epochs}  sanity={sanity}", flush=True)

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])

    train_dataset = datasets.MNIST(data_dir, train=True, download=True, transform=transform)
    test_dataset = datasets.MNIST(data_dir, train=False, download=True, transform=transform)

    if sanity:
        # Use 512 train samples and 256 test samples for quick sanity check
        train_dataset = Subset(train_dataset, range(512))
        test_dataset = Subset(test_dataset, range(256))

    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=256, shuffle=False, num_workers=2, pin_memory=True)

    model = CNN3Layer().to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    records = []
    t0 = time.time()

    for epoch in range(1, epochs + 1):
        t_ep = time.time()
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        test_acc = eval_epoch(model, test_loader, device)
        elapsed_ep = time.time() - t_ep
        records.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "test_accuracy": round(test_acc, 4),
        })
        print(f"epoch={epoch}/{epochs}  train_loss={train_loss:.4f}  test_acc={test_acc:.4f}  ({elapsed_ep:.1f}s)", flush=True)

    elapsed = time.time() - t0
    result = {
        "claim_id": 1,
        "epochs": epochs,
        "sanity": sanity,
        "elapsed_sec": round(elapsed, 2),
        "records": records,
        "final_train_loss": records[-1]["train_loss"],
        "final_test_accuracy": records[-1]["test_accuracy"],
        "pass_accuracy": records[-1]["test_accuracy"] > 0.90,
        "pass_all_epochs_recorded": len(records) == epochs,
    }
    result["pass_all"] = result["pass_accuracy"] and result["pass_all_epochs_recorded"]

    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n[RESULT] final_test_accuracy={result['final_test_accuracy']}  pass_accuracy={result['pass_accuracy']}", flush=True)
    print(f"[RESULT] pass_all={result['pass_all']}  saved to {out_json}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--data_dir", type=str, default="/root/autodl-tmp/data")
    parser.add_argument("--out", type=str, default="/root/autodl-tmp/claim1_result.json")
    parser.add_argument("--sanity", action="store_true", help="Run with minimal data for sanity check")
    args = parser.parse_args()
    main(args.epochs, args.data_dir, args.out, args.sanity)
