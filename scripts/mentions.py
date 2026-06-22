"""Resolve which Dingtalk mobiles to @ for a given event.

Currently a stub that returns []. The user will fill in:
  - rule-based: label / assignee / module-path mapping (config.py)
  - LLM-based:  pass payload to an LLM that picks the right owner

To wire in LLM routing later, override `resolve_mentions` (e.g. read an
env var like MENTIONS_BACKEND=llm and dispatch).
"""
from __future__ import annotations

from typing import Any

from .config import LABEL_OWNER_MAP, MODULE_OWNER_MAP, OWNER_MAP


def _by_labels(labels: list[str]) -> set[str]:
    users: set[str] = set()
    for label in labels:
        users.update(LABEL_OWNER_MAP.get(label, []))
    return users


def _by_assignees(assignees: list[str]) -> set[str]:
    return {u for u in assignees if u in OWNER_MAP}


def _by_modules(paths: list[str]) -> set[str]:
    users: set[str] = set()
    for path in paths:
        for prefix, owners in MODULE_OWNER_MAP.items():
            if path.startswith(prefix):
                users.update(owners)
    return users


def resolve_mentions(event: dict[str, Any]) -> list[str]:
    """Return a list of Dingtalk mobile numbers to @ for this event.

    For now this is rule-only (and the rule tables are empty by default,
    so the result is []). Hook a real router in here when ready.
    """
    candidates: set[str] = set()
    candidates |= _by_labels(event.get("labels", []) or [])
    candidates |= _by_assignees(event.get("assignees", []) or [])
    candidates |= _by_assignees(event.get("reviewers", []) or [])
    candidates |= _by_modules(event.get("changed_paths", []) or [])

    mobiles = [OWNER_MAP[u] for u in candidates if u in OWNER_MAP]
    return sorted(set(mobiles))
