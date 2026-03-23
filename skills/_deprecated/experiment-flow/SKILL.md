---
name: experiment-flow
description: 执行 ML 实验流程：单次 run 执行、多 run 编排、结果验证。当用户需要跑实验、执行实验计划、验证实验结果时使用。
---

# 实验执行流程

## 获取实验计划

按优先级读取：

1. `EXPERIMENT_TRACKER.md` 存在 → 直接执行（已有计划）
2. `EXPERIMENT_PLAN.md` 存在 → 转换为 tracker，再执行
   → 见 [references/preparing-experiment.md](references/preparing-experiment.md)
3. 以上均不存在 → **从对话中提取**：

   从用户描述中识别：
   - **Claim**：要验证的假设（"验证 X 能达到 Y"、"证明 A 优于 B"）；没有明确 claim 时，将整个任务作为一个 claim
   - **命令**：用户提供的脚本路径、入口文件、参数；不完整时询问缺失部分
   - **成功条件**：用户提到的指标和阈值；未提及时询问，或使用"任务完成且无报错"作为默认
   - **GPU budget**：用户提及时使用；未提及时按任务规模估算并告知用户

   提取后生成 `EXPERIMENT_PLAN.md` 和 `EXPERIMENT_TRACKER.md`，展示给用户——**用户有任何回复即视为确认，立即开始执行循环，不再等待显式"开始"指令**。用户若要修改计划，会在回复中明确说明。

## 单次 run

1. 从 `EXPERIMENT_TRACKER.md` 读取 pending run 的命令和成功条件
   → 格式见 [references/tracker-format.md](references/tracker-format.md)
2. 通过 `env_handle.json` 执行命令
   → 执行方式见 experiment-infrastructure skill
3. 收集 artifacts，验证结果：
   - 有验收命令 → 执行，非零 exit code 标记 `failed`
   - 无验收命令 → 读 artifacts，对照自然语言成功条件判断
4. 写入 `rounds/<run_id>.json`，更新 tracker

输出格式：
```json
{
  "run_id": "1.1",
  "status": "passed | failed | blocked",
  "command": "...",
  "success_criteria": "...",
  "manager_judgement": "...",
  "errors": [],
  "started_at": "ISO8601",
  "finished_at": "ISO8601"
}
```

## 多 run 编排

循环执行，由 Manager 判断整体 done / retry / escalate
→ 见 [references/running-loop.md](references/running-loop.md)

Manager 自动重试失败的 run（默认最多 3 次），超限后请求 human in loop
→ 见 [references/manager-retry.md](references/manager-retry.md)

长时间任务（Slurm job、远程训练）的轮询等待
→ 见 [references/monitor.md](references/monitor.md)

遇到执行错误 → 见 experiment-errors skill

## Tracing（可选）

`trace-state.json` 存在时记录执行轨迹 → 见 [tools/trace-guide.md](../../tools/trace-guide.md)
新 context 进入时先执行 `python tools/trace.py conversation --agent claude-code`。
