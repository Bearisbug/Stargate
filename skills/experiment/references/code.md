# 实验代码编写规范

> 参考：[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) | [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)

## 文件组织

每个实验按职责分文件：

```
code/
  data_prep.py      # 数据处理、格式转换
  models.py         # 模型定义
  train.py          # 训练入口
  eval.py           # 评估入口
  run.sh            # job script，串联所有步骤
```

入口脚本职责单一，不内嵌模型定义或数据处理逻辑。

---

## 注释规范

> 参考：[Google Python Style Guide §3.8](https://google.github.io/styleguide/pyguide.html)

### 函数 docstring

简单函数用单行：
```python
def load_jsonl(path: str) -> list:
    """Load a JSONL file and return a list of dicts."""
```

复杂函数用多行（Google Style），按 Args / Returns / Raises 顺序：
```python
def train_ebm(model, train_loader, val_loader, lr, epochs):
    """Train an EBM with group-level Bradley-Terry loss.

    Args:
        model: EBM model instance.
        train_loader: DataLoader yielding (pos, negs) groups.
        lr: Learning rate.
        epochs: Number of training epochs.

    Returns:
        Best validation AUROC achieved during training.

    Raises:
        ValueError: If train_loader yields empty groups.
    """
```

### 行内注释

注释解释"为什么"，不解释"做了什么"：
```python
# 使用 bfloat16 避免 H20 上的精度损失问题
model = model.to(torch.bfloat16)

# 不好的注释（描述显而易见的事）：
# model = model.to(torch.bfloat16)  # 转换为 bfloat16
```

注释与代码间至少 2 个空格，`#` 后接一个空格：
```python
x = x + 1  # compensate for border
```

---

## 必要的命令行参数

每个训练/评估入口至少包含：

```python
parser.add_argument("--output-dir", required=True)   # 结果输出路径
parser.add_argument("--resume", action="store_true")  # 断点续跑
```

输出路径不得硬编码。

---

## 日志输出规范

关键指标必须以 `key=value` 格式输出，方便 agent parse：

```python
# 进度（每 N 步输出一次）
print(f"step={step} loss={loss:.4f} lr={lr:.2e}")

# 阶段标记
print(f"===== epoch {epoch} =====")
print(f"[eval] auroc={auroc:.4f} accuracy={acc:.4f}")
print(f"[done] best_val_auroc={best:.4f} saved to {output_dir}")
```

---

## 输出文件

每次运行写入 `<output-dir>/`：

```
<output-dir>/
  config.json       # 本次运行的所有超参数
  metrics.json      # 最终指标（ANALYZING 阶段读取）
  checkpoint_*.pt   # 模型权重
```

`metrics.json` 最小格式：
```json
{
  "val_auroc": 0.81,
  "best_epoch": 12
}
```

---

## 断点续跑

```python
if args.resume and Path(f"{args.output_dir}/checkpoint_last.pt").exists():
    ckpt = torch.load(f"{args.output_dir}/checkpoint_last.pt")
    model.load_state_dict(ckpt["model"])
    start_epoch = ckpt["epoch"] + 1
    print(f"[resume] from epoch {start_epoch}")
```

---

## Commit Message 规范

> 参考：[Conventional Commits v1.0.0](https://www.conventionalcommits.org/en/v1.0.0/)

格式：`<type>[optional scope]: <description>`

实验层常用 type：

| type | 含义 |
|------|------|
| `exp` | 实验相关改动（新增/修改实验代码） |
| `fix` | 修复 bug |
| `feat` | 新功能 |
| `refactor` | 重构，不改变行为 |
| `docs` | 文档修改 |

实验代码每个 Claim 迭代对应一次 commit：
```
exp(claim-2): add adaptive BT loss
exp(claim-1): fix data leak in train/val split
fix: correct output path in run.sh
```
