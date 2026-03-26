# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Stargate — 全自动科研 Agent 系统

Stargate 是一个三层科研自动化系统：**调研层 → 实验层 → 论文层**。
当前 repo 包含实验层的所有 skill 和工具。

---
## 首次使用：初始化项目配置

  **`project.json` 不存在时，在做任何实验前先完成初始化。**

  运行 `init` skill 收集以下信息，写入 `project.json`：

  | 信息 | 必填 | 说明 |
  |------|:----:|------|
  | `project_name` | ✅ | 项目名，用于报告标题和 Langfuse session |
  | `servers.default` | ✅ | 服务器地址，`user@host` 格式 |
  | `work_dir` | ✅ | 远端实验根目录 |
  | `experiment.platform` | — | slurm / autodl / cloud / lab / local |
  | `experiment.runtime` | — | conda / docker / singularity |
  | `experiment.offline` | — | 是否离线环境 |
  | `model_base_dir` | — | 预训练模型根路径 |
  | `data_base_dir` | — | 数据集根路径 |
  | `feishu.enabled` | — | 是否启用飞书推送 |
  | `langfuse.enabled` | — | 是否启用 tracing，默认 false |

  可选字段跳过时填 `null`，后续用到时再补充，不打断当前任务。

  ### project.json 模板

  ```json
  {
    "project_name": "<填写>",
    "servers": { "default": "user@host" },
    "work_dir": "/workspace",
    "model_base_dir": null,
    "data_base_dir": null,
    "experiment": {
      "platform": "<slurm | autodl | cloud | lab | local>",
      "runtime": "<conda | docker | singularity>",
      "offline": false
    },
    "feishu": {
      "enabled": false,
      "app_id": "",
      "app_secret": "",
      "chat_id": ""
    },
    "langfuse": {
      "enabled": false,
      "host": "https://cloud.langfuse.com",
      "public_key": "",
      "secret_key": ""
    }
  }
  ```

  ### 执行中自动更新 project.json

  | 时机 | 更新内容 |
  |------|---------|
  | ENVIRONMENT 阶段完成 | 补全 `servers.<name>` 的探测结果（GPU 型号、分区等） |
  | 镜像拉取成功 | 更新 `image_registry` 为实际地址 |
  | Langfuse 首次连接成功 | 将 `langfuse.enabled` 置为 `true` |

---
## 实验层 Skill 地图

| Skill | 何时使用 |
|-------|---------|
| `init` | 首次使用，写入 `project.json` |
| `experiment` | 实验执行唯一入口，覆盖完整生命周期（PLAN → ENVIRONMENT → DESIGN → EXECUTING → WAITING → ANALYZING → REPORTING） |
| `refine` | `experiment` REPORTING 完成后自动触发；也可手动调用，召唤独立评估 agent 提炼研究 insight 和 agent 经验 |

> `experiment` skill 已取代原 `experiment-plan / experiment-environment / experiment-flow / experiment-errors / experiment-code / experiment-report` 等全部子 skill。

### experiment skill 状态机

`EXPERIMENT_TRACKER.md` 的 `phase` 字段驱动执行：

```
PLAN → ENVIRONMENT → DESIGN → EXECUTING → WAITING → ANALYZING → REPORTING → DONE
```

每次进入 `experiment` skill，第一步必须读 `EXPERIMENT_TRACKER.md`，按当前 `phase` 跳转到对应阶段。

---

## 常见场景入口

```
有一个 idea，想跑实验：
  → init（若无 project.json）
  → experiment（从 PLAN 开始，全自动运行到 DONE）

有一篇论文，想复现实验：
  → experiment（输入论文 URL，PLAN 阶段自动解析 Claims）

跨 session 恢复实验：
  → experiment（读 EXPERIMENT_TRACKER.md，按 phase 续跑）

只想看实验报告：
  → 直接读 reports/report.md 和 rounds/insights/claim_N.md
```

---

## 文件约定

| 文件 | 产出方 | 消费方 |
|------|-------|-------|
| `project.json` | init / 用户 | experiment skill |
| `env_handle.json` | experiment (ENVIRONMENT) | experiment (DESIGN, EXECUTING) |
| `EXPERIMENT_TRACKER.md` | experiment | experiment（跨 session 恢复依据） |
| `EXPERIMENT_LOG.md` | experiment | refine（append-only，不得修改） |
| `rounds/<run_id>.json` | experiment (ANALYZING) | refine, experiment-report |
| `rounds/insights/claim_N.md` | experiment (REPORTING) | 论文层, 调研层 |
| `reports/report.md` | experiment (REPORTING) | 论文层, 调研层 |
| `knowledge/research/<topic>.md` | refine | 调研层 |
| `knowledge/env/<user@host>.md` | refine | experiment（环境经验） |
| `trace-state.json` | tools/trace.py | tools/trace.py |

---

## 工具

| 工具 | 用途 |
|------|------|
| `tools/trace.py` | Langfuse 可观测性，跨 session 追踪 |
| `tools/viz.py` | 解析训练日志，生成 HTML 可视化 |
| `tools/feishu.py` | 飞书消息推送 CLI，供 skill 在关键节点调用 |
| `tools/feishu_daemon.py` | 飞书控制守护进程，接收指令、触发实验、推送报告 |

tracing 完全可选；`trace-state.json` 不存在时所有 skill 正常工作。
飞书完全可选；`feishu.enabled: false` 时 `tools/feishu.py` 静默退出，不影响实验流程。

---

## 层间接口

**调研层 → 实验层**：以自然语言 idea 或结构化调研报告传入，由 `experiment` skill 的 PLAN 阶段转换为 Claims。

**实验层 → 论文层 / 调研层**：`reports/report.md`（结构化实验报告）+ `rounds/insights/claim_N.md`（per-Claim 分析）+ `knowledge/research/`（跨实验 insight）。

---

## Skill 引用路径

所有 skill 在 `skills/` 目录下，各 skill 的 `SKILL.md` 为入口，`references/` 为详细说明。

- `skills/experiment/references/servers/` — 各平台连接规范（autodl, slurm, cloud_gpu 等）
- `skills/experiment/references/envs/` — 执行环境规范（conda, docker, singularity, gpu）
- `skills/experiment/references/methods/` — 任务类型最佳实践（sft, rft, inference 等）
- `skills/experiment/references/artifacts/` — 各 artifact 格式规范
