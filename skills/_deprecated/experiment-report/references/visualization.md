# 可视化 Dashboard

使用 `tools/viz/viz.py` 生成自包含 HTML dashboard，无需外部服务。

## 调用方式

```bash
# 基本用法（在实验目录下执行）
python <stargate_root>/tools/viz/viz.py

# 指定路径
python <stargate_root>/tools/viz/viz.py \
  --runs ./rounds \
  --output ./reports/dashboard.html

# 生成后直接在浏览器打开
python <stargate_root>/tools/viz/viz.py --open
```

## 前提条件

`rounds/<run_id>.json` 中需要有 `log_path` 字段，指向训练日志文件（本地路径）。
远端执行时，agent 需先将日志从服务器拉取到本地：

```bash
# remote-docker / remote-singularity
rsync -az <host>:<remote_log_path> ./rounds/logs/<run_id>.log
# 然后在 rounds/<run_id>.json 中写入 log_path: "rounds/logs/<run_id>.log"
```

## 日志格式支持

viz.py 默认识别以下格式（大小写不敏感）：

```
loss=0.342   val_loss=0.419   acc=0.87   val_acc=0.91
reward: 2.14   lr=1e-4   step=100   epoch=3
```

日志格式不匹配时，用 `--patterns` 追加自定义正则：

```bash
python viz.py --patterns "train_loss=train_loss:([\d.]+),eval_acc=eval/acc:([\d.]+)"
```

## 输出

| 文件 | 内容 |
|------|------|
| `reports/dashboard.html` | 自包含 HTML，可直接用浏览器打开或分享 |

Dashboard 包含：
- **Run Summary 表格**：所有 run 的 status、命令摘要、manager_judgement、耗时
- **Training Curves**：所有有日志的 run 的 metric 折线图，按 run 着色（绿=passed，红=failed，橙=blocked）

## 在 report skill 中的调用时机

实验整体结束（done / escalate）后执行：

```bash
python <stargate_root>/tools/viz/viz.py --runs ./rounds --output ./reports/dashboard.html
```

结果路径写入 `reports/report.md` 末尾：

```markdown
## 可视化
Dashboard: `reports/dashboard.html`
```
