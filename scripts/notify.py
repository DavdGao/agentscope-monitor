"""Entry point invoked from the monitored repo's GitHub Actions workflow.

Reads the raw webhook payload from environment variables, normalizes it,
persists it to the storage repo, and sends a real-time Dingtalk message.
"""
from __future__ import annotations

import json
import os
import sys

from . import dingtalk
from .config import WATCHED_EVENTS, require_env
from .mentions import resolve_mentions
from .parser import parse_event
from .storage import save_event


def _build_event_id(event_name: str) -> str:
    run_id = os.environ.get("RUN_ID", "manual")
    attempt = os.environ.get("RUN_ATTEMPT", "1")
    return f"{event_name}-{run_id}-{attempt}"


def _render_markdown(event: dict) -> tuple[str, str]:
    emoji = event["emoji"]
    event_cn = event["event_cn"]
    action_cn = event["action_cn"]
    repo = event["repo"]
    sender = event["sender"]
    title = event.get("title", "")
    url = event.get("url", "")
    body = event.get("body", "")
    labels = event.get("labels", []) or []
    extra = event.get("extra", {}) or {}

    header = f"### {emoji} [{repo}] {event_cn} · {action_cn or '事件'}"
    lines: list[str] = [header]

    if title:
        lines.append(f"**标题**：[{title}]({url})" if url else f"**标题**：{title}")
    if event.get("number") is not None:
        lines.append(f"**编号**：#{event['number']}")
    lines.append(f"**操作人**：`{sender}`")
    if labels:
        lines.append(f"**标签**：{', '.join(labels)}")

    # event-specific extras
    if event["event_name"] == "pull_request":
        flags = []
        if extra.get("draft"):
            flags.append("draft")
        if extra.get("merged"):
            flags.append("merged")
        if flags:
            lines.append(f"**状态**：{', '.join(flags)}")
    elif event["event_name"] == "pull_request_review":
        if extra.get("review_state"):
            lines.append(f"**审核结论**：{extra['review_state']}")
    elif event["event_name"] == "push":
        if extra.get("branch"):
            lines.append(f"**分支**：{extra['branch']}（{extra.get('commit_count', 0)} commits）")
    elif event["event_name"] == "discussion":
        if extra.get("category"):
            lines.append(f"**分类**：{extra['category']}")

    if body:
        lines.append(f"\n> {body}")

    text = "\n\n".join(lines)
    title_line = f"{emoji} {repo} · {event_cn}"
    return title_line, text


def main() -> int:
    event_name = require_env("EVENT_NAME")
    repo = require_env("REPO_NAME")
    raw_payload = require_env("EVENT_PAYLOAD")
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        print(f"[error] EVENT_PAYLOAD is not valid JSON: {e}", file=sys.stderr)
        return 1

    if event_name not in WATCHED_EVENTS:
        print(f"[skip] event {event_name} not in watched list")
        return 0

    event = parse_event(event_name, payload, repo)
    if event is None:
        print(f"[skip] parser returned None for {event_name}")
        return 0

    event["at_mobiles"] = resolve_mentions(event)
    event_id = _build_event_id(event_name)

    # 1) persist (best-effort: even if storage fails we still try to notify)
    storage_error: Exception | None = None
    try:
        path = save_event(event, event_id)
        print(f"[ok] stored at {path}")
    except Exception as e:
        storage_error = e
        print(f"[warn] failed to store event: {e}", file=sys.stderr)

    # 2) notify
    title, text = _render_markdown(event)
    try:
        dingtalk.send_markdown(title=title, text=text, at_mobiles=event["at_mobiles"])
        print("[ok] dingtalk sent")
    except Exception as e:
        print(f"[error] dingtalk send failed: {e}", file=sys.stderr)
        return 2

    if storage_error is not None:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
