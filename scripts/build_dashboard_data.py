#!/usr/bin/env python3
"""Merge docs/data.seed.json with TW quotes (yfinance), RSS headlines, and dog mood. Writes docs/data.json."""

from __future__ import annotations

import calendar
import json
import os
import sys
from datetime import datetime, time as dt_time, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
SEED_PATH = DOCS / "data.seed.json"
OUT_PATH = DOCS / "data.json"

TW = ZoneInfo("Asia/Taipei")
DEFAULT_STOCKS = ["2330", "0050", "2317"]
DEFAULT_RSS = [
    "https://news.ltn.com.tw/rss/business.xml",
    "https://news.ltn.com.tw/rss/world.xml",
]
PRIMARY_SYMBOL = "2330"
CHANGE_THRESHOLD_PCT = 1.0
MAX_HEADLINES = 8
TRUMP_POST_LIMIT = 12
TRUMP_EXCERPT_MAX = 220
REQUEST_TIMEOUT = 25
USER_AGENT = "doggo-dashboard-build/1.0 (+https://github.com/meteorcyclops/doggo-dashboard)"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def load_seed() -> dict[str, Any]:
    if not SEED_PATH.is_file():
        print(f"Missing seed file: {SEED_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def tw_trading_window(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    t = now.time()
    return dt_time(9, 0) <= t < dt_time(13, 30)


def fetch_quotes(symbols: list[str]) -> tuple[dict[str, Any], str | None]:
    items: list[dict[str, Any]] = []
    err: str | None = None
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for sym in symbols:
        sym = sym.strip()
        if not sym:
            continue
        suffix = ".TW" if sym.isdigit() or (len(sym) == 4 and sym[0] == "0") else ".TWO"
        ticker = yf.Ticker(f"{sym}{suffix}" if "." not in sym else sym)
        try:
            hist = ticker.history(period="5d")
            if hist is None or hist.empty:
                err = err or "empty history"
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else last
            change_pct = ((last - prev) / prev * 100.0) if prev else 0.0
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                pass
            name = (
                info.get("shortName")
                or info.get("longName")
                or info.get("symbol")
                or sym
            )
            items.append(
                {
                    "symbol": sym,
                    "name": str(name),
                    "price": round(last, 2),
                    "changePct": round(change_pct, 2),
                }
            )
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
    out: dict[str, Any] = {"asOf": as_of, "items": items}
    if err and not items:
        out["error"] = err
    elif err:
        out["error"] = err
    return out, err if not items else None


def _entry_time(entry: Any) -> float:
    if getattr(entry, "published_parsed", None):
        try:
            return calendar.timegm(entry.published_parsed)
        except Exception:
            pass
    if getattr(entry, "updated_parsed", None):
        try:
            return calendar.timegm(entry.updated_parsed)
        except Exception:
            pass
    pub = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if pub:
        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TW)
            return dt.timestamp()
        except Exception:
            pass
    return 0.0


