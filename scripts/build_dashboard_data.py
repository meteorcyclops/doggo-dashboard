#!/usr/bin/env python3
"""Merge docs/data.seed.json with TW quotes (yfinance), RSS headlines, and dog mood. Writes docs/data.json."""

from __future__ import annotations

import calendar
import json
import os
import re
import sys
from datetime import datetime, time as dt_time, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import requests
import yfinance as yf
from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
SEED_PATH = DOCS / "data.seed.json"
OUT_PATH = DOCS / "data.json"

TW = ZoneInfo("Asia/Taipei")
DEFAULT_STOCKS = [
    "2330", "2317", "2454", "2412", "6505", "2308", "2303", "2881", "2882", "1303",
    "1301", "2002", "2886", "2891", "1216", "2382", "2884", "2885", "3711", "2880",
    "5880", "3045", "2883", "2207", "2912", "3008", "4904", "5871", "6415", "3034",
    "2892", "1326", "2603", "1101", "2887", "2327", "2357", "2379", "4938", "2408",
    "1590", "3037", "2356", "2801", "2609", "2615", "8046", "0050", "0056", "2606",
]
DEFAULT_RSS = [
    "https://news.ltn.com.tw/rss/business.xml",
    "https://news.ltn.com.tw/rss/world.xml",
]
DEFAULT_US_STOCKS = ["TSLA", "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "PLTR"]
FLIGHT_PREFERENCES = {
    "origin": "TPE",
    "regions": ["日本", "韓國", "東南亞"],
    "budgetFlexible": True,
}

FLIGHT_WATCHLIST = [
    {"origin": "TPE", "destination": "東京", "region": "日本", "price": 7288, "baseline": 9800, "airline": "樂桃 / 虎航觀察", "window": "5月上旬", "reason": "日本線目前最有機會出現甜價"},
    {"origin": "TPE", "destination": "大阪", "region": "日本", "price": 7599, "baseline": 10200, "airline": "樂桃 / 捷星觀察", "window": "5月中旬", "reason": "關西線常有促銷，適合持續盯"},
    {"origin": "TPE", "destination": "福岡", "region": "日本", "price": 6880, "baseline": 9300, "airline": "虎航觀察", "window": "5月上旬", "reason": "福岡線常出現短打好價"},
    {"origin": "TPE", "destination": "沖繩", "region": "日本", "price": 5666, "baseline": 7600, "airline": "虎航 / 樂桃觀察", "window": "平日短打", "reason": "沖繩線很適合做輕旅行觀察"},
    {"origin": "TPE", "destination": "首爾", "region": "韓國", "price": 6399, "baseline": 8200, "airline": "德威 / 真航空觀察", "window": "4月底至5月", "reason": "韓國線近期價格帶偏甜"},
    {"origin": "TPE", "destination": "釜山", "region": "韓國", "price": 5899, "baseline": 7800, "airline": "釜山航空觀察", "window": "5月平日", "reason": "釜山線常有低調甜價"},
    {"origin": "TPE", "destination": "曼谷", "region": "東南亞", "price": 5988, "baseline": 7800, "airline": "亞航 / 泰獅航觀察", "window": "5月", "reason": "東南亞線價格相對輕盈"},
    {"origin": "TPE", "destination": "新加坡", "region": "東南亞", "price": 6999, "baseline": 9200, "airline": "酷航觀察", "window": "5月中下旬", "reason": "新加坡線近期有機會撿到促銷票"},
    {"origin": "TPE", "destination": "峴港", "region": "東南亞", "price": 6120, "baseline": 8400, "airline": "越捷觀察", "window": "5月中旬", "reason": "越南線近期有甜價空間"},
]
WEATHER_SPOTS = [
    {"key": "shipai", "label": "石牌", "lat": 25.114, "lon": 121.515},
    {"key": "zhonghe", "label": "中和", "lat": 24.999, "lon": 121.498},
    {"key": "songshan", "label": "松山", "lat": 25.050, "lon": 121.578},
]
TW_STOCK_NAME_MAP = {
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2412": "中華電", "6505": "台塑化",
    "2308": "台達電", "2303": "聯電", "2881": "富邦金", "2882": "國泰金", "1303": "南亞",
    "1301": "台塑", "2002": "中鋼", "2886": "兆豐金", "2891": "中信金", "1216": "統一",
    "2382": "廣達", "2884": "玉山金", "2885": "元大金", "3711": "日月光投控", "2880": "華南金",
    "5880": "合庫金", "3045": "台灣大", "2883": "凱基金", "2207": "和泰車", "2912": "統一超",
    "3008": "大立光", "4904": "遠傳", "5871": "中租-KY", "6415": "矽力*-KY", "3034": "聯詠",
    "2892": "第一金", "1326": "台化", "2603": "長榮", "1101": "台泥", "2887": "台新金",
    "2327": "國巨", "2357": "華碩", "2379": "瑞昱", "4938": "和碩", "2408": "南亞科",
    "1590": "亞德客-KY", "3037": "欣興", "2356": "英業達", "2801": "彰銀", "2609": "陽明",
    "2615": "萬海", "8046": "南電", "0050": "元大台灣50", "0056": "元大高股息", "2606": "裕民",
}
PRIMARY_SYMBOL = "2330"
CHANGE_THRESHOLD_PCT = 1.0
MAX_HEADLINES = 8
TRUMP_POST_LIMIT = 12
TRUMP_EXCERPT_MAX = 220
REQUEST_TIMEOUT = 25
USER_AGENT = "doggo-dashboard-build/1.0 (+https://github.com/meteorcyclops/doggo-dashboard)"
TRUMP_TRANSLATE_MAX = 2800
URL_RE = re.compile(r"https?://\S+")


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
            close_series = [float(v) for v in hist["Close"].tail(8).tolist() if v == v and v not in (float('inf'), float('-inf'))]
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else last
            day_high = float(hist["High"].tail(1).iloc[0]) if "High" in hist else last
            day_low = float(hist["Low"].tail(1).iloc[0]) if "Low" in hist else last
            change = last - prev
            change_pct = ((last - prev) / prev * 100.0) if prev else 0.0
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                pass
            name = (
                TW_STOCK_NAME_MAP.get(sym)
                or info.get("shortName")
                or info.get("longName")
                or info.get("symbol")
                or sym
            )
            safe_price = round(last, 2) if last == last and last not in (float('inf'), float('-inf')) else None
            safe_change_pct = round(change_pct, 2) if change_pct == change_pct and change_pct not in (float('inf'), float('-inf')) else None
            pattern = "range"
            if len(close_series) >= 2:
                amplitude_pct = ((max(close_series) - min(close_series)) / close_series[0] * 100.0) if close_series[0] else 0.0
                slope_pct = ((close_series[-1] - close_series[0]) / close_series[0] * 100.0) if close_series[0] else 0.0
                direction_changes = sum(
                    1 for i in range(2, len(close_series))
                    if (close_series[i] - close_series[i-1]) * (close_series[i-1] - close_series[i-2]) < 0
                )
                if amplitude_pct >= 3.2 and direction_changes >= 3:
                    pattern = "volatile"
                elif slope_pct >= 1.2:
                    pattern = "uptrend"
                elif slope_pct <= -1.2:
                    pattern = "downtrend"
                else:
                    pattern = "range"
            items.append(
                {
                    "symbol": sym,
                    "name": str(name),
                    "price": safe_price,
                    "change": round(change, 2) if change == change and change not in (float('inf'), float('-inf')) else None,
                    "changePct": safe_change_pct,
                    "prevClose": round(prev, 2) if prev == prev and prev not in (float('inf'), float('-inf')) else None,
                    "dayHigh": round(day_high, 2) if day_high == day_high and day_high not in (float('inf'), float('-inf')) else None,
                    "dayLow": round(day_low, 2) if day_low == day_low and day_low not in (float('inf'), float('-inf')) else None,
                    "series": [round(v, 2) for v in close_series[-8:]],
                    "pattern": pattern,
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


def weather_icon(weather_code: int | None, rain: float | None) -> str:
    if rain is not None and rain >= 60:
        return "☔"
    if weather_code in {0, 1}:
        return "☀️"
    if weather_code in {2, 3, 45, 48}:
        return "☁️"
    if weather_code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "🌧️"
    if weather_code in {71, 73, 75, 85, 86}:
        return "❄️"
    return "🌤️"


def weather_outfit_advice(temp: float | None, rain: float | None) -> str:
    if temp is None:
        return "帶件薄外套，先看天空臉色。"
    if rain is not None and rain >= 60:
        if temp >= 26:
            return "短袖加摺傘，鞋子別太怕水。"
        if temp >= 20:
            return "薄外套加雨具，出門別穿太單薄。"
        return "外套加雨具，今天偏濕涼。"
    if temp >= 30:
        return "短袖就好，注意防曬和補水。"
    if temp >= 24:
        return "短袖或薄襯衫就夠，早晚可帶薄外套。"
    if temp >= 18:
        return "建議薄外套，體感比較穩。"
    return "建議外套，早晚會偏涼。"


def weather_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "今天先看天空臉色，天氣資料還沒整理好。"
    max_rain = max((item.get('rainChance') or 0) for item in items)
    if max_rain >= 60:
        return "出門建議帶傘。"
    if max_rain >= 30:
        return "可能遇到零星雨。"
    return "今天大致穩。"


def commute_watch(items: list[dict[str, Any]]) -> str:
    if not items:
        return "女友今天移動路線的天氣提醒還沒整理好。"
    route = [item for item in items if item.get('key') in {'zhonghe', 'songshan'}]
    if not route:
        return "中和到松山這段目前沒有特別需要注意的區域。"
    focus = max(route, key=lambda item: item.get('rainChance') or 0)
    rain = focus.get('rainChance') or 0
    if rain >= 60:
        return f"女友今天在 {focus['label']} 這段比較需要注意，下雨機率偏高。"
    if rain >= 30:
        return f"女友今天移動到 {focus['label']} 一帶時，可能會遇到零星降雨。"
    return "中和到松山這段目前看起來還算穩，先不用太擔心下雨。"


def weather_feel_text(temp: float | None, rain: float | None) -> str:
    if temp is None:
        return "帶件薄外套，先看天空臉色。"
    if rain is not None and rain >= 60:
        if temp >= 26:
            return "短袖可，帶傘。"
        if temp >= 20:
            return "薄外套剛好，記得帶傘。"
        return "外套加雨具，今天偏濕涼。"
    if temp >= 30:
        return "悶熱，注意補水。"
    if temp >= 24:
        return "短袖可，早晚可帶薄外套。"
    if temp >= 18:
        return "薄外套剛好。"
    return "建議外套。"


def summarize_flight_deals(items: list[dict[str, Any]]) -> str:
    if not items:
        return "狗狗今天還沒找到值得先追的便宜航點。"
    hottest = [item for item in items if item.get('badge') == 'HOT']
    cheapest = min(items, key=lambda item: item.get('price') or 10**9)
    if hottest:
        top = hottest[0]
        return f"以你固定 TPE 出發來看，現在最香的是 {top['destination']}，約 {top['price']:,} 起；{cheapest['destination']} 則是目前最低門檻。"
    return f"以你固定 TPE 出發來看，目前最低門檻是 {cheapest['destination']} {cheapest['price']:,} 起，整體以日本 / 韓國 / 東南亞最值得追。"


def classify_flight_deal(price: int, baseline: int) -> tuple[str, str]:
    ratio = price / baseline if baseline else 1.0
    if ratio <= 0.72:
        return 'HOT', '現在這條很香，可以優先盯。'
    if ratio <= 0.84:
        return 'LOOK', '這條有甜，可以放進口袋名單。'
    return 'WATCH', '目前不算地板價，但值得續看。'


def fetch_flight_deals() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    origin = FLIGHT_PREFERENCES['origin']
    regions = set(FLIGHT_PREFERENCES['regions'])
    for route in FLIGHT_WATCHLIST:
        if route['origin'] != origin:
            continue
        if route['region'] not in regions:
            continue
        price = int(route['price'])
        baseline = int(route['baseline'])
        badge, note = classify_flight_deal(price, baseline)
        discount_pct = round((1 - price / baseline) * 100) if baseline else 0
        items.append({
            'origin': route['origin'],
            'destination': route['destination'],
            'region': route['region'],
            'price': price,
            'baseline': baseline,
            'airline': route['airline'],
            'window': route['window'],
            'reason': route['reason'],
            'badge': badge,
            'note': note,
            'discountPct': discount_pct,
        })
    items.sort(key=lambda item: ({'HOT': 0, 'LOOK': 1, 'WATCH': 2}.get(item['badge'], 9), item['price']))
    return {
        'source': 'doggo flight watchlist v2',
        'asOf': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        'preferences': FLIGHT_PREFERENCES,
        'items': items,
        'summary': summarize_flight_deals(items),
    }


def fetch_weather(spots: list[dict[str, Any]], session: requests.Session) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    for spot in spots:
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                f"?latitude={spot['lat']}&longitude={spot['lon']}"
                "&current=temperature_2m,weather_code,precipitation_probability"
                "&hourly=precipitation_probability,temperature_2m"
                "&forecast_hours=3"
                "&timezone=Asia%2FTaipei"
            )
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            current = data.get('current', {})
            hourly = data.get('hourly', {}) or {}
            temp = current.get('temperature_2m')
            rain = current.get('precipitation_probability')
            next_rain = hourly.get('precipitation_probability', [])[:3]
            next_temp = hourly.get('temperature_2m', [])[:3]
            code = current.get('weather_code')
            items.append({
                'key': spot['key'],
                'label': spot['label'],
                'icon': weather_icon(code, float(rain) if rain is not None else None),
                'tempC': round(float(temp), 1) if temp is not None else None,
                'rainChance': int(round(float(rain))) if rain is not None else None,
                'weatherCode': code,
                'advice': weather_outfit_advice(float(temp) if temp is not None else None, float(rain) if rain is not None else None),
                'feel': weather_feel_text(float(temp) if temp is not None else None, float(rain) if rain is not None else None),
                'next3h': {
                    'rainPeak': max(next_rain) if next_rain else rain,
                    'tempMin': min(next_temp) if next_temp else temp,
                    'tempMax': max(next_temp) if next_temp else temp,
                },
                'asOf': current.get('time'),
            })
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{spot['label']}: {exc}")
    out: dict[str, Any] = {
        'items': items,
        'summary': weather_summary(items),
        'commuteWatch': commute_watch(items),
    }
    if errors:
        out['error'] = '; '.join(errors[:3])
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


def split_trailing_url(text: str) -> tuple[str, str]:
    s = " ".join(str(text).split())
    if not s:
        return "", ""
    matches = list(URL_RE.finditer(s))
    if not matches:
        return s, ""
    last = matches[-1]
    if last.end() != len(s):
        return s, ""
    body = s[: last.start()].rstrip(" ：:，,\n\t")
    return body, last.group(0)


def polish_tw_zh(text: str) -> str:
    zh = " ".join(str(text).split())
    replacements = {
        "視頻": "影片",
        "信息": "資訊",
        "导弹": "飛彈",
        "关税": "關稅",
        "协议": "協議",
        "达成": "達成",
        "美国": "美國",
        "報道": "報導",
        "總體規劃": "整體規劃",
        "視頻會議": "視訊會議",
        "民眾們": "大家",
        "進行中": "在進行",
        "武器和任何其他": "武器，以及其他一切",
        "適當和必要的東西": "必要的資源",
        "失敗的《紐約時報》": "《紐約時報》那篇失準報導",
        "完全虛假的": "完全捏造的",
        "旨在抹黑": "擺明是在抹黑",
        "和平進程的人們": "和平進程的相關人士",
        "捏造的騙局": "編出來的騙局",
        "已經嚴重退化": "早已被削弱許多",
        "對於致命起訴和銷毀": "用來徹底打擊和摧毀",
        "會立即被徵收關稅": "會立刻被課關稅",
        "沒有人能相信": "根本沒人會信",
        "並不在那裡": "根本沒有出現",
        "如果我們再次需要他們，他們就不會在那裡": "如果下次我們又需要他們，他們照樣不會出現",
        "記住格陵蘭島，那片大而糟糕的冰塊！": "記住格陵蘭，那塊又大、治理又差的冰原！",
        "總裁DJT": "DJT",
        "特朗普": "川普",
        "總統唐納德·J·特朗普": "川普",
        "唐納德·J·特朗普總統": "川普",
        "唐納德·J·川普總統": "川普",
        "President DJT": "DJT",
        "我很高興提名": "我很高興提名",
        "另外兩家主要製藥公司": "又有兩家大型製藥公司",
        "備受尊敬的": "頗受敬重的",
        "真正強大而有力的領導人": "很有份量的領導人",
        "擁有驚人成果的良好記錄": "過去交出的成績也很亮眼",
        "他為他偉大的國家和人民不懈奮鬥並熱愛": "他一直在為自己的國家和人民拚命，也是真的很愛他的國家",
        "在川普的操縱桿下": "在川普主導下",
        "激發了愛國主義": "把愛國情緒再度炒熱",
        "激發愛國主義": "把愛國情緒再度炒熱",
        "歷史上最糟糕的總統、狡猾的喬·拜登": "史上最糟的總統，也就是喬·拜登",
        "非法外籍罪犯": "非法移民罪犯",
        "被釋放到我國": "被放進美國",
        "用錘子將一名無辜婦女打死": "拿鐵鎚活活打死一名無辜女子",
        "很自豪能夠修復": "很自豪能推動整修",
        "世界上最糟糕、最不準確的「編輯委員會」之一": "全世界最爛、最不準的社論團隊之一",
        "宣佈在伊朗取得了過早的勝利": "太早宣布在伊朗贏了",
        "事實上，這是一場勝利，並沒有什麼「過早」的事情": "但在我看來，這本來就是勝利，根本沒有什麼太早不太早",
        "川普顛覆了中國利潤豐厚的製裁石油進口計畫": "川普打亂了中國那套很賺錢的制裁石油進口盤算",
        "在伊朗和委內瑞拉幹預之後，川普推翻了中國利潤豐厚的受制裁石油進口計劃": "在伊朗和委內瑞拉出手干預後，川普打亂了中國那套很賺錢的受制裁石油進口盤算",
        "已被證明擁有強大的作戰能力和裝備": "早就證明自己在作戰能力和裝備方面很有一套",
        "問問我們的敵人吧": "不信去問我們的敵人",
        "是一位很有份量的領導人": "的確是一位很有份量的領導人",
        "本是一位頗受敬重的律師": "Benjamin Flowers 是一位頗受敬重的律師",
        "在那裡他": "他當時在那裡",
    }
    for old, new in replacements.items():
        zh = zh.replace(old, new)

    soften_replacements = {
        "有些人會說": "有人會說",
        "做得非常糟糕": "做得很差",
        "這不是我們的協議": "這跟我們談好的不一樣",
        "那不是我們的協議": "這跟我們談好的不一樣",
        "沒有人更有資格發言": "沒有誰比她更適合談這件事",
        "寫了一本新書": "出了新書",
        "將透過": "會透過",
        "推出產品": "推出產品",
        "在美國成立 250 週年之前": "替美國 250 週年前的氣氛先暖身",
        "替美國 250 週年前的氣氛先暖身把愛國情緒再度炒熱": "替美國 250 週年前的氣氛先暖身，也把愛國情緒再度炒熱",
        "替美國 250 週年前的氣氛先暖身激發愛國主義": "替美國 250 週年前的氣氛先暖身，也把愛國情緒再度炒熱",
        "被史上最糟的總統，也就是喬·拜登和國會中的激進民主黨人釋放到我國": "被史上最糟的總統喬·拜登和國會裡的激進民主黨人放進美國",
        "世界上最強大的重置！ ！ ！DJT": "史上最強重置！！！DJT",
        "我很高興提名本傑明·弗勞爾斯": "我很高興提名 Benjamin Flowers",
        "問問我們的敵人吧！DJT": "不信去問我們的敵人。DJT",
        "伊朗在允許石油通過霍爾木茲海峽方面做得很差": "伊朗在放行石油通過霍爾木茲海峽這件事上做得很差",
    }
    for old, new in soften_replacements.items():
        zh = zh.replace(old, new)

    cleanup_replacements = {
        "Benjamin Flowers (Benjamin Flowers)": "Benjamin Flowers",
        "（Elise Stefanik）": "",
        "他當時在那裡": "他在任內",
        "我的朋友、紐約州國會女議員": "我的朋友、來自紐約州的國會女議員",
        "頗受敬重的匈牙利總理": "匈牙利總理",
        "的確是一位很有份量的領導人": "確實很有份量",
        "出了新書": "最近出了新書",
        "會透過 TrumpRx 推出產品": "將透過 TrumpRx 推出產品",
        "一名來自海地的非法移民罪犯": "一名來自海地的非法移民罪犯",
    }
    for old, new in cleanup_replacements.items():
        zh = zh.replace(old, new)

    zh = re.sub(r"\b([A-Z][a-z]+ [A-Z][a-z]+) \(\1\)", r"\1", zh)
    zh = re.sub(r"\s+([，。！？])", r"\1", zh)
    zh = re.sub(r"([。！？])\s+", r"\1", zh)
    zh = zh.strip()

    return zh


def summarize_trump_post(item: dict[str, Any]) -> str:
    text = str(item.get("excerptZhTw") or item.get("excerpt") or "").strip()
    if not text:
        return "狗狗重點：這則內容太短，建議直接看原文。"
    lower = str(item.get("excerpt") or "").lower()
    if "iran" in lower or "hormuz" in lower or "oil" in lower:
        return "狗狗重點：這則偏能源與地緣政治訊號，語氣明顯帶警告意味。"
    if "trumprx" in lower or "pharmaceutical" in lower:
        return "狗狗重點：這則是在宣傳 TrumpRx 擴張，比較像政策宣傳或品牌加分文。"
    if "moon" in lower or "artemis" in lower or "patriotism" in lower:
        return "狗狗重點：這則是在把太空任務包裝成愛國敘事，屬於造勢型貼文。"
    if "palantir" in lower:
        return "狗狗重點：這則是在替 Palantir 背書，強調軍事能力與戰場價值。"
    if "orbán" in lower or "orban" in lower:
        return "狗狗重點：這則是在稱讚友好政治人物，屬於表態支持型貼文。"
    if "stefanik" in lower or "book" in lower:
        return "狗狗重點：這則是在幫盟友新書宣傳，重點不是政策而是站台。"
    if "judge" in lower or "court of appeals" in lower or "nominate" in lower:
        return "狗狗重點：這則是人事提名文，重點在法院任命與政治布局。"
    if item.get("important"):
        return "狗狗重點：這則屬於高優先度貼文，建議先看原文和語氣。"
    return "狗狗重點：這則比較偏川普一貫的表態或宣傳型貼文。"


def translate_trump_truth(trump_truth: dict[str, Any]) -> dict[str, Any]:
    items = trump_truth.get("items") or []
    if not items:
        return trump_truth
    try:
        translator = GoogleTranslator(source="en", target="zh-TW")
    except Exception:
        for item in items:
            item["excerptZhTw"] = item.get("excerptZhTw") or ""
            item["dogSummary"] = summarize_trump_post(item)
        return trump_truth

    for item in items:
        text = str(item.get("excerpt") or "").strip()
        body, trailing_url = split_trailing_url(text)
        if trailing_url and not item.get("linkUrl"):
            item["linkUrl"] = trailing_url
        if not body and trailing_url:
            item["excerptZhTw"] = "這則主要是連結貼文，請直接點原文查看。"
            item["dogSummary"] = summarize_trump_post(item)
            continue
        if not text:
            item["excerptZhTw"] = ""
            item["dogSummary"] = summarize_trump_post(item)
            continue
        if text.startswith("http://") or text.startswith("https://"):
            item["excerptZhTw"] = "這則主要是連結貼文，請直接點原文查看。"
            item["dogSummary"] = summarize_trump_post(item)
            continue
        try:
            raw = translator.translate(body[:TRUMP_TRANSLATE_MAX] if body else text[:TRUMP_TRANSLATE_MAX])
            item["excerptZhTw"] = polish_tw_zh(raw)
        except Exception:
            item["excerptZhTw"] = ""
        item["dogSummary"] = summarize_trump_post(item)
    trump_truth.pop("translationError", None)
    return trump_truth


def summarize_us_quote(item: dict[str, Any], session: str) -> str:
    pct = float(item.get("changePct") or 0)
    symbol = item.get("symbol") or "這檔"
    if pct >= 3:
        return f"狗狗重點：{symbol} 今天衝得很兇，是今晚美股最熱的帶頭股之一。"
    if pct >= 1.5:
        return f"狗狗重點：{symbol} 明顯走強，今晚市場情緒偏偏多。"
    if pct <= -3:
        return f"狗狗重點：{symbol} 跌幅偏大，今晚這檔要特別留意。"
    if pct <= -1.5:
        return f"狗狗重點：{symbol} 明顯轉弱，今晚市場有點緊。"
    session_map = {
        "premarket": "盤前還在暖身",
        "market": "盤中還在觀察",
        "afterhours": "盤後還有餘波",
        "closed": "現在已經休市",
    }
    return f"狗狗重點：{symbol} 目前波動不算大，{session_map.get(session, '今晚先列進觀察名單')}。"


def fetch_us_quotes(symbols: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    err: str | None = None
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for sym in symbols:
        sym = sym.strip().upper()
        if not sym:
            continue
        ticker = yf.Ticker(sym)
        try:
            hist = ticker.history(period="5d", interval="1d")
            if hist is None or hist.empty:
                err = err or "empty history"
                continue
            close_series = [float(v) for v in hist["Close"].tail(8).tolist() if v == v and v not in (float('inf'), float('-inf'))]
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else last
            change_pct = ((last - prev) / prev * 100.0) if prev else 0.0
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                pass
            items.append({
                "symbol": sym,
                "name": info.get("shortName") or info.get("longName") or sym,
                "price": round(last, 2),
                "changePct": round(change_pct, 2),
                "series": [round(v, 2) for v in close_series[-5:]],
            })
        except Exception as exc:  # noqa: BLE001
            err = err or str(exc)
    items.sort(key=lambda item: abs(float(item.get("changePct") or 0)), reverse=True)
    session = "closed"
    now_ny = datetime.now(ZoneInfo("America/New_York"))
    mins = now_ny.hour * 60 + now_ny.minute
    if now_ny.weekday() < 5:
        if 4 * 60 <= mins < 9 * 60 + 30:
            session = "premarket"
        elif 9 * 60 + 30 <= mins < 16 * 60:
            session = "market"
        elif 16 * 60 <= mins < 20 * 60:
            session = "afterhours"
    summary = "美股觀察清單整理中。"
    if items:
        for item in items:
            item["dogSummary"] = summarize_us_quote(item, session)
        leader = items[0]
        pct = float(leader.get("changePct") or 0)
        if pct >= 2:
            summary = f"{leader['symbol']} 漲幅最明顯，今天美股情緒偏熱。"
        elif pct <= -2:
            summary = f"{leader['symbol']} 波動最大且偏弱，美股情緒有點緊。"
        else:
            summary = f"{leader['symbol']} 目前最活躍，美股整體還在觀察區。"
    return {
        "asOf": as_of,
        "session": session,
        "summary": summary,
        "items": items,
        **({"error": err} if err and not items else {}),
    }


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
    us_stock_env = os.environ.get("DOGGO_US_STOCK_SYMBOLS", "")
    us_symbols = [s.strip() for s in us_stock_env.split(",") if s.strip()] or list(DEFAULT_US_STOCKS)
    rss_env = os.environ.get("DOGGO_RSS_URLS", "")
    rss_urls = [s.strip() for s in rss_env.split(",") if s.strip()] or list(DEFAULT_RSS)

    seed = load_seed()
    session = _session()

    quotes, _ = fetch_quotes(symbols)
    us_quotes = fetch_us_quotes(us_symbols)
    feed = fetch_feed(rss_urls, session)
    weather = fetch_weather(WEATHER_SPOTS, session)
    flight_deals = fetch_flight_deals()
    now_tw = datetime.now(TW)
    dog = compute_dog(quotes, now_tw)
    provenance = build_provenance(quotes, feed)

    trump_truth = translate_trump_truth(fetch_trump_truth())

    build_trigger = (os.environ.get("DOGGO_BUILD_TRIGGER") or "manual").strip().lower()
    out: dict[str, Any] = {
        **seed,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "buildTrigger": build_trigger,
        "provenance": provenance,
        "quotes": quotes,
        "usQuotes": us_quotes,
        "feed": feed,
        "weather": weather,
        "flightDeals": flight_deals,
        "dog": dog,
        "trumpTruth": trump_truth,
    }

    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
