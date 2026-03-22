# 通用 DL 训练规范

适用于图像分类、目标检测、序列标注等非语言模型任务。

## 标准命令行接口

```bash
python train.py \
  --model    resnet18 \
  --dataset  /data/cifar10 \
  --output   /workspace/runs/exp1 \
  --epochs   100 \
  --batch-size 128 \
  --lr       0.1 \
  --seed     42
```

## 日志输出格式（供 viz.py 解析）

```
epoch=1  step=100  loss=2.31  lr=0.1
epoch=1  step=200  loss=2.05  lr=0.1
epoch=1  val_loss=1.98  val_acc=0.423  ← epoch 结束时输出验证集指标
```

## checkpoint 规范

```python
# 每 N epoch 保存一次
torch.save({
    "epoch": epoch,
    "model_state_dict": model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
    "val_acc": val_acc,
}, f"{output_dir}/checkpoint_epoch{epoch}.pt")

# 同时保存 best model
if val_acc > best_acc:
    torch.save(model.state_dict(), f"{output_dir}/best_model.pt")
```

## eval.py 规范

```bash
# 独立于训练可运行
python eval.py --checkpoint /workspace/runs/exp1/best_model.pt --dataset /data/cifar10/test
# 输出：acc=0.934  (单行，供验收命令 grep)
```

## 镜像

基础镜像：`base-pytorch-cu121`（`<PLACEHOLDER: 镜像仓库地址>/base-pytorch-cu121`）

依赖：`torch>=2.1`, `torchvision>=0.16`
