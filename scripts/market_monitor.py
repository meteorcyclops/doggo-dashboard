#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
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

    print(f"美股盤中 15 分鐘更新 {now.strftime('%H:%M')} ET")
    print(f"- {sentiment_label(ranking)}")
    for line in lines:
        print(f"- {line}")
    print(f"- 最強: {strongest}，最弱: {weakest}")
    if alerts:
        print(f"- 異常提醒: {'；'.join(alerts)}")
    else:
        print("- 異常提醒: 暫無明顯異常波動")
    print("- 這是盤中趨勢整理，不是買賣建議")
    return 0


if __name__ == "__main__":
    sys.exit(main())
