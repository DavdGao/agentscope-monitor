"""Smoke tests for parser + summary using mock webhook payloads.

Run: python -m tests.test_pipeline
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.parser import parse_event
from scripts.summary import _bucket, build_markdown


REPO = "agentscope-ai/agentscope"

ISSUE_OPENED = {
    "action": "opened",
    "sender": {"login": "alice"},
    "issue": {
        "number": 42,
        "title": "Bug: agent crashes on empty input",
        "html_url": "https://github.com/agentscope-ai/agentscope/issues/42",
        "body": "Steps to reproduce…",
        "labels": [{"name": "bug"}, {"name": "urgent"}],
        "assignees": [{"login": "bob"}],
        "user": {"login": "alice"},
        "state": "open",
    },
}

ISSUE_COMMENT = {
    "action": "created",
    "sender": {"login": "carol"},
    "issue": {
        "number": 42,
        "title": "Bug: agent crashes on empty input",
        "html_url": "https://github.com/agentscope-ai/agentscope/issues/42",
        "user": {"login": "alice"},
    },
    "comment": {
        "body": "I can repro this.",
        "html_url": "https://github.com/agentscope-ai/agentscope/issues/42#issuecomment-1",
        "user": {"login": "carol"},
    },
}

PR_OPENED = {
    "action": "opened",
    "sender": {"login": "dave"},
    "pull_request": {
        "number": 100,
        "title": "Add caching layer",
        "html_url": "https://github.com/agentscope-ai/agentscope/pull/100",
        "body": "Implements LRU cache for tool calls.",
        "labels": [{"name": "enhancement"}],
        "requested_reviewers": [{"login": "alice"}],
        "assignees": [],
        "user": {"login": "dave"},
        "state": "open",
        "merged": False,
        "draft": False,
        "head": {"sha": "deadbeef"},
        "base": {"ref": "main"},
        "additions": 100, "deletions": 5, "changed_files": 3,
    },
}

PR_SYNC = {
    "action": "synchronize",
    "sender": {"login": "dave"},
    "pull_request": {
        "number": 100,
        "title": "Add caching layer",
        "html_url": "https://github.com/agentscope-ai/agentscope/pull/100",
        "body": "...",
        "labels": [],
        "requested_reviewers": [],
        "assignees": [],
        "user": {"login": "dave"},
        "state": "open", "merged": False, "draft": False,
        "head": {"sha": "cafef00d"}, "base": {"ref": "main"},
    },
}

PR_REVIEW = {
    "action": "submitted",
    "sender": {"login": "alice"},
    "pull_request": {
        "number": 100,
        "title": "Add caching layer",
        "html_url": "https://github.com/agentscope-ai/agentscope/pull/100",
        "user": {"login": "dave"},
    },
    "review": {
        "state": "approved",
        "body": "LGTM",
        "html_url": "https://github.com/agentscope-ai/agentscope/pull/100#review-1",
        "user": {"login": "alice"},
    },
}

DISCUSSION_CREATED = {
    "action": "created",
    "sender": {"login": "eve"},
    "discussion": {
        "number": 7,
        "title": "How to extend agents?",
        "html_url": "https://github.com/agentscope-ai/agentscope/discussions/7",
        "body": "Question about extension points.",
        "category": {"name": "Q&A"},
        "user": {"login": "eve"},
    },
}

DISCUSSION_COMMENT = {
    "action": "created",
    "sender": {"login": "frank"},
    "discussion": {
        "number": 7,
        "title": "How to extend agents?",
        "html_url": "https://github.com/agentscope-ai/agentscope/discussions/7",
        "user": {"login": "eve"},
    },
    "comment": {
        "body": "See the docs section X.",
        "html_url": "https://github.com/agentscope-ai/agentscope/discussions/7#comment-1",
        "user": {"login": "frank"},
    },
}

PUSH = {
    "sender": {"login": "dave"},
    "ref": "refs/heads/main",
    "before": "0" * 40,
    "after": "abc" + "0" * 37,
    "head_commit": {
        "message": "fix: handle empty tool output",
        "url": "https://github.com/agentscope-ai/agentscope/commit/abc",
        "author": {"username": "dave", "name": "Dave"},
    },
    "commits": [
        {"added": ["src/x.py"], "modified": ["src/y.py"], "removed": []},
    ],
    "compare": "https://github.com/agentscope-ai/agentscope/compare/aaa...bbb",
    "forced": False,
}

CASES = [
    ("issues", ISSUE_OPENED),
    ("issue_comment", ISSUE_COMMENT),
    ("pull_request", PR_OPENED),
    ("pull_request", PR_SYNC),
    ("pull_request_review", PR_REVIEW),
    ("discussion", DISCUSSION_CREATED),
    ("discussion_comment", DISCUSSION_COMMENT),
    ("push", PUSH),
]


def test_parser():
    print("=" * 60)
    print("PARSER OUTPUTS")
    print("=" * 60)
    parsed = []
    for name, payload in CASES:
        ev = parse_event(name, payload, REPO)
        assert ev is not None, f"parser returned None for {name}"
        parsed.append(ev)
        print(f"\n--- {name} / {ev['action']} ---")
        print(json.dumps(ev, ensure_ascii=False, indent=2))
    return parsed


def test_summary(parsed):
    print("\n" + "=" * 60)
    print("SUMMARY OUTPUT")
    print("=" * 60)
    buckets = _bucket(parsed)
    title, text = build_markdown("2026-06-21", buckets)
    print(title)
    print()
    print(text)

    # sanity checks
    assert len(buckets["new_issues"]) == 1
    assert len(buckets["new_prs"]) == 1
    assert len(buckets["new_discussions"]) == 1
    assert len(buckets["pr_new_commits"]) == 1
    # 1 issue_comment + 1 pr_review + 1 discussion_comment = 3 comment entries
    assert sum(buckets["comment_counts"].values()) == 3
    print("\n[ok] all summary assertions passed")


if __name__ == "__main__":
    parsed = test_parser()
    test_summary(parsed)
