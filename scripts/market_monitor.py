#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

TICKERS = {
    "NVDL": {"exchange": "NASDAQ", "stooq": "nvdl.us"},
    "SBET": {"exchange": "NASDAQ", "stooq": "sbet.us"},
    "SOXL": {"exchange": "NYSEARCA", "stooq": "soxl.us"},
    "TQQQ": {"exchange": "NASDAQ", "stooq": "tqqq.us"},
}
NY = ZoneInfo("America/New_York")
STATE_PATH = Path(__file__).resolve().parent.parent / "memory" / "stock-monitor-state.json"
ALERT_15M_THRESHOLD = 3.0
ALERT_DAY_THRESHOLD = 8.0
NEWS_KEYWORDS = ["Nasdaq", "semiconductor", "Nvidia", "TSMC", "Fed", "Iran", "oil market"]
BULLISH_TERMS = ["ceasefire", "cooling", "rally", "gain", "surge", "drop in oil", "rate cut", "rebound", "beat"]
BEARISH_TERMS = ["attack", "war", "selloff", "slump", "inflation", "tariff", "sanction", "spike in oil", "downgrade"]
TITLE_REPLACEMENTS = [
    ("Oil Futures Fall", "油價期貨下跌"),
    ("Oil and Gas Prices Plunge", "油氣價格大跌"),
    ("Stock Markets Soar", "股市大漲"),
    ("ceasefire", "停火"),
    ("deal", "協議"),
    ("remain", "仍在持續"),
    ("Doubts About", "市場仍懷疑"),
    ("US-Iran", "美伊"),
    ("Iran", "伊朗"),
    ("oil", "油價"),
    ("markets", "市場"),
    ("stocks", "股市"),
    ("surge", "大漲"),
    ("fall", "下跌"),
]


def is_regular_market_open(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    current = now.time()
    return time(9, 30) <= current < time(16, 0)


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


def curl_text(url: str) -> str:
    return subprocess.check_output(
        [
            "curl",
            "-fsSL",
            "--max-time",
            "20",
            "-H",
            "User-Agent: Mozilla/5.0",
            url,
        ],
        text=True,
    )


def fetch_live_quote(symbol: str, exchange: str) -> dict:
    url = f"https://www.google.com/finance/quote/{symbol}:{exchange}?hl=en"
    html = curl_text(url)
    price_match = re.search(r'data-last-price="([0-9.]+)"', html)
    ts_match = re.search(r'data-last-normal-market-timestamp="([0-9]+)"', html)
    if not price_match or not ts_match:
        raise RuntimeError(f"無法解析 {symbol} 即時價格")
    return {
        "symbol": symbol,
        "price": float(price_match.group(1)),
        "timestamp": int(ts_match.group(1)),
    }


def fetch_previous_close(stooq_symbol: str) -> float | None:
    url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcvn&e=json"
    data = json.loads(curl_text(url))
    items = data.get("symbols") or []
    if not items:
        return None
    close = items[0].get("close")
    return float(close) if isinstance(close, (int, float)) else None


def sign_arrow(delta: float) -> str:
    if delta > 0.001:
        return "↗"
    if delta < -0.001:
        return "↘"
    return "→"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:+.2f}%"


def fmt_price(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.2f}"


def sentiment_label(ranking: list[tuple[str, float]]) -> str:
    if not ranking:
        return "市場情緒：資料不足"
    avg = sum(value for _, value in ranking) / len(ranking)
    if avg >= 4:
        return "市場情緒：明顯偏多"
    if avg >= 1:
        return "市場情緒：偏多"
    if avg <= -4:
        return "市場情緒：明顯偏弱"
    if avg <= -1:
        return "市場情緒：偏弱"
    return "市場情緒：震盪整理"


def news_query() -> str:
    return " OR ".join(NEWS_KEYWORDS)


