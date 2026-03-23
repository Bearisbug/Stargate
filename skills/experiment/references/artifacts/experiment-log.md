# EXPERIMENT_LOG.md 格式规范

跨 session 的决策叙事文件。**Append-only，不得修改或删除已有记录。**

## 写入时机

| 时机 | 写入内容 |
|------|---------|
| PLAN 完成 | 实验目标、提取的 Claims、输入来源 |
| DESIGN 完成 | 本轮针对哪个 Claim、设计决策、代码改动摘要 |
| EXECUTING 提交 | job_id、git_hash、提交命令 |
| WAITING 出错 | 错误原因、修复方式、retry_count |
| ANALYZING 完成 | Claim 结论、关键指标、下一步决策 |
| 重要的自主调整 | 偏离原设计的决策及理由 |

## 格式

```markdown
## 2024-01-15T10:30:00Z  PLAN

输入：自然语言 idea —— "训练 EBM 区分 human vs LLM 生成的 rubric"

提取 Claims：
- Claim 1：数据管道正确，训练对覆盖全量指令（AUROC > random）
- Claim 2：最优 EBM 配置 val AUROC ≥ 0.72
- Claim 3：Prometheus 跨域泛化 AUROC ≥ 0.70

---

## 2024-01-15T11:00:00Z  DESIGN  [Claim 1]

设计：用 Qwen3-4B 生成 5 种 prompt 变体作为 style negatives，
      data_prep.py 加 --hard-negatives 生成跨 instruction 负样本。
代码改动：gen_llm_rubrics.py 切换 chat template，data_prep.py 加 mine_hard_negatives()
commit: abc1234

---

## 2024-01-15T11:15:00Z  EXECUTING  [Claim 1]

提交 job：sbatch code/run_all.sh
job_id: 1255577
git_hash: abc1234

---

## 2024-01-16T09:00:00Z  ANALYZING  [Claim 1]

结论：ANSWERED
- llm_rubrics.jsonl: 5735 条（5 × 1147）
- train_groups.jsonl: 917 groups
- hard_negatives: 1082 条
下一步：继续 Claim 2（模型训练）

---
```

## 规则

- 每条记录以 `## <ISO 时间>  <阶段>` 开头
- 记录之间用 `---` 分隔
- 只追加，不修改历史记录
- 不记录冗余信息（不复制粘贴代码，不重复 TRACKER 已有的状态）
- 重点记录**决策理由**，而不是操作步骤
