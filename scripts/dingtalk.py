"""Dingtalk webhook client.

- Always injects the configured keyword (so "custom keyword" security passes).
- Optionally signs requests when DINGTALK_SECRET is set.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
from typing import Sequence

import requests

from .config import DINGTALK_KEYWORD


class DingtalkError(RuntimeError):
    pass


def _ensure_keyword(text: str) -> str:
    """The custom-keyword security rule rejects messages missing the keyword."""
    if DINGTALK_KEYWORD and DINGTALK_KEYWORD not in text:
        return f"[{DINGTALK_KEYWORD}] {text}"
    return text


def _signed_url(webhook: str, secret: str) -> str:
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(digest))
    sep = "&" if "?" in webhook else "?"
    return f"{webhook}{sep}timestamp={timestamp}&sign={sign}"


def _post(payload: dict) -> dict:
    webhook = os.environ.get("DINGTALK_WEBHOOK")
    if not webhook:
        raise DingtalkError("DINGTALK_WEBHOOK is not configured")

    secret = os.environ.get("DINGTALK_SECRET")
    url = _signed_url(webhook, secret) if secret else webhook

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=10,
            )
            data = resp.json()
            if data.get("errcode") == 0:
                return data
            # 310000 = signature failed; 410100 = keyword missing — don't retry
            if data.get("errcode") in (310000, 410100):
                raise DingtalkError(f"Dingtalk rejected: {data}")
            last_err = DingtalkError(f"Dingtalk error (attempt {attempt+1}): {data}")
        except (requests.RequestException, ValueError) as e:
            last_err = e
        time.sleep(1 + attempt)
    raise DingtalkError(f"Dingtalk send failed after retries: {last_err}")


def send_markdown(
    title: str,
    text: str,
    at_mobiles: Sequence[str] | None = None,
    at_all: bool = False,
) -> dict:
    title = _ensure_keyword(title)
    text = _ensure_keyword(text)
    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
        "at": {
            "atMobiles": list(at_mobiles or []),
            "isAtAll": bool(at_all),
        },
    }
    return _post(payload)


def send_text(
    content: str,
    at_mobiles: Sequence[str] | None = None,
    at_all: bool = False,
) -> dict:
    content = _ensure_keyword(content)
    payload = {
        "msgtype": "text",
        "text": {"content": content},
        "at": {
            "atMobiles": list(at_mobiles or []),
            "isAtAll": bool(at_all),
        },
    }
    return _post(payload)
