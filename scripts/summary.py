"""Generate yesterday's digest and send it to Dingtalk.

Aggregation rules (per user's request):
  1) Newly created issues / PRs / discussions
  2) New comment activity (which issues/PRs/discussions got comments)
  3) PRs with new commits (synchronize) — flagged as "needs re-review"
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from . import dingtalk
from .config import MONITORED_REPO, TIMEZONE
from .mentions import resolve_on_call_mobiles
from .storage import list_events_for_day


def _today_str() -> str:
    return datetime.now(TIMEZONE).date().strftime("%Y-%m-%d")


def _yesterday_str() -> str:
    today = datetime.now(TIMEZONE).date()
    return (today - timedelta(days=1)).strftime("%Y-%m-%d")


def _resolve_day_and_label() -> tuple[str, str]:
    """Return (YYYY-MM-DD, human-readable label) based on env vars."""
    explicit = os.environ.get("REPORT_DAY", "").strip()
    if explicit:
        return explicit, explicit

    scope = (os.environ.get("REPORT_SCOPE") or "yesterday").strip().lower()
    if scope == "today":
        day = _today_str()
        return day, f"{day}（今日截至 {datetime.now(TIMEZONE).strftime('%H:%M')}）"
    # default
    day = _yesterday_str()
    return day, f"{day}（昨日）"


def _bucket(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Group events into the buckets needed for the digest."""
    new_issues: list[dict] = []
    new_prs: list[dict] = []
    new_discussions: list[dict] = []

    comment_counts: dict[tuple[str, int, str, str], int] = defaultdict(int)
    pr_new_commits: dict[int, dict] = {}

    for e in events:
        name = e.get("event_name")
        action = e.get("action")
        num = e.get("number")
        title = e.get("title") or ""
        url = e.get("url") or ""

        if name == "issues" and action == "opened":
            new_issues.append({"number": num, "title": title, "url": url, "author": (e.get("extra") or {}).get("author")})
        elif name == "pull_request" and action == "opened":
            new_prs.append({"number": num, "title": title, "url": url, "author": (e.get("extra") or {}).get("author")})
        elif name == "discussion" and action == "created":
            new_discussions.append({"number": num, "title": title, "url": url, "author": (e.get("extra") or {}).get("author")})

        # comment activity
        if name in ("issue_comment", "pull_request_review_comment", "discussion_comment", "pull_request_review") and action in ("created", "submitted"):
            if num is None:
                continue
            kind = {
                "issue_comment": "issue",
                "pull_request_review_comment": "pr",
                "pull_request_review": "pr",
                "discussion_comment": "discussion",
            }[name]
            # issue_comment on PRs: parser sets extra.is_pr
            if name == "issue_comment" and (e.get("extra") or {}).get("is_pr"):
                kind = "pr"
            key = (kind, num, title, url)
            comment_counts[key] += 1

        # PR synchronize = new commits pushed
        if name == "pull_request" and action == "synchronize" and num is not None:
            pr_new_commits[num] = {
                "number": num,
                "title": title,
                "url": url,
                "author": (e.get("extra") or {}).get("author"),
            }

    return {
        "new_issues": new_issues,
        "new_prs": new_prs,
        "new_discussions": new_discussions,
        "comment_counts": comment_counts,
        "pr_new_commits": list(pr_new_commits.values()),
    }


def _section(title: str, items: list[str]) -> str:
    if not items:
        return f"### {title}\n_无_"
    body = "\n".join(f"- {it}" for it in items)
    return f"### {title}（{len(items)}）\n{body}"


def _format_item(it: dict) -> str:
    num = it.get("number")
    title = it.get("title") or ""
    url = it.get("url") or ""
    author = it.get("author") or ""
    head = f"#{num} [{title}]({url})" if url else f"#{num} {title}"
    if author:
        head += f" — `@{author}`"
    return head


def _format_comment_group(comment_counts: dict[tuple[str, int, str, str], int], kind: str) -> list[str]:
    rows: list[tuple[int, str]] = []
    for (k, num, title, url), n in comment_counts.items():
        if k != kind:
            continue
        head = f"#{num} [{title}]({url})" if url else f"#{num} {title}"
        rows.append((n, f"{head} — **{n}** 条新评论"))
    rows.sort(key=lambda r: -r[0])
    return [r[1] for r in rows]


def build_markdown(label: str, buckets: dict[str, Any]) -> tuple[str, str]:
    title = f"📊 {MONITORED_REPO} 日报 · {label}"

    sections: list[str] = [f"## 📊 GitHub 监控日报 · {label}", f"**仓库**：`{MONITORED_REPO}`", ""]

    # 1. 新建
    sections.append("---")
    sections.append("## 1️⃣ 新建")
    sections.append(_section("🆕 新 Issue", [_format_item(it) for it in buckets["new_issues"]]))
    sections.append(_section("🔀 新 Pull Request", [_format_item(it) for it in buckets["new_prs"]]))
    sections.append(_section("🗣️ 新 Discussion", [_format_item(it) for it in buckets["new_discussions"]]))

    # 2. 留言
    sections.append("---")
    sections.append("## 2️⃣ 新留言情况")
    sections.append(_section("💬 Issue 留言", _format_comment_group(buckets["comment_counts"], "issue")))
    sections.append(_section("💭 PR 留言/审核", _format_comment_group(buckets["comment_counts"], "pr")))
    sections.append(_section("💬 Discussion 留言", _format_comment_group(buckets["comment_counts"], "discussion")))

    # 3. 需要 review 的 PR
    sections.append("---")
    sections.append("## 3️⃣ PR 有新提交 · 待 review")
    sections.append(_section("🔁 同步了新 commit 的 PR", [_format_item(it) for it in buckets["pr_new_commits"]]))

    text = "\n\n".join(sections)
    return title, text


def main() -> int:
    day, label = _resolve_day_and_label()
    events = list_events_for_day(day)
    print(f"[info] loaded {len(events)} events for {day} (label={label})")

    buckets = _bucket(events)
    title, text = build_markdown(label, buckets)

    # Only the "yesterday" run (10:00 Beijing) participates in the rotation.
    # The 16:00 today-so-far run never @ anyone.
    scope = (os.environ.get("REPORT_SCOPE") or "yesterday").strip().lower()
    explicit = os.environ.get("REPORT_DAY", "").strip()
    at_mobiles: list[str] = []
    if scope == "yesterday" and not explicit:
        at_mobiles = resolve_on_call_mobiles()
        if at_mobiles:
            print(f"[info] on-call @ list for today: {at_mobiles}")
        else:
            print("[info] no on-call entry for today's weekday")

    if os.environ.get("DRY_RUN") == "1":
        print(title)
        print(text)
        if at_mobiles:
            print(f"\n[dry-run] would @ {at_mobiles}")
        return 0

    try:
        dingtalk.send_markdown(title=title, text=text, at_mobiles=at_mobiles)
        print("[ok] daily summary sent")
    except Exception as e:
        print(f"[error] failed to send daily summary: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
