#!/usr/bin/env python3
"""
Stargate Feishu 控制守护进程 v2

改进：
- 多实验目录（experiments/{timestamp}_{slug}/）
- 逐阶段推进：每次 Claude 只跑一个阶段，daemon 检测 phase 变化自动触发下一阶段
- 全阶段失败重试（含 DESIGN/EXECUTING/ANALYZING/REPORTING）
- 用量限制自动等待重试
- 所有中断场景均可自动恢复

飞书命令：
  /run <idea>   启动新实验
  /status       查看当前实验进度
  /stop         中断当前实验及自动推进
  /report       发送最近一次报告
  /help         命令列表
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from feishu import FeishuCommandPoller, FeishuNotifier, FeishuCommand, load_feishu_config

HELP_TEXT = """\
Stargate 实验 Agent 🤖

命令列表：
  /run <idea>   启动新实验
  /status       查看实验进度
  /stop         中断当前实验
  /report       发送最近报告
  /help         显示此帮助
"""

WAITING_POLL_INTERVAL = 120   # 秒，WAITING 阶段 SSH 轮询间隔
MAX_PHASE_RETRIES = 3         # 每个阶段最多重试次数


# ── Phase prompt 模板 ────────────────────────────────────────────

def _phase_prompt(phase: str, exp_dir: Path, work_dir: Path, idea: str = "") -> str:
    feishu_cmd = f"python {work_dir / 'tools' / 'feishu.py'}"
    header = (
        f"Experiment directory: {exp_dir}\n"
        f"All experiment artifacts (TRACKER, LOG, rounds/, reports/) go in: {exp_dir}\n"
        "Read EXPERIMENT_TRACKER.md in that directory to understand current state.\n"
        "IMPORTANT: Use the `experiment` skill (invoke via Skill tool, skill name: experiment) "
        "to execute this task — it contains all phase logic, method references, and artifact specs.\n"
        "IMPORTANT: Fully automated run — do NOT pause for user confirmation at any step.\n"
        "IMPORTANT: Execute ONLY the phase specified below. "
        "When that phase is complete, update TRACKER and exit immediately. "
        "Do NOT continue to the next phase.\n"
        f"Send Feishu notifications via: {feishu_cmd} send \"<message>\"\n\n"
    )
    instructions: dict[str, str] = {
        "": (
            f"Start a new experiment for this idea: {idea}\n\n"
            "Execute ONLY the PLAN phase:\n"
            "- Extract Claims and success criteria from the idea\n"
            "- Create EXPERIMENT_TRACKER.md and EXPERIMENT_LOG.md in the experiment directory\n"
            "- When done: set phase=ENVIRONMENT in TRACKER, then exit."
        ),
        "PLAN": (
            f"Idea: {idea}\n\n"
            "Execute ONLY the PLAN phase:\n"
            "- Extract Claims and success criteria\n"
            "- Create/update EXPERIMENT_TRACKER.md and EXPERIMENT_LOG.md\n"
            "- When done: set phase=ENVIRONMENT in TRACKER, then exit."
        ),
        "ENVIRONMENT": (
            "Execute ONLY the ENVIRONMENT phase:\n"
            "- If env_handle.json already exists and status=ready, skip to updating TRACKER\n"
            "- Otherwise: connect to server, verify Slurm/conda/GPU environment\n"
            "- Write env_handle.json to the experiment directory\n"
            "- When done: set phase=DESIGN in TRACKER, then exit."
        ),
        "DESIGN": (
            "Execute ONLY the DESIGN phase:\n"
            "- Read env_handle.json, select current Claim, choose method\n"
            "- Write/update experiment code\n"
            "- Run sanity check (minimal scale)\n"
            "- Commit code changes\n"
            "- When done: set phase=EXECUTING in TRACKER, then exit."
        ),
        "EXECUTING": (
            "Execute ONLY the EXECUTING phase:\n"
            "- Submit the job (sbatch / tmux / docker as appropriate)\n"
            "- Record job_id, git_hash, expected_outputs in TRACKER\n"
            "- When done: set phase=WAITING in TRACKER, then exit."
        ),
        "ANALYZING": (
            "Execute ONLY the ANALYZING phase:\n"
            "- Pull output files from server\n"
            "- Parse metrics, evaluate against Claim success criteria\n"
            "- Write rounds/<run_id>.json\n"
            "- Update Claim status in TRACKER\n"
            "- When done: set phase=REPORTING (or DESIGN if iterating) in TRACKER, then exit."
        ),
        "REPORTING": (
            "Execute ONLY the REPORTING phase:\n"
            "- Read all rounds/*.json\n"
            "- Generate reports/report.md\n"
            "- Generate rounds/insights/claim_N.md for each answered Claim\n"
            "- When done: set phase=DONE in TRACKER, then exit."
        ),
    }
    return header + instructions.get(phase, f"Continue from phase={phase}. Complete it, update TRACKER, then exit.")


def _phase_label(phase: str) -> str:
    labels = {
        "": "PLAN", "PLAN": "PLAN", "ENVIRONMENT": "ENVIRONMENT",
        "DESIGN": "DESIGN", "EXECUTING": "EXECUTING", "WAITING": "WAITING",
        "ANALYZING": "ANALYZING", "REPORTING": "REPORTING", "DONE": "DONE",
    }
    return labels.get(phase, phase)


# ── Daemon ───────────────────────────────────────────────────────

class StargateFeishuDaemon:
    def __init__(self, work_dir: Path, notifier: FeishuNotifier) -> None:
        self._work_dir = work_dir
        self._notifier = notifier
        self._proc: subprocess.Popen | None = None
        self._proc_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._waiting_timer: threading.Timer | None = None
        self._polling_stopped = False
        self._phase_retries: dict[str, int] = {}   # "exp_dir:phase" → count
        self._current_exp_dir: Path | None = None
        self._active_token: int = 0  # 每次 /run 递增，旧实验线程检测到不匹配则退出

    # ── 命令处理 ──────────────────────────────────────────────────

    def handle(self, cmd: FeishuCommand) -> None:
        print(f"[daemon] 收到命令: /{cmd.kind} {cmd.text[:80]}")
        if cmd.kind == "run":
            self._cmd_run(cmd.text)
        elif cmd.kind == "status":
            self._cmd_status()
        elif cmd.kind == "stop":
            self._cmd_stop()
        elif cmd.kind == "report":
            self._cmd_report()
        elif cmd.kind == "help":
            self._notifier.send_message(HELP_TEXT)
        elif cmd.kind == "inject":
            self._notifier.send_message("💬 提示：用 /run <想法> 启动实验，/help 查看命令。")

    def _cmd_run(self, idea: str) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._notifier.send_message(
                    f"⚠️ 当前已有实验在运行，请先 /stop 再启动新实验。\nPID: {self._proc.pid}"
                )
                return
        if not idea.strip():
            self._notifier.send_message("用法：/run <实验 idea>")
            return

        exp_dir = self._create_exp_dir(idea)
        self._current_exp_dir = exp_dir
        self._polling_stopped = False
        self._phase_retries.clear()
        self._cancel_waiting_timer()
        self._active_token += 1  # 使旧实验的所有后台线程失效
        # 清除 stopped 标记
        stopped_file = exp_dir / ".stopped"
        if stopped_file.exists():
            stopped_file.unlink()
        self._notifier.send_message(f"🚀 启动实验：{idea[:200]}\n实验目录：{exp_dir.name}")
        self._trigger_phase(exp_dir, "", idea=idea)

    def _cmd_status(self) -> None:
        with self._lock:
            running = self._proc and self._proc.poll() is None
            pid = self._proc.pid if self._proc else None
        proc_status = f"🟢 claude 运行中 (PID {pid})" if running else "⚪ 无活跃子进程"

        exp_dir = self._get_active_exp_dir()
        if not exp_dir:
            self._notifier.send_message(f"📭 无活跃实验\n{proc_status}")
            return
        tracker = exp_dir / "EXPERIMENT_TRACKER.md"
        if not tracker.exists():
            self._notifier.send_message(f"📭 无 TRACKER\n实验目录: {exp_dir.name}\n{proc_status}")
            return
        content = tracker.read_text(encoding="utf-8")
        lines = [l for l in content.splitlines()
                 if any(l.startswith(k) for k in
                        ("phase:", "job_id:", "updated_at:", "retry_count:", "next:"))]
        summary = "\n".join(lines) if lines else content[:400]
        self._notifier.send_message(
            f"📊 [{exp_dir.name}]\n\n{summary}\n\n{proc_status}"
        )

    def _cmd_stop(self) -> None:
        self._polling_stopped = True
        self._cancel_waiting_timer()
        # 持久化 stopped 状态，防止 daemon 重启后自动恢复
        exp_dir = self._get_active_exp_dir()
        if exp_dir:
            (exp_dir / ".stopped").touch()
        with self._lock:
            proc = self._proc
        if not proc or proc.poll() is not None:
            self._notifier.send_message("⚪ 当前没有运行中的实验（自动推进已停止）。")
            return
        try:
            proc.terminate()
            time.sleep(2)
            if proc.poll() is None:
                proc.kill()
            self._notifier.send_message(f"🛑 实验已中断 (PID {proc.pid})，自动推进已停止。")
        except Exception as e:
            self._notifier.send_message(f"❌ 中断失败: {e}")

    def _cmd_report(self) -> None:
        exp_dir = self._get_active_exp_dir()
        if not exp_dir:
            self._notifier.send_message("📭 无活跃实验")
            return
        report = exp_dir / "reports" / "report.md"
        if not report.exists():
            self._notifier.send_message(
                f"📭 暂无报告（{exp_dir.name}/reports/report.md 不存在）"
            )
            return
        self._notifier.send_report(str(report))

    # ── 实验目录 ──────────────────────────────────────────────────

    def _create_exp_dir(self, idea: str) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-zA-Z0-9]", "_", idea[:40]).strip("_")
        name = f"{ts}_{slug}"
        exp_dir = self._work_dir / "experiments" / name
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "idea.txt").write_text(idea, encoding="utf-8")
        (self._work_dir / "active_exp").write_text(name, encoding="utf-8")
        return exp_dir

    def _get_active_exp_dir(self) -> Path | None:
        # 优先当前 session 记录
        if self._current_exp_dir and self._current_exp_dir.exists():
            return self._current_exp_dir
        # 读 active_exp 文件
        active_file = self._work_dir / "active_exp"
        if active_file.exists():
            name = active_file.read_text(encoding="utf-8").strip()
            p = self._work_dir / "experiments" / name
            if p.exists():
                self._current_exp_dir = p
                return p
        # 向后兼容：旧版 TRACKER 在 work_dir 根目录
        if (self._work_dir / "EXPERIMENT_TRACKER.md").exists():
            return self._work_dir
        return None

    def _get_tracker_phase(self, exp_dir: Path) -> str:
        tracker = exp_dir / "EXPERIMENT_TRACKER.md"
        if not tracker.exists():
            return ""
        for line in tracker.read_text(encoding="utf-8").splitlines():
            if line.startswith("phase:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _get_exp_idea(self, exp_dir: Path) -> str:
        idea_file = exp_dir / "idea.txt"
        return idea_file.read_text(encoding="utf-8").strip() if idea_file.exists() else ""

    # ── 阶段推进状态机 ────────────────────────────────────────────

    def _trigger_phase(self, exp_dir: Path, phase: str, idea: str = "",
                       token: int | None = None) -> None:
        if self._polling_stopped:
            return
        # 若 token 不匹配，说明已有新实验启动，当前调用作废
        if token is not None and token != self._active_token:
            print(f"[daemon] token 过期，丢弃 {exp_dir.name} phase={_phase_label(phase)}")
            return
        if not idea:
            idea = self._get_exp_idea(exp_dir)
        prompt = _phase_prompt(phase, exp_dir, self._work_dir, idea=idea)
        self._spawn_claude(prompt, exp_dir=exp_dir, phase=phase, idea=idea,
                           token=self._active_token)

    def _on_claude_exit(self, exp_dir: Path, prev_phase: str,
                        returncode: int, tail: str, idea: str = "",
                        token: int | None = None) -> None:
        """Claude 子进程退出后的状态机推进。"""
        if self._polling_stopped:
            return
        # token 过期：已有新实验启动，丢弃
        if token is not None and token != self._active_token:
            print(f"[daemon] token 过期，丢弃 {exp_dir.name} 退出处理")
            return

        # 用量限制：等到重置时间后重试
        if _is_rate_limit(tail):
            reset_dt = _parse_reset_time(tail)
            wait_sec = max(300, int((reset_dt - datetime.now()).total_seconds())) if reset_dt else 3600
            self._notifier.send_message(
                f"⏳ Claude 用量已用完，{int(wait_sec/60)} 分钟后自动重试"
                f"（{_phase_label(prev_phase)} 阶段）。"
            )
            t = threading.Timer(wait_sec,
                                lambda: self._trigger_phase(exp_dir, prev_phase, idea=idea))
            t.daemon = True
            t.start()
            return

        new_phase = self._get_tracker_phase(exp_dir)

        # 非零退出
        if returncode != 0:
            self._handle_phase_failure(
                exp_dir, prev_phase, idea,
                f"exit code {returncode}\n{tail[-300:]}", token=token
            )
            return

        # 实验完成
        if new_phase == "DONE":
            self._cancel_waiting_timer()
            report = exp_dir / "reports" / "report.md"
            if report.exists():
                self._notifier.send_report(str(report))
            else:
                self._notifier.send_message("✅ 实验完成（无报告文件）。")
            return

        # 进入 WAITING：daemon 接管 SSH 轮询
        if new_phase == "WAITING":
            self._maybe_start_waiting_poll_for(exp_dir)
            return

        # phase 没推进（Claude 退出但没更新 TRACKER）
        if not new_phase or new_phase == prev_phase:
            self._handle_phase_failure(
                exp_dir, prev_phase, idea, "TRACKER phase 未推进", token=token
            )
            return

        # phase 成功推进，立即触发下一阶段
        print(f"[daemon] {prev_phase or 'START'} → {new_phase}，继续推进")
        self._phase_retries.pop(f"{exp_dir}:{prev_phase}", None)
        self._trigger_phase(exp_dir, new_phase, idea=idea, token=token)

    def _handle_phase_failure(self, exp_dir: Path, phase: str,
                               idea: str, reason: str, token: int | None = None) -> None:
        # token 过期说明已有新实验，直接放弃
        if token is not None and token != self._active_token:
            return
        key = f"{exp_dir}:{phase}"
        count = self._phase_retries.get(key, 0) + 1
        self._phase_retries[key] = count
        if count > MAX_PHASE_RETRIES:
            self._notifier.send_message(
                f"❌ {_phase_label(phase)} 阶段重试 {MAX_PHASE_RETRIES} 次仍失败，"
                f"需要人工介入。\n原因：{reason[:300]}"
            )
            return
        self._notifier.send_message(
            f"🔄 {_phase_label(phase)} 失败，第 {count}/{MAX_PHASE_RETRIES} 次重试...\n"
            f"原因：{reason[:150]}"
        )
        time.sleep(5)
        self._trigger_phase(exp_dir, phase, idea=idea, token=token)

    # ── WAITING 轮询 ──────────────────────────────────────────────

    def _maybe_start_waiting_poll_for(self, exp_dir: Path) -> None:
        phase = self._get_tracker_phase(exp_dir)
        if phase not in ("WAITING", "ANALYZING", "REPORTING"):
            return
        tracker = exp_dir / "EXPERIMENT_TRACKER.md"
        job_id = ""
        if tracker.exists():
            for line in tracker.read_text(encoding="utf-8").splitlines():
                if line.startswith("job_id:"):
                    job_id = line.split(":", 1)[1].strip()
                    break
        print(f"[daemon] phase={phase} (job={job_id})，{WAITING_POLL_INTERVAL}s 后自动轮询")
        self._schedule_waiting_poll(exp_dir)

    def _schedule_waiting_poll(self, exp_dir: Path) -> None:
        self._cancel_waiting_timer()
        self._waiting_timer = threading.Timer(
            WAITING_POLL_INTERVAL, lambda: self._do_waiting_poll(exp_dir)
        )
        self._waiting_timer.daemon = True
        self._waiting_timer.start()

    def _do_waiting_poll(self, exp_dir: Path) -> None:
        if self._polling_stopped:
            return
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._schedule_waiting_poll(exp_dir)
                return

        phase = self._get_tracker_phase(exp_dir)

        # ANALYZING/REPORTING 阶段 Claude 中途退出：重调继续
        if phase in ("ANALYZING", "REPORTING"):
            print(f"[daemon] 自动轮询：phase={phase}，重调 Claude 继续")
            self._trigger_phase(exp_dir, phase)
            return

        if phase != "WAITING":
            return

        # WAITING：直接 SSH 查 job，不消耗 Claude token
        tracker = exp_dir / "EXPERIMENT_TRACKER.md"
        job_id = ""
        if tracker.exists():
            for line in tracker.read_text(encoding="utf-8").splitlines():
                if line.startswith("job_id:"):
                    job_id = line.split(":", 1)[1].strip()
                    break

        host = self._get_ssh_host(exp_dir)
        if not host or not job_id:
            self._schedule_waiting_poll(exp_dir)
            return

        # 根据 job_id 格式选择检查方式
        if job_id.startswith("nohup/") or job_id.startswith("tmux/"):
            pid = job_id.split("/", 1)[1]
            status = _check_nohup_job(host, pid, exp_dir)
        else:
            status = _check_slurm_job(host, job_id)
        print(f"[daemon] job {job_id} 状态: {status}")

        if status == "RUNNING":
            self._schedule_waiting_poll(exp_dir)
        elif status == "COMPLETED":
            self._cancel_waiting_timer()
            self._notifier.send_message(f"✅ Job {job_id} 已完成，开始分析结果...")
            self._trigger_phase(exp_dir, "ANALYZING")
        elif status == "UNKNOWN":
            # 进程找不到，可能已完成也可能崩了，交给 Claude 判断
            self._cancel_waiting_timer()
            self._notifier.send_message(f"🔍 Job {job_id} 进程已退出，检查结果...")
            self._trigger_phase(exp_dir, "ANALYZING")
        else:
            # FAILED / CANCELLED 等
            self._cancel_waiting_timer()
            self._notifier.send_message(f"⚠️ Job {job_id} 状态异常（{status}），尝试自动处理...")
            self._trigger_phase(exp_dir, "WAITING")

    def _cancel_waiting_timer(self) -> None:
        if self._waiting_timer:
            self._waiting_timer.cancel()
            self._waiting_timer = None

    def _get_ssh_host(self, exp_dir: Path | None = None) -> str | None:
        search_dirs = []
        if exp_dir:
            search_dirs.append(exp_dir)
        search_dirs.append(self._work_dir)
        for d in search_dirs:
            for fname in ("env_handle.json", "project.json"):
                fpath = d / fname
                if not fpath.exists():
                    continue
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    host = data.get("host") or (data.get("servers", {}) or {}).get("default")
                    if host:
                        return host
                except Exception:
                    pass
        return None

    # ── Claude 子进程 ──────────────────────────────────────────────

    def _spawn_claude(self, prompt: str, exp_dir: Path | None = None,
                      phase: str = "", idea: str = "", token: int | None = None) -> None:
        if exp_dir is None:
            exp_dir = self._get_active_exp_dir() or self._work_dir
        _exp_dir = exp_dir  # 闭包捕获

        def _run() -> None:
            import shutil
            bash = shutil.which("bash") or "bash"
            escaped = prompt.replace("'", "'\\''")
            cmd = [bash, "-c",
                   f"claude --print --dangerously-skip-permissions -p '{escaped}'"]
            env = os.environ.copy()
            git_bash = _find_git_bash()
            if git_bash:
                env["CLAUDE_CODE_GIT_BASH_PATH"] = git_bash
            print(f"[daemon] 启动 claude phase={_phase_label(phase)} "
                  f"exp={_exp_dir.name} ...")
            with self._lock:
                try:
                    self._proc = subprocess.Popen(
                        cmd,
                        cwd=str(_exp_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=env,
                    )
                except FileNotFoundError:
                    self._notifier.send_message(
                        "❌ 找不到 `bash` 或 `claude` 命令。\n"
                        "请确认 git-bash 和 Claude Code CLI 已安装。"
                    )
                    return

            proc = self._proc
            tail_lines: list[str] = []
            for line in proc.stdout:
                print(f"[claude] {line}", end="", flush=True)
                tail_lines.append(line)
                if len(tail_lines) > 50:
                    tail_lines.pop(0)

            returncode = proc.wait()
            tail = "".join(tail_lines[-20:]).strip()
            self._on_claude_exit(_exp_dir, phase, returncode, tail,
                                 idea=idea, token=token)

        self._proc_thread = threading.Thread(target=_run, daemon=True)
        self._proc_thread.start()


# ── 工具函数 ─────────────────────────────────────────────────────

def _is_rate_limit(text: str) -> bool:
    t = text.lower()
    return "hit your limit" in t or "rate limit" in t or "resets" in t


def _parse_reset_time(text: str) -> datetime | None:
    """从 'resets 6am (Asia/Shanghai)' 等字符串解析重置时间。"""
    import re as _re
    m = _re.search(r"resets\s+(\d{1,2})(am|pm)", text, _re.IGNORECASE)
    if not m:
        return None
    hour = int(m.group(1))
    if m.group(2).lower() == "pm" and hour != 12:
        hour += 12
    now = datetime.now()
    reset = now.replace(hour=hour, minute=5, second=0, microsecond=0)
    if reset <= now:
        reset = reset.replace(day=now.day + 1)
    return reset


def _check_nohup_job(host: str, pid: str, exp_dir: Path) -> str:
    """检查 nohup/tmux 进程是否还在运行。"""
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host,
             f"ps -p {pid} -o pid= 2>/dev/null"],
            capture_output=True, text=True, timeout=15
        )
        if r.stdout.strip():
            return "RUNNING"
        return "UNKNOWN"  # 进程已退出，让 Claude 判断成功/失败
    except Exception as e:
        print(f"[daemon] _check_nohup_job 异常: {e}")
        return "UNKNOWN"


def _check_slurm_job(host: str, job_id: str) -> str:
    """SSH 查询 Slurm job 状态。返回 RUNNING/PENDING/COMPLETED/FAILED/CANCELLED/UNKNOWN。"""
    try:
        r = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host,
             f"squeue -j {job_id} -h -o '%T' 2>/dev/null"],
            capture_output=True, text=True, timeout=15
        )
        state = r.stdout.strip().upper()
        if state in ("RUNNING", "PENDING", "CONFIGURING", "COMPLETING"):
            return "RUNNING" if state == "CONFIGURING" else state
        r2 = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host,
             f"sacct -j {job_id} -n -o State --noheader 2>/dev/null | head -1"],
            capture_output=True, text=True, timeout=15
        )
        state2 = r2.stdout.strip().upper().split()[0] if r2.stdout.strip() else ""
        return state2 if state2 else "UNKNOWN"
    except Exception as e:
        print(f"[daemon] _check_slurm_job 异常: {e}")
        return "UNKNOWN"


def _find_git_bash() -> str | None:
    import shutil, subprocess as sp
    bash = shutil.which("bash")
    if not bash:
        return None
    try:
        r = sp.run(["cygpath", "-w", bash], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    for candidate in [
        r"D:\Git\usr\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Git\usr\bin\bash.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    return None


# ── 入口 ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Stargate Feishu Daemon v2")
    parser.add_argument("--work-dir", default=".", help="项目根目录（含 project.json）")
    args = parser.parse_args()

    work_dir = Path(args.work_dir).resolve()
    if not (work_dir / "project.json").exists():
        print(f"[daemon] 错误：{work_dir}/project.json 不存在", file=sys.stderr)
        sys.exit(1)

    os.chdir(work_dir)

    cfg = load_feishu_config()
    if not cfg:
        print("[daemon] 错误：feishu 未配置（检查 project.json feishu 字段）", file=sys.stderr)
        sys.exit(1)

    notifier = FeishuNotifier(cfg["app_id"], cfg["app_secret"], cfg["chat_id"])
    daemon = StargateFeishuDaemon(work_dir, notifier)

    poller = FeishuCommandPoller(
        app_id=cfg["app_id"],
        app_secret=cfg["app_secret"],
        chat_id=cfg["chat_id"],
        on_command=daemon.handle,
        poll_interval=2,
    )

    def _shutdown(sig, frame):
        print("\n[daemon] 收到退出信号，正在停止...")
        poller.stop()
        notifier.send_message("🔴 Stargate daemon 已停止。")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # 启动时自动恢复未完成实验
    exp_dir = daemon._get_active_exp_dir()
    startup_msg = f"🟢 Stargate daemon 已启动\n工作目录：{work_dir}"
    if exp_dir:
        phase = daemon._get_tracker_phase(exp_dir)
        stopped = (exp_dir / ".stopped").exists()
        if stopped:
            startup_msg += f"\n\n⏸️ 实验 [{exp_dir.name}] 已手动停止（phase={phase}），发送 /run 继续。"
        elif phase == "DONE" or not phase:
            pass
        elif phase == "WAITING":
            startup_msg += f"\n\n🔄 恢复实验 [{exp_dir.name}]（phase=WAITING），自动恢复监控..."
            daemon._maybe_start_waiting_poll_for(exp_dir)
        elif phase in ("ANALYZING", "REPORTING"):
            startup_msg += f"\n\n🔄 恢复实验 [{exp_dir.name}]（phase={phase}），自动继续..."
            daemon._maybe_start_waiting_poll_for(exp_dir)
        else:
            startup_msg += (
                f"\n\n⚠️ 检测到未完成实验 [{exp_dir.name}]（phase={phase}），"
                f"发送 /run 继续执行。"
            )
    startup_msg += "\n\n发送 /help 查看可用命令。"
    notifier.send_message(startup_msg)
    poller.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown(None, None)


if __name__ == "__main__":
    main()
