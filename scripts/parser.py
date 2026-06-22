"""Parse raw GitHub webhook payloads into a normalized event dict."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .config import ACTION_CN, EVENT_CN, EVENT_EMOJI


def _trim(text: str | None, n: int = 200) -> str:
    if not text:
        return ""
    text = text.strip().replace("\r\n", "\n")
    return text if len(text) <= n else text[:n] + "…"


def _base(event_name: str, payload: dict, repo: str) -> dict[str, Any]:
    action = payload.get("action", "") or ""
    return {
        "event_name": event_name,
        "event_cn": EVENT_CN.get(event_name, event_name),
        "emoji": EVENT_EMOJI.get(event_name, "🔔"),
        "action": action,
        "action_cn": ACTION_CN.get(action, action),
        "sender": (payload.get("sender") or {}).get("login", "unknown"),
        "repo": repo,
        "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        # placeholders, filled below
        "title": "",
        "url": "",
        "number": None,
        "body": "",
        "labels": [],
        "assignees": [],
        "reviewers": [],
        "changed_paths": [],
        "extra": {},
    }


def parse_event(event_name: str, payload: dict, repo: str) -> dict[str, Any] | None:
    """Return a structured event dict, or None if the event should be ignored."""
    out = _base(event_name, payload, repo)

    if event_name == "issues":
        issue = payload.get("issue") or {}
        out["title"] = issue.get("title", "")
        out["url"] = issue.get("html_url", "")
        out["number"] = issue.get("number")
        out["body"] = _trim(issue.get("body"))
        out["labels"] = [l.get("name") for l in (issue.get("labels") or []) if l.get("name")]
        out["assignees"] = [a.get("login") for a in (issue.get("assignees") or []) if a.get("login")]
        out["extra"] = {"state": issue.get("state"), "author": (issue.get("user") or {}).get("login")}

    elif event_name == "issue_comment":
        issue = payload.get("issue") or {}
        comment = payload.get("comment") or {}
        out["title"] = issue.get("title", "")
        out["url"] = comment.get("html_url") or issue.get("html_url", "")
        out["number"] = issue.get("number")
        out["body"] = _trim(comment.get("body"))
        # `issue` includes pull_request key when it's actually a PR comment
        out["extra"] = {
            "is_pr": "pull_request" in issue,
            "author": (issue.get("user") or {}).get("login"),
            "commenter": (comment.get("user") or {}).get("login"),
        }

    elif event_name == "pull_request":
        pr = payload.get("pull_request") or {}
        out["title"] = pr.get("title", "")
        out["url"] = pr.get("html_url", "")
        out["number"] = pr.get("number")
        out["body"] = _trim(pr.get("body"))
        out["labels"] = [l.get("name") for l in (pr.get("labels") or []) if l.get("name")]
        out["reviewers"] = [r.get("login") for r in (pr.get("requested_reviewers") or []) if r.get("login")]
        out["assignees"] = [a.get("login") for a in (pr.get("assignees") or []) if a.get("login")]
        out["extra"] = {
            "state": pr.get("state"),
            "merged": pr.get("merged", False),
            "draft": pr.get("draft", False),
            "author": (pr.get("user") or {}).get("login"),
            "head_sha": (pr.get("head") or {}).get("sha"),
            "base_ref": (pr.get("base") or {}).get("ref"),
            "additions": pr.get("additions"),
            "deletions": pr.get("deletions"),
            "changed_files": pr.get("changed_files"),
        }

    elif event_name == "pull_request_review":
        pr = payload.get("pull_request") or {}
        review = payload.get("review") or {}
        out["title"] = pr.get("title", "")
        out["url"] = review.get("html_url") or pr.get("html_url", "")
        out["number"] = pr.get("number")
        out["body"] = _trim(review.get("body"))
        out["extra"] = {
            "review_state": review.get("state"),
            "reviewer": (review.get("user") or {}).get("login"),
            "pr_author": (pr.get("user") or {}).get("login"),
        }

    elif event_name == "pull_request_review_comment":
        pr = payload.get("pull_request") or {}
        comment = payload.get("comment") or {}
        out["title"] = pr.get("title", "")
        out["url"] = comment.get("html_url") or pr.get("html_url", "")
        out["number"] = pr.get("number")
        out["body"] = _trim(comment.get("body"))
        out["extra"] = {
            "path": comment.get("path"),
            "commenter": (comment.get("user") or {}).get("login"),
            "pr_author": (pr.get("user") or {}).get("login"),
        }
        if comment.get("path"):
            out["changed_paths"] = [comment["path"]]

    elif event_name == "discussion":
        d = payload.get("discussion") or {}
        out["title"] = d.get("title", "")
        out["url"] = d.get("html_url", "")
        out["number"] = d.get("number")
        out["body"] = _trim(d.get("body"))
        out["extra"] = {
            "category": (d.get("category") or {}).get("name"),
            "author": (d.get("user") or {}).get("login"),
        }

    elif event_name == "discussion_comment":
        d = payload.get("discussion") or {}
        comment = payload.get("comment") or {}
        out["title"] = d.get("title", "")
        out["url"] = comment.get("html_url") or d.get("html_url", "")
        out["number"] = d.get("number")
        out["body"] = _trim(comment.get("body"))
        out["extra"] = {
            "commenter": (comment.get("user") or {}).get("login"),
            "discussion_author": (d.get("user") or {}).get("login"),
        }

    elif event_name == "push":
        head = payload.get("head_commit") or {}
        commits = payload.get("commits") or []
        ref = payload.get("ref", "") or ""
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
        out["title"] = _trim(head.get("message"), 80)
        out["url"] = head.get("url", "") or payload.get("compare", "")
        out["body"] = ""
        changed: set[str] = set()
        for c in commits:
            changed.update(c.get("added") or [])
            changed.update(c.get("modified") or [])
            changed.update(c.get("removed") or [])
        out["changed_paths"] = sorted(changed)
        out["extra"] = {
            "branch": branch,
            "commit_count": len(commits),
            "before": payload.get("before"),
            "after": payload.get("after"),
            "forced": payload.get("forced", False),
            "head_author": (head.get("author") or {}).get("username")
                          or (head.get("author") or {}).get("name"),
        }

    else:
        return None

    return out
