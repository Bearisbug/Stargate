#!/usr/bin/env python3
"""
Stargate experiment visualizer.
Reads rounds/*.json + training logs, generates a self-contained HTML dashboard.

Usage:
    python viz.py                           # rounds/ → reports/dashboard.html
    python viz.py --runs path/to/rounds     # custom rounds dir
    python viz.py --output path/out.html    # custom output
    python viz.py --open                    # open in browser after generating
"""
import argparse
import json
import re
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

# ── Metric patterns ───────────────────────────────────────────────────────────
# Extend or override by passing --patterns key=regex,key=regex
DEFAULT_PATTERNS = {
    "loss":     r"\bloss[=:\s]+([\d.]+)",
    "val_loss": r"\bval(?:_loss)?[=:\s]+([\d.]+)",
    "acc":      r"\bacc(?:uracy)?[=:\s]+([\d.]+)",
    "val_acc":  r"\bval(?:_acc)?[=:\s]+([\d.]+)",
    "reward":   r"\breward[=:\s]+([\d.]+)",
    "lr":       r"\blr[=:\s]+([\d.e+\-]+)",
    # x-axis (step wins over epoch when both present)
    "step":     r"\bstep[=:\s]+(\d+)",
    "epoch":    r"\bepoch[=:\s]+(\d+)",
}


def parse_log(log_path: str | None, patterns: dict = None) -> list[dict]:
    """Parse a training log file and return a list of {step, metric…} dicts."""
    if not log_path:
        return []
    p = Path(log_path)
    if not p.exists():
        return []
    patterns = patterns or DEFAULT_PATTERNS
    rows, cursor = [], 0
    for line in p.read_text(errors="replace").splitlines():
        row = {}
        for key, pat in patterns.items():
            m = re.search(pat, line, re.IGNORECASE)
            if m:
                row[key] = float(m.group(1))
        if len(row) <= 1:       # need at least one metric beyond step/epoch
            continue
        cursor = int(row.pop("step", row.pop("epoch", cursor + 1)))
        rows.append({"step": cursor, **row})
    return rows


# ── Load runs ─────────────────────────────────────────────────────────────────
def load_runs(runs_dir: str, patterns: dict = None) -> list[dict]:
    runs = []
    for p in sorted(Path(runs_dir).glob("*.json")):
        if p.stem == "final_summary":
            continue
        try:
            data = json.loads(p.read_text())
            data["_metrics"] = parse_log(data.get("log_path"), patterns)
            runs.append(data)
        except Exception as e:
            print(f"[viz] skip {p.name}: {e}", file=sys.stderr)
    return runs


# ── Helpers ───────────────────────────────────────────────────────────────────
STATUS_COLOR = {
    "passed":  "#22c55e",
    "failed":  "#ef4444",
    "blocked": "#f97316",
}

def _color(status: str) -> str:
    return STATUS_COLOR.get(status, "#94a3b8")


def _trunc(s: str | None, n: int) -> str:
    if not s:
        return "—"
    return s[:n] + ("…" if len(s) > n else "")


# ── Plotly traces ─────────────────────────────────────────────────────────────
def build_traces(runs: list[dict]) -> list[dict]:
    traces = []
    for run in runs:
        metrics = run.get("_metrics", [])
        if not metrics:
            continue
        metric_keys = [k for k in metrics[0] if k != "step"]
        for key in metric_keys:
            x = [r["step"] for r in metrics if key in r]
            y = [r[key]    for r in metrics if key in r]
            traces.append({
                "name":   f"{run.get('run_id', '?')} / {key}",
                "x":      x,
                "y":      y,
                "type":   "scatter",
                "mode":   "lines",
                "line":   {"color": _color(run.get("status", ""))},
            })
    return traces


