# knowledge/ 目录规范

refine skill 写入，供未来实验和调研层消费。

---

## 目录结构

```
knowledge/
  KNOWLEDGE.md          # 索引，同 MEMORY.md 的角色
  research/             # 科研 insight
    <topic>_<date>.md
  env/                  # 服务器/环境经验
    <user@host>.md
```

---

## KNOWLEDGE.md 索引格式

```markdown
# Knowledge Index

## Research Insights
- [hard_negatives_2026-03-24.md](research/hard_negatives_2026-03-24.md) — EBM 任务中 hard negatives 对 AUROC 的影响

## Environment
- [sc100123@174.0.250.88.md](env/sc100123@174.0.250.88.md) — 服务器字段约定、限制
```

---

## research/ 文件格式

```markdown
---
topic: <关键词>
experiment: <project_name>/<claim_id>
date: <ISO 日期>
confidence: high | medium | low
---

<一句话核心发现>

**证据**：<实验名、指标值>
**适用范围**：<什么任务/场景>
**待验证**：<尚需进一步实验确认的部分，无则填"无">
```

置信度标准：
- `high`：多次实验复现，有消融对比
- `medium`：单次实验，结果清晰，方法合理
- `low`：间接证据，或作为待验证假设记录

---

## env/ 文件格式

追加式，不做严格结构，直接记录事实：

```markdown
# <user@host>

更新时间：<ISO 日期>

## 已知限制
- <限制描述及对应解决方案>

## 路径约定
- <项目路径、数据路径等>

## 环境配置
- <conda env、module load 命令等>
```
