---
name: refine
description: 实验完成后自动触发。召唤独立评估 agent 交叉评估本轮执行质量，提取研究 insight 和 agent 经验，分类写入持久化知识库。
---

# 实验复盘与经验提炼

由 `experiment` skill 的 REPORTING 阶段完成后自动触发，也可手动调用。

---

## Step 1：收集 Artifacts

读取本轮实验的全部记录：

- `EXPERIMENT_TRACKER.md` — 最终状态和 Claim 结论
- `EXPERIMENT_LOG.md` — 完整决策叙事
- `rounds/*.json` — 每轮数字结果
- `reports/report.md` — 最终报告

---

## Step 2：召唤评估 agent

将上述 artifacts 交给独立评估 agent，要求其从三个维度评估本轮实验：

**执行质量**
- 指令遵循情况（有无静默替换、有无误解约束）
- 错误处理方式（是 bug 修复还是绕过问题）
- 工具选型是否合理

**实验质量**
- Claim 设计是否清晰可验证
- 方法选择是否合理
- 有无数据泄露或明显 bias

**Insight 可信度**
- 结论是否有足够实验证据支撑
- 有无过度泛化

评估 agent 返回结构化评估结果，包含各维度评分（好 / 一般 / 差）和具体说明。

→ 评估 agent 提示词及结果处理规则：`references/eval-agent.md`

---

## Step 3：向用户展示摘要

用一段简短摘要（不超过 10 行）告知用户：

- 本轮执行的主要问题（如有）
- 值得记录的 insight（如有）
- 评估 agent 的整体判断

**用户有任何回复即视为确认，有异议时直接说明。** 不等待显式"确认"指令。

---

## Step 4：提取研究 insight

根据评估置信度，将值得记录的科研发现写入 `knowledge/research/`：

```markdown
---
topic: <关键词>
experiment: <项目名 + claim_id>
confidence: high | medium | low
---

<一句话核心发现>

**证据**：<哪个实验、哪个指标>
**适用范围**：<什么任务/场景下可能适用>
**待验证**：<需要进一步实验才能确认的部分>
```

置信度标准：
- `high`：多次实验复现，有消融对比
- `medium`：单次实验，结果清晰
- `low`：间接证据，或仅作为假设记录

---

## Step 5：提取 agent 经验

分两类写入：

**环境级**（项目/服务器专属）→ `knowledge/env/<user@host>.md`

追加事实性记录，不做结构化：
```markdown
# <user@host>
- <发现的限制、字段名、路径约定等>
- <对应解决方案>
```

**原则级**（跨项目通用）→ `memory/` 目录

按现有 memory 格式写入或更新，重点记录：
- 执行层面的行为改进（如指令遵循、工具选型）
- 本轮评估 agent 指出的执行问题

低置信度的经验或评估 agent 标记为"有争议"的内容，不写入 memory。

---

## 输出文件

```
knowledge/
  research/
    <topic>_<date>.md     # 研究 insight
  env/
    <user@host>.md        # 环境经验
memory/
  <updated>.md            # 更新的通用原则（如有）
```

→ knowledge/ 目录和文件格式规范：`references/knowledge-format.md`
