#!/usr/bin/env python3
"""
Stargate Feishu 客户端 — 消息推送 + 命令接收。

CLI 用法（供 experiment skill 调用）：
  python tools/feishu.py send "消息内容"
  python tools/feishu.py send-file /path/to/file [--caption "说明"]

配置：从当前目录或上级目录的 project.json 读取 feishu 字段。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

# ── 配置加载 ────────────────────────────────────────────────

def find_project_json() -> Path | None:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        p = parent / "project.json"
        if p.exists():
            return p
    return None


def load_feishu_config() -> dict[str, str] | None:
    path = find_project_json()
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    cfg = data.get("feishu", {})
    if not cfg.get("enabled"):
        return None
    required = ("app_id", "app_secret", "chat_id")
    if not all(cfg.get(k) for k in required):
        return None
    return {k: cfg[k] for k in required}


# ── Token 管理 ────────────────────────────────────────────────

class FeishuTokenManager:
    _TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    def __init__(self, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._token: str | None = None
        self._expires_at = 0.0

    def get(self) -> str | None:
        if self._token and time.time() < self._expires_at - 30:
            return self._token
        payload = json.dumps({"app_id": self._app_id, "app_secret": self._app_secret}).encode()
        req = urllib.request.Request(self._TOKEN_URL, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        result = _json_request(req, label="feishu auth")
        if not result:
            return None
        token = result.get("tenant_access_token", "").strip()
        if not token:
            return None
        self._token = token
        self._expires_at = time.time() + int(result.get("expire", 7200))
        return self._token


# ── Notifier ────────────────────────────────────────────────

class FeishuNotifier:
    _SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
    _IMAGE_URL = "https://open.feishu.cn/open-apis/im/v1/images"
    _FILE_URL  = "https://open.feishu.cn/open-apis/im/v1/files"

    def __init__(self, app_id: str, app_secret: str, chat_id: str) -> None:
        self._tokens = FeishuTokenManager(app_id, app_secret)
        self._chat_id = chat_id

    def send_message(self, text: str) -> bool:
        token = self._tokens.get()
        if not token:
            return False
        ok = True
        for chunk in _split(text):
            ok = self._send(token, "text", {"text": chunk}) and ok
        return ok

    def send_file(self, path: str | Path, caption: str = "") -> bool:
        token = self._tokens.get()
        if not token:
            return False
        p = Path(path)
        if not p.exists():
            print(f"[feishu] 文件不存在: {p}", file=sys.stderr)
            return False
        data = p.read_bytes()
        suffix = p.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            key = self._upload_image(token, p.name, data)
            if not key:
                return False
            ok = self._send(token, "image", {"image_key": key})
        else:
            key = self._upload_file(token, p.name, data)
            if not key:
                return False
            ok = self._send(token, "file", {"file_key": key})
        if caption.strip():
            self._send(token, "text", {"text": caption[:1500]})
        return ok

    def _send(self, token: str, msg_type: str, content: dict) -> bool:
        body = json.dumps({
            "receive_id": self._chat_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        }, ensure_ascii=False).encode()
        url = self._SEND_URL + "?" + urllib.parse.urlencode({"receive_id_type": "chat_id"})
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8",
                                              "Authorization": f"Bearer {token}"})
        return _json_request(req, label="feishu send") is not None

    def _upload_image(self, token: str, name: str, data: bytes) -> str | None:
        result = _multipart_post(token, self._IMAGE_URL,
                                 {"image_type": "message"}, "image", name, data)
        return (result or {}).get("data", {}).get("image_key")

    def _upload_file(self, token: str, name: str, data: bytes) -> str | None:
        result = _multipart_post(token, self._FILE_URL,
                                 {"file_type": "stream", "file_name": name}, "file", name, data)
        return (result or {}).get("data", {}).get("file_key")

    def send_report(self, path: str | Path) -> bool:
        """将 report.md 转换为飞书富文本消息发送。"""
        p = Path(path)
        if not p.exists():
            return self.send_message(f"📭 报告文件不存在：{p}")
        md = p.read_text(encoding="utf-8")
        post = _md_to_feishu_post(md)
        token = self._tokens.get()
        if not token:
            return False
        return self._send(token, "post", post)


# ── Command Poller ────────────────────────────────────────────────

@dataclass
class FeishuCommand:
    kind: str   # run / status / stop / report / help / inject
    text: str


CommandCallback = Callable[[FeishuCommand], None]


class FeishuCommandPoller:
    _LIST_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

    def __init__(self, app_id: str, app_secret: str, chat_id: str,
                 on_command: CommandCallback, poll_interval: int = 2) -> None:
        self._tokens = FeishuTokenManager(app_id, app_secret)
        self._chat_id = chat_id
        self._on_command = on_command
        self._poll_interval = max(1, poll_interval)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_id: str | None = None
        # 只处理 daemon 启动后的消息（毫秒时间戳）
        self._start_ms = int(time.time() * 1000)

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                for msg in self._fetch_new():
                    cmd = _parse_command(msg)
                    if cmd:
                        self._on_command(cmd)
            except Exception as e:
                print(f"[feishu poller] {e}", file=sys.stderr)
            self._stop.wait(self._poll_interval)

    def _fetch_new(self) -> list[dict]:
        token = self._tokens.get()
        if not token:
            return []
        params = {"container_id_type": "chat", "container_id": self._chat_id,
                  "sort_type": "ByCreateTimeDesc", "page_size": "20"}
        req = urllib.request.Request(
            self._LIST_URL + "?" + urllib.parse.urlencode(params), method="GET",
            headers={"Authorization": f"Bearer {token}"})
        result = _json_request(req, label="feishu list")
        items = (result or {}).get("data", {}).get("items", [])
        if not isinstance(items, list):
            return []
        # 只返回 daemon 启动后且尚未处理的新消息
        fresh = []
        for item in items:
            msg_id = item.get("message_id", "")
            if msg_id and msg_id == self._last_id:
                break
            create_time = int(item.get("create_time", 0))
            if create_time < self._start_ms:
                break
            fresh.append(item)
        if fresh:
            self._last_id = fresh[0].get("message_id", self._last_id)
        elif self._last_id is None and items:
            # 首次轮询，初始化游标但不处理历史消息
            self._last_id = items[0].get("message_id", "")
        return list(reversed(fresh))


# ── 命令解析 ────────────────────────────────────────────────

def _parse_command(item: dict) -> FeishuCommand | None:
    # 过滤 bot 自身消息
    sender = item.get("sender", {})
    if str(sender.get("sender_type", "")).lower() in {"app", "bot"}:
        return None
    body = item.get("body", {}).get("content", "")
    try:
        text = json.loads(body).get("text", "").strip()
    except Exception:
        return None
    if not text:
        return None
    # 去除 @mention 前缀
    while text.startswith("@"):
        parts = text.split(None, 1)
        text = parts[1].strip() if len(parts) > 1 else ""
    if not text:
        return None
    lo = text.lower()
    if lo.startswith("/run "):
        return FeishuCommand("run", text[5:].strip())
    if lo in {"/status", "/stat"}:
        return FeishuCommand("status", "")
    if lo in {"/stop", "/halt"}:
        return FeishuCommand("stop", "")
    if lo in {"/report"}:
        return FeishuCommand("report", "")
    if lo in {"/help", "/commands"}:
        return FeishuCommand("help", "")
    if not lo.startswith("/"):
        return FeishuCommand("inject", text)
    return None


# ── 工具函数 ────────────────────────────────────────────────

def _json_request(req: urllib.request.Request, *, label: str) -> dict | None:
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        print(f"[feishu] {label} HTTP {e.code}: {body[:300]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[feishu] {label} error: {e}", file=sys.stderr)
        return None
    if result.get("code", 0) not in {0, "0", None}:
        print(f"[feishu] {label} api error code={result.get('code')} msg={result.get('msg')}", file=sys.stderr)
        return None
    return result


def _md_to_feishu_post(md: str) -> dict:
    """将 Markdown 转换为飞书 post 富文本格式。"""
    import re as _re

    def _inline(text: str) -> list[dict]:
        """解析行内 **bold** 和普通文本，返回 inline 元素列表。"""
        parts = _re.split(r"(\*\*[^*]+\*\*)", text)
        elems = []
        for part in parts:
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                elems.append({"tag": "text", "text": part[2:-2], "style": ["bold"]})
            else:
                elems.append({"tag": "text", "text": part})
        return elems or [{"tag": "text", "text": text}]

    title = ""
    content: list[list[dict]] = []
    in_code = False
    in_table = False

    for line in md.splitlines():
        # 代码块
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            content.append([{"tag": "text", "text": line}])
            continue

        # 表格
        if line.startswith("|"):
            if _re.match(r"^[\|\s\-:]+$", line):
                continue  # 分隔行
            cells = [c.strip() for c in line.split("|") if c.strip()]
            content.append([{"tag": "text", "text": "  ".join(cells)}])
            continue

        # H1 → 标题
        if line.startswith("# "):
            if not title:
                title = line[2:].strip()
            else:
                content.append([{"tag": "text", "text": line[2:].strip(), "style": ["bold"]}])
            continue

        # H2/H3 → 加粗段落
        if line.startswith("## ") or line.startswith("### "):
            text = line.lstrip("#").strip()
            content.append([{"tag": "text", "text": text, "style": ["bold"]}])
            continue

        # 列表项
        if _re.match(r"^[-*]\s", line):
            text = line[2:].strip()
            content.append([{"tag": "text", "text": "• "}] + _inline(text))
            continue

        # 有序列表
        if _re.match(r"^\d+\.\s", line):
            text = _re.sub(r"^\d+\.\s", "", line)
            content.append(_inline(text))
            continue

        # 空行 → 空段落（间距）
        if not line.strip():
            continue

        # 普通段落
        content.append(_inline(line.strip()))

    # 飞书 post 内容不能为空
    if not content:
        content = [[{"tag": "text", "text": md[:500]}]]

    return {
        "zh_cn": {
            "title": title or "实验报告",
            "content": content,
        }
    }


def _split(text: str, max_chars: int = 1500) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks, remaining = [], text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, max_chars)
        if cut <= 0:
            cut = max_chars
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


def _multipart_post(token: str, url: str, fields: dict,
                    file_field: str, file_name: str, file_data: bytes) -> dict | None:
    boundary = f"----stargate{uuid4().hex}"
    body = bytearray()
    for k, v in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f'name="{k}"\r\n\r\n{v}\r\n').encode()
    safe = file_name.replace('"', "_")
    body += (f"--{boundary}\r\nContent-Disposition: form-data; "
             f'name="{file_field}"; filename="{safe}"\r\n'
             f"Content-Type: application/octet-stream\r\n\r\n").encode()
    body += file_data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=bytes(body), method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": f"multipart/form-data; boundary={boundary}"})
    return _json_request(req, label=f"feishu upload {file_field}")


# ── CLI ────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Stargate Feishu CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_send = sub.add_parser("send", help="发送文本消息")
    p_send.add_argument("text", nargs="+")

    p_file = sub.add_parser("send-file", help="发送文件")
    p_file.add_argument("path")
    p_file.add_argument("--caption", default="")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    cfg = load_feishu_config()
    if not cfg:
        print("[feishu] 飞书未配置或已禁用（检查 project.json feishu 字段）", file=sys.stderr)
        sys.exit(0)  # 静默退出，不影响实验流程

    notifier = FeishuNotifier(cfg["app_id"], cfg["app_secret"], cfg["chat_id"])

    if args.cmd == "send":
        text = " ".join(args.text)
        ok = notifier.send_message(text)
        sys.exit(0 if ok else 1)

    if args.cmd == "send-file":
        ok = notifier.send_file(args.path, caption=args.caption)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
