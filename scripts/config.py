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
}

# (event_name, action) tuples that are STORED to the repo but NOT sent
# to Dingtalk in real time. Used to keep raw data for the daily digest
# while avoiding noisy chat messages.
SILENT_REALTIME_EVENTS: set[tuple[str, str]] = {
    ("pull_request", "synchronize"),   # author pushed new commits — daily summary handles it
}

EVENT_EMOJI = {
    "issues": "📋",
    "issue_comment": "💬",
    "pull_request": "🔀",
    "pull_request_review": "👀",
    "pull_request_review_comment": "💭",
    "discussion": "🗣️",
    "discussion_comment": "💬",
}

EVENT_CN = {
    "issues": "Issue",
    "issue_comment": "Issue 评论",
    "pull_request": "Pull Request",
    "pull_request_review": "PR 审核",
    "pull_request_review_comment": "PR 行评论",
    "discussion": "Discussion",
    "discussion_comment": "Discussion 评论",
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

# ─── @ Mention configuration ────────────────────────────────────────────────
# Fill these in to enable real @ in the Dingtalk group.
# IMPORTANT: only mobile numbers really trigger a Dingtalk push notification
# in a普通群 / 自定义机器人. atUserIds / 阿里钉号 / 邮箱前缀 都不行（只是文本渲染）.

# Nickname → Dingtalk-registered mobile number.
# The nickname is just a key you'll reference in the rotation tables below.
OWNER_MAP: dict[str, str] = {
    # "dawei":      "13800000000",
    # "chenguan":   "13800000001",
}

# Weekly on-call rotation for the 10:00 (yesterday) daily summary.
# Key: Python weekday (0 = Monday ... 6 = Sunday).
# Value: list of nicknames from OWNER_MAP to @ in that day's summary.
# Empty list → no one is @-ed that day.
WEEKDAY_ON_CALL: dict[int, list[str]] = {
    0: [],   # Mon  周一  ─ fill with names from OWNER_MAP, e.g. ["dawei"]
    1: [],   # Tue  周二
    2: [],   # Wed  周三
    3: [],   # Thu  周四
    4: [],   # Fri  周五
    5: [],   # Sat  周六
    6: [],   # Sun  周日 (typically empty)
}

# Issue/PR label → list of nicknames. Used by realtime mentions.resolve_mentions.
LABEL_OWNER_MAP: dict[str, list[str]] = {
    # "bug": ["dawei"],
    # "urgent": ["dawei", "chenguan"],
}

# Module path prefix → list of nicknames. Hook for the future LLM router.
MODULE_OWNER_MAP: dict[str, list[str]] = {
    # "src/agentscope/agents/": ["dawei"],
}

# ─── Environment helpers ────────────────────────────────────────────────────
def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val
