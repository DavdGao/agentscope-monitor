"""Write event records into the storage repo via the GitHub Contents API.

We use the API instead of `git push` so concurrent workflow runs cannot
collide on a shared branch. Each event is written to its own file path
under `data/YYYY-MM-DD/`.
"""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from typing import Any

import requests

from .config import STORAGE_REPO, TIMEZONE, require_env

API_ROOT = "https://api.github.com"


def _headers() -> dict[str, str]:
    token = require_env("STORAGE_REPO_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _file_path(event_id: str, ts: datetime) -> str:
    day = ts.astimezone(TIMEZONE).strftime("%Y-%m-%d")
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in event_id)
    return f"data/{day}/{safe}.json"


def _get_sha_if_exists(path: str) -> str | None:
    url = f"{API_ROOT}/repos/{STORAGE_REPO}/contents/{path}"
    resp = requests.get(url, headers=_headers(), timeout=15)
    if resp.status_code == 200:
        return resp.json().get("sha")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return None


def save_event(event: dict[str, Any], event_id: str) -> str:
    """Upload one event JSON to the storage repo. Returns committed path."""
    ts = datetime.fromisoformat(event["time"].replace("Z", "+00:00"))
    path = _file_path(event_id, ts)

    body = json.dumps(event, ensure_ascii=False, indent=2).encode("utf-8")
    payload = {
        "message": f"event: {event.get('event_name')} {event.get('action','')} ({event_id})",
        "content": base64.b64encode(body).decode("ascii"),
        "committer": {
            "name": "agentscope-monitor-bot",
            "email": "bot@users.noreply.github.com",
        },
    }
    existing_sha = _get_sha_if_exists(path)
    if existing_sha:
        payload["sha"] = existing_sha

    url = f"{API_ROOT}/repos/{STORAGE_REPO}/contents/{path}"
    resp = requests.put(url, headers=_headers(), json=payload, timeout=20)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to store event ({resp.status_code}): {resp.text}"
        )
    return path


def list_events_for_day(day: str) -> list[dict[str, Any]]:
    """Read all event JSONs for a given YYYY-MM-DD from the storage repo.

    Used by the daily summary, which runs inside the storage repo itself —
    so it reads from the local checkout when available, falling back to API.
    """
    from pathlib import Path

    local = Path("data") / day
    records: list[dict[str, Any]] = []
    if local.exists():
        for fp in sorted(local.glob("*.json")):
            try:
                records.append(json.loads(fp.read_text("utf-8")))
            except (OSError, json.JSONDecodeError) as e:
                print(f"[warn] skipping {fp}: {e}")
        return records

    # Fallback: pull via API (rare — only when run outside checkout).
    url = f"{API_ROOT}/repos/{STORAGE_REPO}/contents/data/{day}"
    resp = requests.get(url, headers=_headers(), timeout=15)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    for item in resp.json():
        if item["type"] != "file":
            continue
        f_resp = requests.get(item["download_url"], timeout=15)
        f_resp.raise_for_status()
        try:
            records.append(f_resp.json())
        except ValueError:
            pass
    return records
