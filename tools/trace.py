#!/usr/bin/env python3
"""
Stargate trace CLI — Langfuse 的薄封装。

层级设计：
  Task ID      = Langfuse session_id，整个实验任务，永久不变
  Conversation = Langfuse trace_id，每次 agent session 新建
  Span         = skill 调用，两种模式：
    · 普通 span：在当前对话内开/关（span-start / span-end）
    · 延迟 span：跨对话的异步操作（span-defer / span-end）
                 span-defer 只记录开始时间到 trace-state.json，不调用 Langfuse
                 span-end   完成时用历史时间戳一次性创建完整 span

用法：
  python tools/trace.py init          --experiment <name>
  python tools/trace.py conversation  [--agent <name>]
  python tools/trace.py span-start    --name <skill> [--run-id <id>] [--input <json>]
  python tools/trace.py span-defer    --name <skill> [--run-id <id>] [--input <json>]
  python tools/trace.py span-end      --name <skill> [--run-id <id>] [--output <json>] [--status ok|error]
  python tools/trace.py event         --name <event>  [--data <json>]
  python tools/trace.py score         --name <metric> --value <float> [--comment <str>]

环境变量：LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_HOST（默认 http://localhost:3000）
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = "trace-state.json"


# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    p = Path(STATE_FILE)
    return json.loads(p.read_text()) if p.exists() else {}


def save_state(state: dict):
    Path(STATE_FILE).write_text(json.dumps(state, indent=2, ensure_ascii=False))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_dt() -> datetime:
    return datetime.now(timezone.utc)


# ── Langfuse client ───────────────────────────────────────────────────────────

def load_langfuse_config() -> dict:
    """从 project.json 读取 langfuse 配置，环境变量优先覆盖。"""
    cfg = {}
    p = Path("project.json")
    if p.exists():
        try:
            cfg = json.loads(p.read_text()).get("langfuse", {})
        except Exception:
            pass
    return {
        "host":       os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL") or cfg.get("host", "http://localhost:3000"),
        "public_key": os.environ.get("LANGFUSE_PUBLIC_KEY") or cfg.get("public_key", ""),
        "secret_key": os.environ.get("LANGFUSE_SECRET_KEY") or cfg.get("secret_key", ""),
    }


def get_client():
    try:
        from langfuse import Langfuse
    except ImportError:
        print("[trace] langfuse not installed: pip install langfuse", file=sys.stderr)
        sys.exit(1)
    cfg = load_langfuse_config()
    if not cfg["public_key"] or not cfg["secret_key"]:
        print("[trace] Langfuse keys not set (env vars or project.json)", file=sys.stderr)
        sys.exit(1)
    return Langfuse(public_key=cfg["public_key"], secret_key=cfg["secret_key"], host=cfg["host"])


def current_trace_id() -> str:
    state = load_state()
    tid = state.get("current_trace_id")
    if not tid:
        print("[trace] no active conversation — run 'conversation' first", file=sys.stderr)
        sys.exit(1)
    return tid


def span_key(name: str, run_id: str | None) -> str:
    return f"{name}/{run_id}" if run_id else name


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(args):
    """创建 Task ID，写入 trace-state.json。每个实验只运行一次。"""
    task_id = f"task-{args.experiment}-{uuid.uuid4().hex[:8]}"
    save_state({
        "experiment":       args.experiment,
        "task_id":          task_id,
        "current_trace_id": None,
        "current_agent":    None,
        "spans":            {},   # 当前对话内的活跃 span
        "pending_spans":    {},   # 跨对话的异步延迟 span
        "created_at":       now_iso(),
    })
    print(f"[trace] init  experiment={args.experiment}  task_id={task_id}")


def cmd_conversation(args):
    """新建 Conversation trace，挂在当前 task_id 下。每次 agent session 开始时调用。"""
    state = load_state()
    if not state:
        print("[trace] trace-state.json not found — run 'init' first", file=sys.stderr)
        sys.exit(1)

    lf         = get_client()
    agent_name = args.agent or "claude-code"

    trace = lf.trace(
        name=f"{state['experiment']} / {agent_name}",
        session_id=state["task_id"],
        metadata={
            "agent":      agent_name,
            "task_id":    state["task_id"],
            "started_at": now_iso(),
        },
    )

    # 新对话开始，清空上一轮的 spans（不应有遗留，但防御性清理）
    state["current_trace_id"] = trace.id
    state["current_agent"]    = agent_name
    state["spans"]            = {}
    save_state(state)
    lf.flush()

    pending = list(state.get("pending_spans", {}).keys())
    pending_hint = f"  pending_spans={pending}" if pending else ""
    print(f"[trace] conversation  agent={agent_name}  trace_id={trace.id}  task_id={state['task_id']}{pending_hint}")


def cmd_span_start(args):
    """开启普通 span（同对话内开/关）。"""
    state = load_state()
    lf    = get_client()
    trace = lf.trace(id=current_trace_id())
    key   = span_key(args.name, args.run_id)

    span = trace.span(
        name=args.name,
        metadata={"run_id": args.run_id} if args.run_id else {},
        input=json.loads(args.input) if args.input else {},
        start_time=now_dt(),
    )
    state.setdefault("spans", {})[key] = span.id
    save_state(state)
    lf.flush()
    print(f"[trace] span-start  key={key}  span_id={span.id}")


def cmd_span_defer(args):
    """
    记录异步操作的开始（Slurm job 提交等），不调用 Langfuse。
    完成时由任意 agent 调用 span-end，用历史时间戳补发完整 span。
    """
    state = load_state()
    if not state:
        print("[trace] trace-state.json not found — run 'init' first", file=sys.stderr)
        sys.exit(1)

    key = span_key(args.name, args.run_id)
    state.setdefault("pending_spans", {})[key] = {
        "name":              args.name,
        "run_id":            args.run_id,
        "start_time":        now_iso(),
        "input":             json.loads(args.input) if args.input else {},
        "started_in_trace":  state.get("current_trace_id"),
        "started_by_agent":  state.get("current_agent"),
    }
    save_state(state)
    # 不调用 Langfuse
    print(f"[trace] span-defer  key={key}  start_time recorded (no Langfuse call)")


def cmd_span_end(args):
    """
    关闭 span。自动判断是普通 span 还是延迟 span：
    · 普通 span：从 spans 字典取 span_id，正常关闭
    · 延迟 span：从 pending_spans 取历史开始时间，补发完整 span 到当前 trace
    """
    state   = load_state()
    key     = span_key(args.name, args.run_id)
    output  = json.loads(args.output) if args.output else {}
    level   = "ERROR" if args.status == "error" else "DEFAULT"

    # ── 延迟 span（跨对话异步操作）────────────────────────────────────────────
    if key in state.get("pending_spans", {}):
        pending = state["pending_spans"][key]
        lf      = get_client()
        trace   = lf.trace(id=current_trace_id())

        start_dt = datetime.fromisoformat(pending["start_time"])
        trace.span(
            name=pending["name"],
            start_time=start_dt,
            end_time=now_dt(),
            input=pending["input"],
            output=output,
            level=level,
            metadata={
                "run_id":            pending.get("run_id"),
                "async":             True,
                "started_in_trace":  pending.get("started_in_trace"),
                "started_by_agent":  pending.get("started_by_agent"),
            },
        )
        del state["pending_spans"][key]
        save_state(state)
        lf.flush()

        duration_s = (now_dt() - start_dt).total_seconds()
        print(f"[trace] span-end (deferred)  key={key}  duration={duration_s:.0f}s  status={args.status or 'ok'}")
        return

    # ── 普通 span（同对话）────────────────────────────────────────────────────
    span_id = state.get("spans", {}).get(key)
    if not span_id:
        print(f"[trace] span '{key}' not found in spans or pending_spans — skipping")
        return

    lf    = get_client()
    trace = lf.trace(id=current_trace_id())
    span  = trace.span(id=span_id, end_time=now_dt())
    span.update(output=output, level=level)

    del state["spans"][key]
    save_state(state)
    lf.flush()
    print(f"[trace] span-end  key={key}  status={args.status or 'ok'}")


def cmd_event(args):
    """记录时间点事件。"""
    lf    = get_client()
    trace = lf.trace(id=current_trace_id())
    trace.event(name=args.name, metadata=json.loads(args.data) if args.data else {})
    lf.flush()
    print(f"[trace] event  name={args.name}")


def cmd_score(args):
    """给当前 trace 打分。"""
    lf = get_client()
    lf.score(
        trace_id=current_trace_id(),
        name=args.name,
        value=float(args.value),
        comment=args.comment or "",
    )
    lf.flush()
    print(f"[trace] score  name={args.name}  value={args.value}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap  = argparse.ArgumentParser(description="Stargate trace CLI")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--experiment", required=True)

    p = sub.add_parser("conversation")
    p.add_argument("--agent", default=None, help="agent 名称，如 claude-code / codex")

    for cmd in ("span-start", "span-defer"):
        p = sub.add_parser(cmd)
        p.add_argument("--name",   required=True)
        p.add_argument("--run-id", default=None)
        p.add_argument("--input",  default=None, help="JSON 字符串")

    p = sub.add_parser("span-end")
    p.add_argument("--name",   required=True)
    p.add_argument("--run-id", default=None)
    p.add_argument("--output", default=None, help="JSON 字符串")
    p.add_argument("--status", default="ok", choices=["ok", "error"])

    p = sub.add_parser("event")
    p.add_argument("--name", required=True)
    p.add_argument("--data", default=None, help="JSON 字符串")

    p = sub.add_parser("score")
    p.add_argument("--name",    required=True)
    p.add_argument("--value",   required=True)
    p.add_argument("--comment", default=None)

    args = ap.parse_args()
    {
        "init":         cmd_init,
        "conversation": cmd_conversation,
        "span-start":   cmd_span_start,
        "span-defer":   cmd_span_defer,
        "span-end":     cmd_span_end,
        "event":        cmd_event,
        "score":        cmd_score,
    }[args.command](args)


if __name__ == "__main__":
    main()
