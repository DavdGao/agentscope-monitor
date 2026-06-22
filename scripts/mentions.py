"""Resolve which Dingtalk mobiles to @ for a given event or summary.

Two entry points:
  - resolve_mentions(event)            → realtime per-event @
  - resolve_on_call_mobiles(day)       → weekly rotation for 10:00 summary

Both ultimately return a list of mobile numbers (the only thing that
actually triggers @ in a self-built robot group).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .config import (
    LABEL_OWNER_MAP,
    MODULE_OWNER_MAP,
    OWNER_MAP,
    TIMEZONE,
    WEEKDAY_ON_CALL,
)


def _nicknames_to_mobiles(nicks) -> list[str]:
    seen: list[str] = []
    for n in nicks:
        m = OWNER_MAP.get(n)
        if m and m not in seen:
            seen.append(m)
    return seen


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
    """Return mobile numbers to @ for a realtime event notification."""
    candidates: set[str] = set()
    candidates |= _by_labels(event.get("labels", []) or [])
    candidates |= _by_assignees(event.get("assignees", []) or [])
    candidates |= _by_assignees(event.get("reviewers", []) or [])
    candidates |= _by_modules(event.get("changed_paths", []) or [])
    return _nicknames_to_mobiles(sorted(candidates))


def resolve_on_call_mobiles(target_day: str | date | None = None) -> list[str]:
    """Return the on-call mobiles for the given day's 10:00 summary.

    `target_day` is the day the summary is *about* (i.e. yesterday at 10:00).
    The rotation lookup uses the weekday of that day, so Monday's report
    (published Tuesday 10:00) hits WEEKDAY_ON_CALL[0]... wait, no — the
    user wants "the 10:00 run on Mon/Wed/Fri @ group A". The published-on
    weekday matters, not the data weekday. We therefore key on TODAY's
    weekday in TIMEZONE, regardless of what date the data is about.
    """
    today = datetime.now(TIMEZONE).date()
    weekday = today.weekday()  # 0 = Monday
    nicks = WEEKDAY_ON_CALL.get(weekday, []) or []
    return _nicknames_to_mobiles(nicks)