def fetch_feed(urls: list[str], session: requests.Session) -> dict[str, Any]:
    merged: list[tuple[float, dict[str, str]]] = []
    errors: list[str] = []
    for url in urls:
        u = url.strip()
        if not u:
            continue
        try:
            r = session.get(u, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            if getattr(parsed, "bozo", False) and not parsed.entries:
                errors.append(f"{u}: parse")
                continue
            for e in parsed.entries:
                title = (e.get("title") or "").strip()
                link = (e.get("link") or "").strip()
                if not title:
                    continue
                ts = _entry_time(e)
                tstr = ""
                if getattr(e, "published", None):
                    tstr = e.published
                elif getattr(e, "updated", None):
                    tstr = e.updated
                merged.append(
                    (
                        ts,
                        {"title": title, "url": link, "time": tstr},
                    )
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{u}: {exc}")
    merged.sort(key=lambda x: x[0], reverse=True)
    items = [x[1] for x in merged[:MAX_HEADLINES]]
    source = " + ".join(urls[:2]) if urls else ""
    if len(urls) > 2:
        source = f"{urls[0]} + {len(urls) - 1} more"
    out: dict[str, Any] = {"source": source, "items": items}
    if errors:
        out["error"] = "; ".join(errors[:3])
    return out


def compute_dog(
    quotes: dict[str, Any],
    now_tw: datetime,
) -> dict[str, str]:
    primary_change = 0.0
    for it in quotes.get("items") or []:
        if str(it.get("symbol")) == PRIMARY_SYMBOL:
            try:
                primary_change = float(it.get("changePct") or 0)
            except (TypeError, ValueError):
                primary_change = 0.0
            break
    if not tw_trading_window(now_tw):
        return {"state": "sleepy", "label": "市場休息，打個盹"}
    if quotes.get("error") and not quotes.get("items"):
        return {"state": "idle", "label": "報價暫時缺席"}
    if primary_change < -CHANGE_THRESHOLD_PCT:
        return {"state": "worried", "label": "大盤情緒偏保守"}
    if primary_change > CHANGE_THRESHOLD_PCT:
        pick = "bone" if (now_tw.day + now_tw.hour) % 2 else "excited"
        return {
            "state": pick,
            "label": "行情不錯，開心晃晃" if pick == "bone" else "活力滿滿盯盤中",
        }
    return {"state": "idle", "label": "平穩日常"}


def fetch_trump_truth() -> dict[str, Any]:
    """Scrape third-party Trump post archive; failures yield empty items + error (no sys.exit)."""
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: dict[str, Any] = {
        "source": "https://www.trumpstruth.org/ (third-party archive; not Truth Social)",
        "asOf": as_of,
        "items": [],
    }
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from trump_truth_tracker import fetch_posts, is_important
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"import tracker: {exc}"
        return out
    try:
        posts = fetch_posts(limit=TRUMP_POST_LIMIT)
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        return out
    items: list[dict[str, Any]] = []
    for p in posts:
        content = (p.get("content") or "").strip()
        if len(content) <= TRUMP_EXCERPT_MAX:
            excerpt = content
        else:
            excerpt = content[: TRUMP_EXCERPT_MAX - 1].rstrip() + "…"
        item: dict[str, Any] = {
            "postedAtTw": p.get("posted_at_tw") or "",
            "excerpt": excerpt,
            "url": (p.get("archive_link") or "").strip(),
        }
        if is_important(p):
            item["important"] = True
        items.append(item)
    out["items"] = items
    return out


def build_provenance(quotes: dict[str, Any], feed: dict[str, Any]) -> str:
    q_ok = bool(quotes.get("items"))
    f_ok = bool(feed.get("items"))
    if q_ok and f_ok:
        return "LIVE (build)"
    if q_ok:
        return "LIVE (build, RSS partial)"
    if f_ok:
        return "PARTIAL (quotes unavailable)"
    return "DEMO (seed + fetch issues)"


def main() -> None:
    stock_env = os.environ.get("DOGGO_STOCK_SYMBOLS", "")
    symbols = [s.strip() for s in stock_env.split(",") if s.strip()] or list(DEFAULT_STOCKS)
    rss_env = os.environ.get("DOGGO_RSS_URLS", "")
    rss_urls = [s.strip() for s in rss_env.split(",") if s.strip()] or list(DEFAULT_RSS)

    seed = load_seed()
    session = _session()

    quotes, _ = fetch_quotes(symbols)
    feed = fetch_feed(rss_urls, session)
    now_tw = datetime.now(TW)
    dog = compute_dog(quotes, now_tw)
    provenance = build_provenance(quotes, feed)

    trump_truth = fetch_trump_truth()

    out: dict[str, Any] = {
        **seed,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provenance": provenance,
        "quotes": quotes,
        "feed": feed,
        "dog": dog,
        "trumpTruth": trump_truth,
    }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
