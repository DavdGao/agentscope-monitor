"""Test which Dingtalk @ identifier works in your group.

Usage:
    DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=..." \
    DINGTALK_SECRET="SEC..."   # optional, only if you enabled 加签 \
    python -m tests.at_test \
        --mobile 138xxxxxxxx \
        --staff-id 382563 \
        --ali-ding x0p_f72yv0sci

Each candidate is sent as a *separate* message so you can clearly see in
the group which one actually highlighted you / popped up a notification.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import dingtalk  # noqa: E402


def send_with_at(label: str, identifier: str, kind: str) -> None:
    """kind = 'mobile' or 'userid'"""
    keyword = "AgentScope"
    text = (
        f"### 🧪 {keyword} @ 测试 — {label}\n\n"
        f"**identifier**: `{identifier}`\n\n"
        f"**kind**: {kind}\n\n"
        f"如果你被 @ 高亮 + 收到推送通知 → ✅ 这个 ID 可用\n\n"
        f"---\n\n"
        f"@{identifier}"
    )
    title = f"AgentScope AT 测试 - {label}"

    if kind == "mobile":
        dingtalk.send_markdown(title=title, text=text, at_mobiles=[identifier])
    elif kind == "userid":
        # NOTE: dingtalk.send_markdown doesn't currently accept atUserIds;
        # we call the raw _post helper to inject it.
        from scripts.dingtalk import _ensure_keyword, _post
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": _ensure_keyword(title),
                "text": _ensure_keyword(text),
            },
            "at": {
                "atUserIds": [identifier],
                "isAtAll": False,
            },
        }
        _post(payload)
    else:
        raise ValueError(kind)
    print(f"[ok] sent {label} ({kind}={identifier})")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mobile", help="Mobile number, e.g. 13812345678")
    p.add_argument("--staff-id", help="Alibaba staff ID / 工号, e.g. 382563")
    p.add_argument("--ali-ding", help="阿里钉号, e.g. x0p_f72yv0sci")
    p.add_argument("--email-prefix", help="Email prefix, e.g. qianbingchen.qbc")
    args = p.parse_args()

    if not os.environ.get("DINGTALK_WEBHOOK"):
        print("[error] please set DINGTALK_WEBHOOK env var", file=sys.stderr)
        return 1

    tried = 0
    if args.mobile:
        send_with_at("手机号 (atMobiles)", args.mobile, "mobile")
        time.sleep(2)
        tried += 1
    if args.staff_id:
        send_with_at("工号 (atUserIds)", args.staff_id, "userid")
        time.sleep(2)
        tried += 1
    if args.ali_ding:
        send_with_at("阿里钉号 (atUserIds)", args.ali_ding, "userid")
        time.sleep(2)
        tried += 1
    if args.email_prefix:
        send_with_at("邮箱前缀 (atUserIds)", args.email_prefix, "userid")
        tried += 1

    if tried == 0:
        print("Nothing to test. Pass at least one of --mobile / --staff-id / --ali-ding / --email-prefix.")
        return 1

    print(f"\n[done] Sent {tried} test messages. Check the Dingtalk group:")
    print("  - Which message highlighted your name in blue?")
    print("  - Which message gave you a notification badge?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
