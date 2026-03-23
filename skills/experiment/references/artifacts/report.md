# reports/report.md 格式规范

REPORTING 阶段生成，面向用户和论文层。必须能独立阅读，不依赖其他文件。

---

## 完整格式

```markdown
# 实验报告：<project_name>

**生成时间**：<ISO 时间戳>
**实验目录**：<work_dir>

---

## 背景与目标

<一段话说明这组实验要验证什么，为什么做。>

---

## Claims 总览

| Claim | 描述 | 结论 | 关键指标 |
|-------|------|------|---------|
| 1 | <描述> | ANSWERED ✅ | val_auroc=0.81 |
| 2 | <描述> | FAILED ❌ | val_auroc=0.61（目标≥0.72）|

---

## 方法

### 数据
<数据来源、规模、处理方式>

### 模型与框架
<使用的模型、训练框架、关键超参>

### 评估方式
<指标定义、测试集构成>

---

## 详细结论

### Claim 1：<描述>

**结论**：ANSWERED

**方法**：<本轮用了什么方案>

**结果**：
- val_auroc = 0.81（目标 ≥ 0.72）✅
- best_epoch = 12

**分析**：<为什么达标，有什么值得注意的现象>

---

### Claim 2：<描述>

**结论**：FAILED

**方法**：<本轮用了什么方案>

**结果**：
- val_auroc = 0.61（目标 ≥ 0.72）❌

**失败分析**：<为什么没达标，是方法问题还是数据问题，下一步可以怎么做>

---

## 执行过程

每个阶段做了什么、得到了什么，让用户无需查日志就能还原整个实验过程。

| 阶段 | 做了什么 | 得到了什么 |
|------|---------|----------|
| PLAN | 从 <输入来源> 提取 2 个 Claim | TRACKER + EXPERIMENT_LOG 初始化 |
| ENVIRONMENT | 连接 <host>，确认 Conda 环境 lf，GPU H20×1 可用 | env_handle.json |
| DESIGN [Claim 1] | 设计数据管道，生成 5735 条 Qwen3-4B rubrics | data/llm_rubrics.jsonl |
| EXECUTING [Claim 1] | 提交 Slurm job 1255577，12h 时间限制 | job_id 记录到 TRACKER |
| WAITING [Claim 1] | 监控训练，epoch 12 val_auroc 最高 | 训练日志 |
| ANALYZING [Claim 1] | AUROC=0.81 达标，标记 ANSWERED | rounds/claim1-1.json |
| REPORTING | 汇总所有结果，生成报告 | reports/report.md |

---

## 可复现性

| 字段 | 值 |
|------|---|
| Git commit | `abc1234` |
| Random seed | 42 |
| Python 环境 | `<pip freeze 输出路径或关键包版本>` |
| 数据 checksum | `<md5sum data/train_groups.jsonl>` |

---

## 附录：各轮运行记录

| run_id | Claim | git_hash | val_auroc | 备注 |
|--------|-------|---------|-----------|------|
| claim1-1 | 1 | abc1234 | 0.81 | |
| claim2-1 | 2 | def5678 | 0.61 | 首次 FAILED |
```

---

## 写入规则

- 从 `rounds/*.json` 读取所有数字，不手动填写指标
- 可复现性字段必须填写，git_hash 从 `rounds/*.json` 读取，seed 从代码或 config.json 读取
- FAILED 的 Claim 必须有失败分析，不能只写"未达标"
- 整体报告不超过 500 行，保持可读性
