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


def summarize_text(text: str, limit: int = 120) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[:limit].rstrip() + "..."


def infer_market_link(text: str) -> str:
    lower = text.lower()
    links = []
    if any(k in lower for k in ["iran", "hormuz", "oil", "sanction", "tariff"]):
        links.append("油價")
    if any(k in lower for k in ["war", "attack", "bomb", "nuclear"]):
        links.append("黃金")
        links.append("軍工")
    if any(k in lower for k in ["fed", "market", "stock", "powell", "tariff"]):
        links.append("美股科技")
    if not links:
        links.append("市場情緒")
    deduped = []
    for item in links:
        if item not in deduped:
            deduped.append(item)
    return " / ".join(deduped[:3])


def cmd_digest(hours: int, limit: int) -> int:
    posts = fetch_posts(limit=max(limit, 12))
    cutoff = datetime.now(TW) - timedelta(hours=hours)
    recent = [p for p in posts if datetime.fromisoformat(p["posted_at_tw"]) >= cutoff and is_important(p)]
    if not recent:
        print("NO_REPLY")
        return 0
    focus = recent[:limit]
    lead = focus[0]
    print("川普社群日摘要")
    print(f"- 今天重點: {summarize_text(lead['content'], 140)}")
    print(f"- 可能影響: 目前主軸偏向 {infer_market_link(' '.join(p['content'] for p in focus))}，短線仍受中東與政策消息牽動。")
    print(f"- 市場連動: {infer_market_link(' '.join(p['content'] for p in focus))}")
    print("- 要觀察: 後續是否出現新的停火、制裁、關稅或軍事升級貼文。")
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
    lead = new_important[0]
    same_topic_window_min = 180
    last_alert = state.get("last_alert") or {}
    lead_time = datetime.fromisoformat(lead["posted_at_tw"])
    lead_summary = summarize_text(lead["content"], 80)
    last_summary = last_alert.get("summary", "")
    last_time_raw = last_alert.get("posted_at_tw")
    if last_time_raw:
        try:
            last_time = datetime.fromisoformat(last_time_raw)
            if lead_summary == last_summary and (lead_time - last_time).total_seconds() < same_topic_window_min * 60:
                updated_ids = list({*seen_ids, *(p["truth_id"] for p in new_important)})
                save_state({
                    "alerted_truth_ids": updated_ids[-200:],
                    "last_alert": last_alert,
                })
                print("NO_REPLY")
                return 0
        except ValueError:
            pass
    print("川普重大發言提醒")
    print(f"- 新動向: {summarize_text(lead['content'], 140)}")
    print(f"- 可能影響: 短線先看 {infer_market_link(lead['content'])}，若後續消息被市場確認，波動可能擴大。")
    print(f"- 市場連動: {infer_market_link(lead['content'])}")
    print(f"- 原文連結: {lead['original_link']}")
    updated_ids = list({*seen_ids, *(p["truth_id"] for p in new_important)})
    save_state({
        "alerted_truth_ids": updated_ids[-200:],
        "last_alert": {
            "truth_id": lead["truth_id"],
            "posted_at_tw": lead["posted_at_tw"],
            "summary": lead_summary,
        },
    })
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