# ── HTML ──────────────────────────────────────────────────────────────────────
def generate_html(runs: list[dict], output_path: str) -> str:
    traces_json = json.dumps(build_traces(runs))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Summary table rows
    table_rows = ""
    for r in runs:
        status = r.get("status", "—")
        color  = _color(status)
        table_rows += f"""
        <tr>
          <td><code>{r.get('run_id', '—')}</code></td>
          <td><span style="color:{color};font-weight:600">{status}</span></td>
          <td class="mono small">{_trunc(r.get('command'), 80)}</td>
          <td class="small">{_trunc(r.get('manager_judgement'), 120)}</td>
          <td class="muted small">{(r.get('started_at') or '—')[:16]}</td>
          <td class="muted small">{(r.get('finished_at') or '—')[:16]}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>Stargate · Experiment Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body  {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px 32px; }}
  h1    {{ color: #f8fafc; font-size: 1.4rem; margin: 0 0 4px; }}
  .sub  {{ color: #64748b; font-size: 0.85rem; margin-bottom: 32px; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 20px 24px;
           margin-bottom: 24px; }}
  h2    {{ color: #94a3b8; font-size: 0.8rem; text-transform: uppercase;
           letter-spacing: 0.1em; margin: 0 0 16px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th    {{ text-align: left; color: #475569; font-size: 0.8rem;
           padding: 6px 12px; border-bottom: 1px solid #334155; }}
  td    {{ padding: 9px 12px; border-bottom: 1px solid #263348;
           vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #263348; }}
  code  {{ font-family: "JetBrains Mono", "Fira Code", monospace;
           font-size: 0.85em; }}
  .mono  {{ font-family: "JetBrains Mono", "Fira Code", monospace; }}
  .small {{ font-size: 0.85em; }}
  .muted {{ color: #64748b; }}
  #chart {{ width: 100%; height: 460px; }}
  .no-data {{ color: #475569; font-size: 0.9rem; padding: 24px 0; }}
</style>
</head>
<body>
<h1>Stargate · Experiment Dashboard</h1>
<div class="sub">Generated {generated_at} &nbsp;·&nbsp; {len(runs)} runs</div>

<div class="card">
  <h2>Run Summary</h2>
  <table>
    <thead><tr>
      <th>Run</th>
      <th>Status</th>
      <th>Command</th>
      <th>Manager Judgement</th>
      <th>Started</th>
      <th>Finished</th>
    </tr></thead>
    <tbody>{table_rows or '<tr><td colspan="6" class="no-data">No runs found.</td></tr>'}</tbody>
  </table>
</div>

<div class="card">
  <h2>Training Curves</h2>
  {"<div id='chart'></div>" if any(r.get('_metrics') for r in runs)
   else "<div class='no-data'>No metric data found in training logs.<br>Make sure <code>log_path</code> is set in each run JSON and the log files are accessible.</div>"}
</div>

<script>
(function () {{
  const traces = {traces_json};
  if (!traces.length) return;
  const layout = {{
    paper_bgcolor: "transparent",
    plot_bgcolor:  "#0f172a",
    font:   {{ color: "#e2e8f0", size: 12 }},
    xaxis:  {{ title: "Step", gridcolor: "#1e293b", zeroline: false }},
    yaxis:  {{ gridcolor: "#1e293b", zeroline: false }},
    legend: {{ bgcolor: "rgba(0,0,0,0)", borderwidth: 0 }},
    margin: {{ t: 16, b: 48, l: 56, r: 16 }},
    hovermode: "x unified",
  }};
  Plotly.newPlot("chart", traces, layout, {{
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  }});
}})();
</script>
</body>
</html>"""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out.resolve())


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_patterns(s: str | None) -> dict:
    """Parse 'key=regex,key=regex' into a dict, merged with defaults."""
    if not s:
        return DEFAULT_PATTERNS
    extra = {}
    for part in s.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            extra[k.strip()] = v.strip()
    return {**DEFAULT_PATTERNS, **extra}


def main():
    ap = argparse.ArgumentParser(description="Stargate experiment visualizer")
    ap.add_argument("--runs",     default="rounds",
                    help="Directory containing run JSON files (default: rounds/)")
    ap.add_argument("--output",   default="reports/dashboard.html",
                    help="Output HTML path (default: reports/dashboard.html)")
    ap.add_argument("--patterns", default=None,
                    help="Extra metric patterns: 'key=regex,key=regex'")
    ap.add_argument("--open",     action="store_true",
                    help="Open dashboard in browser after generating")
    args = ap.parse_args()

    patterns = parse_patterns(args.patterns)
    runs = load_runs(args.runs, patterns)
    if not runs:
        print(f"[viz] no run JSONs found in '{args.runs}'", file=sys.stderr)
        sys.exit(1)

    out = generate_html(runs, args.output)
    print(f"[viz] dashboard written → {out}")

    if args.open:
        webbrowser.open(f"file://{out}")


if __name__ == "__main__":
    main()