def fetch_news(limit: int = 3) -> list[dict]:
    query = urllib.parse.quote(news_query())
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    rss = curl_text(url)
    root = ET.fromstring(rss)
    items = []
    for item in root.findall("./channel/item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "pubDate": pub_date})
    return items


def zh_summary(title: str) -> str:
    summary = title
    for src, dst in TITLE_REPLACEMENTS:
        summary = re.sub(src, dst, summary, flags=re.I)
    summary = re.sub(r"\s+-\s+.*$", "", summary)
    summary = summary.strip(" -")
    if summary == title:
        summary = f"重點是：{title}"
    return summary


def score_news(items: list[dict], ranking: list[tuple[str, float]]) -> tuple[str, dict[str, int]]:
    bull = 0
    bear = 0
    for title in [item["title"].lower() for item in items]:
        bull += sum(term in title for term in BULLISH_TERMS)
        bear += sum(term in title for term in BEARISH_TERMS)
    avg = sum(value for _, value in ranking) / len(ranking) if ranking else 0
    if avg > 1:
        bull += 2
    elif avg < -1:
        bear += 2
    total = bull + bear + 3
    neutral = 3
    bull_pct = round((bull / total) * 100)
    bear_pct = round((bear / total) * 100)
    neutral_pct = max(0, 100 - bull_pct - bear_pct)
    if bull_pct >= bear_pct + 15:
        bias = "偏多"
    elif bear_pct >= bull_pct + 15:
        bias = "偏空"
    else:
        bias = "中性偏震盪"
    return bias, {"bull": bull_pct, "bear": bear_pct, "neutral": neutral_pct}


def now_in_market_tz() -> datetime:
    override = os.environ.get("MARKET_MONITOR_NOW")
    if override:
        return datetime.fromisoformat(override).astimezone(NY)
    return datetime.now(NY)


def main() -> int:
    now = now_in_market_tz()
    if not is_regular_market_open(now):
        print("NO_REPLY")
        return 0

    try:
        quotes = {
            symbol: fetch_live_quote(symbol, meta["exchange"])
            for symbol, meta in TICKERS.items()
        }
        previous_closes = {
            symbol: fetch_previous_close(meta["stooq"])
            for symbol, meta in TICKERS.items()
        }
        news_items = fetch_news(3)
    except Exception as exc:
        print(f"抓取報價失敗: {exc}")
        return 1

    live_dates = {datetime.fromtimestamp(item["timestamp"], NY).date() for item in quotes.values()}
    if len(live_dates) != 1 or next(iter(live_dates)) != now.date():
        print("NO_REPLY")
        return 0

    state = load_state()
    previous = state.get("quotes", {})
    timestamp = now.isoformat()

    lines: list[str] = []
    alerts: list[str] = []
    ranking: list[tuple[str, float]] = []

    for symbol in TICKERS:
        quote = quotes.get(symbol, {})
        price = quote.get("price")
        prev_close = previous_closes.get(symbol)
        day_pct = None
        if isinstance(price, (int, float)) and isinstance(prev_close, (int, float)) and prev_close:
            day_pct = ((price - prev_close) / prev_close) * 100
        prev_price = previous.get(symbol, {}).get("price")
        intraday_move = None
        if isinstance(price, (int, float)) and isinstance(prev_price, (int, float)) and prev_price:
            intraday_move = ((price - prev_price) / prev_price) * 100
        arrow = sign_arrow(intraday_move or 0.0)
        trend = fmt_pct(intraday_move)
        lines.append(f"{symbol} {arrow} {fmt_price(price)}，15分 {trend}，日內 {fmt_pct(day_pct)}")
        if isinstance(day_pct, (int, float)):
            ranking.append((symbol, day_pct))
        if isinstance(intraday_move, (int, float)) and abs(intraday_move) >= ALERT_15M_THRESHOLD:
            alerts.append(f"{symbol} 15 分鐘波動 {fmt_pct(intraday_move)}")
        if isinstance(day_pct, (int, float)) and abs(day_pct) >= ALERT_DAY_THRESHOLD:
            alerts.append(f"{symbol} 日內波動 {fmt_pct(day_pct)}")

    save_state(
        {
            "updatedAt": timestamp,
            "quotes": {
                symbol: {"price": quotes.get(symbol, {}).get("price")}
                for symbol in TICKERS
            },
        }
    )

    strongest = max(ranking, key=lambda item: item[1])[0] if ranking else "--"
    weakest = min(ranking, key=lambda item: item[1])[0] if ranking else "--"
    bias, probs = score_news(news_items, ranking)

    print(f"美股盤中 15 分鐘更新 {now.strftime('%H:%M')} ET")
    print(f"- {sentiment_label(ranking)}")
    for line in lines:
        print(f"- {line}")
    print(f"- 最強: {strongest}，最弱: {weakest}")
    print(f"- 多空判斷: {bias}，多 {probs['bull']}% / 空 {probs['bear']}% / 震盪 {probs['neutral']}%")
    if news_items:
        print("- 最新新聞:")
        for item in news_items[:3]:
            print(f"  • {item['title']}")
            print(f"    中文摘要: {zh_summary(item['title'])}")
    if alerts:
        print(f"- 異常提醒: {'；'.join(alerts)}")
    else:
        print("- 異常提醒: 暫無明顯異常波動")
    print("- 這是盤中趨勢整理，不是買賣建議")
    return 0


if __name__ == "__main__":
    sys.exit(main())
