# Stargate — TODO & 技术债

## P1 — 阻塞性（skill 用到时会卡住）

- [x] `references/servers/` — 补全各平台连接指南（slurm / autodl / cloud_gpu / lab_server / bastion / kubernetes / connection / intranet）
- [x] `references/envs/` — 补全环境指南（docker / conda / singularity / gpu）
- [x] `references/artifacts/env-handle.md` — env_handle.json 格式规范
- [x] `references/artifacts/experiment-log.md` — LOG.md 格式规范
- [x] `references/artifacts/rounds.md` — rounds/<run_id>.json 格式规范
- [x] `references/code.md` — 实验代码编写规范
- [x] ANALYZING 内联进 SKILL.md（不再需要 references/phases/analyzing.md）
- [x] REPORTING 内联进 SKILL.md（不再需要 references/phases/reporting.md）
- [x] TRACKER 加 `current_claim_id` 字段

## P2 — Langfuse 集成

- [ ] SKILL.md 加 Langfuse 集成逻辑（各 phase 的 trace.py 调用时机）
- [ ] trace.py 读 `project.json` 的 langfuse 配置（目前只读环境变量）
- [ ] `init` skill — 独立出来，负责 project.json 初始化 + `trace.py init`
- [ ] 代码版本历史规范（commit message 格式、保留最近 N 次记录到 LOG.md）

## P3 — 自建 Tracing 工具（替换 Langfuse 依赖）

> 目标：复现 Langfuse 核心功能，数据完全本地，不依赖外部服务。
> 接口与 tools/trace.py 保持兼容（相同 CLI），只换后端存储。

- [ ] 设计本地存储格式（SQLite 或 JSONL，per-experiment）
- [ ] 实现 session / trace / span / score 的本地记录
- [ ] 实现简单 HTML 报告生成（替代 Langfuse UI）
- [ ] 迁移 trace.py：检测 langfuse 未安装时自动 fallback 到本地后端

## P4 — 未来扩展

- [ ] 并行实验支持（orchestrator + worker agents，多 Claim 并发）
- [ ] dry-run / sanity 模式（不提交 job，只验证配置和路径）
- [ ] TRACKER 损坏恢复程序

---

## 已完成

- [x] 统一 experiment skill（替代原 6 个子 skill）
- [x] 状态机设计（PLAN → ENVIRONMENT → DESIGN → EXECUTING → WAITING → ANALYZING → REPORTING）
- [x] 版本控制集成（提交前强制 commit，git_hash 记录到 TRACKER）
- [x] EBM 实验代码（gen_llm_rubrics / data_prep / train_ebm / eval_ebm）
- [x] Qwen3-4B 下载到服务器
- [x] trace.py 支持从 project.json 读取 Langfuse 配置
- [x] Langfuse Cloud 配置完成（us.cloud.langfuse.com）
- [x] trace.py — Langfuse 薄封装，支持异步 span（跨 session Slurm job 追踪）
