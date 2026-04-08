#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

SITE_URL = "https://www.trumpstruth.org/"
STATE_PATH = Path(__file__).resolve().parent.parent / "memory" / "trump-truth-state.json"
ET = ZoneInfo("America/New_York")
TW = ZoneInfo("Asia/Taipei")
CRITICAL_KEYWORDS = [
    "iran",
    "israel",
    "war",
    "attack",
    "strike",
    "bomb",
    "ceasefire",
    "nuclear",
    "hormuz",
    "china",
    "taiwan",
]
ECONOMIC_KEYWORDS = [
    "tariff",
    "sanction",
    "oil",
    "fed",
    "powell",
    "market",
    "stock",
    "recession",
    "inflation",
    "dollar",
]
IGNORE_HINTS = [
    "endorse",
    "endorsement",
    "vote",
    "senate district",
    "governor",
    "congress",
    "republican primary",
]


def curl_text(url: str) -> str:
    return subprocess.check_output(
        ["curl", "-A", "Mozilla/5.0", "-fsSL", "--max-time", "20", url],
        text=True,
    )


def clean_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>\s*<p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_posts(limit: int = 12) -> list[dict]:
    html = curl_text(SITE_URL)
    pattern = re.compile(
        r'<div class="status"\s+data-status-url="(?P<archive>[^"]+)".*?'
        r'<a href="(?P<archive_link>https://www\.trumpstruth\.org/statuses/(?P<archive_id>\d+))" class="status-info__meta-item">(?P<posted_at>[^<]+)</a>.*?'
        r'<a href="(?P<original>https://truthsocial\.com/@realDonaldTrump/(?P<truth_id>\d+))"[^>]*>.*?</a>.*?'
        r'<div class="status__content">(?P<content>.*?)</div>',
        re.S,
    )
    posts = []
    for match in pattern.finditer(html):
        posted_at_raw = clean_html(match.group("posted_at"))
        try:
            posted_at = datetime.strptime(posted_at_raw, "%B %d, %Y, %I:%M %p").replace(tzinfo=ET)
        except ValueError:
            continue
        content = clean_html(match.group("content"))
        posts.append(
            {
                "archive_id": match.group("archive_id"),
                "truth_id": match.group("truth_id"),
                "posted_at_et": posted_at.isoformat(),
                "posted_at_tw": posted_at.astimezone(TW).isoformat(),
                "archive_link": match.group("archive_link"),
                "original_link": match.group("original"),
                "content": content,
            }
        )
        if len(posts) >= limit:
            break
    return posts


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def is_important(post: dict) -> bool:
    text = post["content"].lower()
    if any(hint in text for hint in IGNORE_HINTS):
        return False
    critical_hits = sum(keyword in text for keyword in CRITICAL_KEYWORDS)
    economic_hits = sum(keyword in text for keyword in ECONOMIC_KEYWORDS)
    return critical_hits >= 1 or economic_hits >= 2


def render_post(post: dict) -> str:
    preview = post["content"].strip()
    if len(preview) > 500:
        preview = preview[:500].rstrip() + "..."
    return (
        f"時間: {post['posted_at_tw']}\n"
        f"內容:\n{preview}\n"
        f"原文: {post['original_link']}\n"
        f"存檔: {post['archive_link']}"
    )


def cmd_digest(hours: int, limit: int) -> int:
    posts = fetch_posts(limit=max(limit, 12))
    cutoff = datetime.now(TW) - timedelta(hours=hours)
    recent = [p for p in posts if datetime.fromisoformat(p["posted_at_tw"]) >= cutoff]
    if not recent:
        print("NO_REPLY")
        return 0
    print(f"過去 {hours} 小時內川普 Truth Social 重點原文，共 {len(recent)} 則")
    for idx, post in enumerate(recent[:limit], start=1):
        print(f"\n[{idx}]\n{render_post(post)}")
    return 0


def cmd_alerts(limit: int) -> int:
    posts = fetch_posts(limit=max(limit, 12))
    state = load_state()
    seen_ids = set(state.get("alerted_truth_ids", []))
    new_important = [p for p in posts if p["truth_id"] not in seen_ids and is_important(p)]
    if not new_important:
        print("NO_REPLY")
        return 0
    new_important.sort(key=lambda p: p["posted_at_tw"])
    print(f"偵測到 {len(new_important)} 則川普重大貼文")
    for idx, post in enumerate(new_important[:limit], start=1):
        print(f"\n[{idx}]\n{render_post(post)}")
    updated_ids = list({*seen_ids, *(p["truth_id"] for p in new_important)})
    save_state({"alerted_truth_ids": updated_ids[-200:]})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    digest = sub.add_parser("digest")
    digest.add_argument("--hours", type=int, default=24)
    digest.add_argument("--limit", type=int, default=6)

    alerts = sub.add_parser("alerts")
    alerts.add_argument("--limit", type=int, default=3)

    args = parser.parse_args()
    if args.mode == "digest":
        return cmd_digest(args.hours, args.limit)
    if args.mode == "alerts":
        return cmd_alerts(args.limit)
    return 1


if __name__ == "__main__":
    sys.exit(main())
