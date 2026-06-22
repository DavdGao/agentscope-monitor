"""Centralized configuration for the AgentScope GitHub monitor."""
from __future__ import annotations

import os
from zoneinfo import ZoneInfo

# ─── Repos ──────────────────────────────────────────────────────────────────
# The monitored upstream repo (informational, used in messages).
MONITORED_REPO = "agentscope-ai/agentscope"

# The private storage repo that holds raw events + workflows.
STORAGE_REPO = os.environ.get("STORAGE_REPO", "DavdGao/agentscope-monitor")

# ─── Time ───────────────────────────────────────────────────────────────────
# All "today / yesterday" calculations use Beijing time.
TIMEZONE = ZoneInfo("Asia/Shanghai")

# ─── Dingtalk ───────────────────────────────────────────────────────────────
# Keyword that MUST appear in every Dingtalk message (matches the bot's
# "custom keyword" security setting). Sending will fail otherwise.
DINGTALK_KEYWORD = "AgentScope"

# ─── Event filtering ────────────────────────────────────────────────────────
WATCHED_EVENTS = {
    "issues",
    "issue_comment",
    "pull_request",
    "pull_request_review",
    "pull_request_review_comment",
    "discussion",
    "discussion_comment",
    "push",
}

EVENT_EMOJI = {
    "issues": "📋",
    "issue_comment": "💬",
    "pull_request": "🔀",
    "pull_request_review": "👀",
    "pull_request_review_comment": "💭",
    "discussion": "🗣️",
    "discussion_comment": "💬",
    "push": "📦",
}

EVENT_CN = {
    "issues": "Issue",
    "issue_comment": "Issue 评论",
    "pull_request": "Pull Request",
    "pull_request_review": "PR 审核",
    "pull_request_review_comment": "PR 行评论",
    "discussion": "Discussion",
    "discussion_comment": "Discussion 评论",
    "push": "Push",
}

ACTION_CN = {
    "opened": "新建",
    "closed": "关闭",
    "reopened": "重新打开",
    "edited": "编辑",
    "deleted": "删除",
    "created": "新建",
    "submitted": "提交",
    "synchronize": "更新提交",
    "review_requested": "请求审核",
    "ready_for_review": "标记可审核",
    "answered": "已解答",
    "assigned": "指派",
    "unassigned": "取消指派",
    "labeled": "添加标签",
    "unlabeled": "移除标签",
    "approved": "已批准",
    "changes_requested": "请求修改",
    "commented": "评论",
}

# ─── @ Mention configuration (placeholders — user fills later) ──────────────
# GitHub username -> Dingtalk mobile number.
OWNER_MAP: dict[str, str] = {
    # "alice": "13800000000",
}

# Issue/PR label -> list of GitHub usernames.
LABEL_OWNER_MAP: dict[str, list[str]] = {
    # "bug": ["alice"],
    # "urgent": ["alice", "bob"],
}

# Module/path -> list of GitHub usernames (used by future LLM router).
MODULE_OWNER_MAP: dict[str, list[str]] = {
    # "src/agentscope/agents/": ["alice"],
}

# ─── Environment helpers ────────────────────────────────────────────────────
def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val
