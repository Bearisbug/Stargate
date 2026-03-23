# Stargate — 全自动科研 Agent 系统

Stargate 是一个三层科研自动化系统：**调研层 → 实验层 → 论文层**。
当前 repo 包含实验层的所有 skill 和工具。

---
## 首次使用：初始化项目配置

  **`project.json` 不存在时，在做任何实验前先完成初始化。**

  收集以下信息，写入 `project.json`：

  | 信息 | 必填 | 说明 |
  |------|:----:|------|
  | `project_name` | ✅ | 项目名，用于报告标题和 Langfuse session |
  | `servers.default` | ✅ | 服务器地址，`user@host` 格式 |
  | `work_dir` | ✅ | 远端实验根目录 |
  | `model_base_dir` | — | 预训练模型根路径 |
  | `data_base_dir` | — | 数据集根路径 |
  | `image_registry` | — | 镜像仓库前缀 |
  | `langfuse.enabled` | — | 是否启用 tracing，默认 true |

  可选字段跳过时填 `null`，后续用到时再补充，不打断当前任务。

  ### project.json 模板

  ```json
  {
    "project_name": "<填写>",
    "servers": { "default": "user@host" },
    "work_dir": "/workspace",
    "model_base_dir": null,
    "data_base_dir": null,
    "image_registry": null,
    "langfuse": {
      "enabled": false,
      "host": "http://localhost:3000",
      "public_key": "",
      "secret_key": ""
    }
  }
  ```

  ### 执行中自动更新 project.json

  | 时机 | 更新内容 |
  |------|---------|
  | experiment-environment 完成 | 补全 `servers.<name>` 的探测结果 |
  | 镜像拉取成功 | 更新 `image_registry` 为实际地址 |
  | Langfuse 首次连接成功 | 将 `langfuse.enabled` 置为 `true` |

  ### Langfuse 部署选项

  | 选项 | 方式 |
  |------|------|
  | Cloud（快速开始） | cloud.langfuse.com 注册，复制 API key |
  | 自部署（数据不出本地） | `docker compose up`（官方 compose 文件）|

  ```bash
  export LANGFUSE_PUBLIC_KEY=pk-lf-xxx
  export LANGFUSE_SECRET_KEY=sk-lf-xxx
  export LANGFUSE_HOST=https://cloud.langfuse.com
  ```
  
## 实验层 Skill 地图

### 规划类（输出 EXPERIMENT_PLAN.md）

| Skill | 何时使用 |
|-------|---------|
| `experiment-plan` | 有 idea、论文、或已有结果，需要生成/更新实验计划 |
| `experiment-code` | 有计划，需要生成/规范实验代码框架 |

### 环境类（输出 env_handle.json）

| Skill | 何时使用 |
|-------|---------|
| `experiment-environment` | 第一次连接服务器，或环境失效需要重建 |
| `experiment-infrastructure` | 在已有环境中执行单条命令、收集 artifacts |

### 执行类（输出 rounds/）

| Skill | 何时使用 |
|-------|---------|
| `experiment-flow` | 有 TRACKER，跑实验循环，由 Manager 编排 |
| `experiment-errors` | 执行出错时的分类处理和自动修复 |

### 报告类（输出 reports/）

| Skill | 何时使用 |
|-------|---------|
| `experiment-report` | Claim 完成后记录 insight；实验结束后生成报告 |

---

## 常见场景入口

```
有一个 idea，想跑实验：
  → experiment-plan（idea → EXPERIMENT_PLAN.md）
  → experiment-environment（初始化环境）
  → experiment-flow（跑实验循环）

有一篇论文，想复现实验：
  → experiment-plan（paper → EXPERIMENT_PLAN.md）
  → experiment-code（生成代码框架）
  → experiment-environment → experiment-flow

有已有结果，想进一步实验：
  → experiment-plan（results → next EXPERIMENT_PLAN.md）
  → experiment-flow（继续跑）

只想在服务器上跑一个命令：
  → experiment-environment（如无 env_handle.json）
  → experiment-infrastructure（直接执行命令）

只想看实验报告：
  → experiment-report（直接读 rounds/，无需重跑）
```

---

## 文件约定

| 文件 | 产出方 | 消费方 |
|------|-------|-------|
| `env_config.json` | 用户 / experiment-environment | experiment-environment |
| `env_handle.json` | experiment-environment | experiment-infrastructure, experiment-flow |
| `EXPERIMENT_PLAN.md` | experiment-plan / 用户 | experiment-flow |
| `EXPERIMENT_TRACKER.md` | experiment-flow | experiment-flow, experiment-report |
| `rounds/<run_id>.json` | experiment-flow | experiment-report |
| `rounds/insights/claim_N.md` | experiment-report | 论文层, 调研层 |
| `reports/report.md` | experiment-report | 论文层, 调研层 |
| `trace-state.json` | tools/trace.py | tools/trace.py |

---

## 工具

| 工具 | 用途 |
|------|------|
| `tools/trace.py` | Langfuse 可观测性，跨 session 追踪 |
| `tools/viz.py` | 解析训练日志，生成 HTML 可视化 |

tracing 完全可选；`trace-state.json` 不存在时所有 skill 正常工作。

---

## 层间接口

**调研层 → 实验层**：以自然语言 idea 或结构化调研报告传入，由 `experiment-plan` 转换为 `EXPERIMENT_PLAN.md`。

**实验层 → 论文层 / 调研层**：`reports/report.md`（结构化实验报告）+ `rounds/insights/claim_N.md`（per-Claim 分析）。论文层直接消费 report；调研层用 insight 决定是否调整研究方向。

**镜像托管**：`<PLACEHOLDER: 镜像仓库地址>`（base-pytorch-cu121 等基础镜像）

---

## Skill 引用路径

所有 skill 在 `skills/` 目录下，各 skill 的 `SKILL.md` 为入口，`references/` 为详细说明。
