from __future__ import annotations

import calendar
import json
import mimetypes
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request as urllib_request

import feedparser
import requests
import yfinance as yf
from deep_translator import GoogleTranslator
from zoneinfo import ZoneInfo

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

ADMIN_TOKEN = os.environ.get('CHAT_ADMIN_TOKEN', '')
SECRET_KEY = os.environ.get('CHAT_SECRET_KEY', '')
DEFAULT_ROOM_SLUG = os.environ.get('CHAT_DEFAULT_ROOM', 'lobby')
RATE_LIMIT_SECONDS = int(os.environ.get('CHAT_RATE_LIMIT_SECONDS', '8'))
MAX_MESSAGE_LENGTH = int(os.environ.get('CHAT_MAX_MESSAGE_LENGTH', '400'))
MAX_MESSAGES = int(os.environ.get('CHAT_MAX_MESSAGES', '120'))
TW_QUOTES_CACHE_SECONDS = int(os.environ.get('TW_QUOTES_CACHE_SECONDS', '15'))
TW_QUOTES_MAX_SYMBOLS = int(os.environ.get('TW_QUOTES_MAX_SYMBOLS', '80'))
DOGGO_RSS_URLS = [s.strip() for s in os.environ.get('DOGGO_RSS_URLS', 'https://news.ltn.com.tw/rss/business.xml,https://news.ltn.com.tw/rss/world.xml').split(',') if s.strip()]
DOGGO_US_STOCK_SYMBOLS = [s.strip().upper() for s in os.environ.get('DOGGO_US_STOCK_SYMBOLS', 'TSLA,NVDA,AAPL,MSFT,AMZN,META,GOOGL,PLTR').split(',') if s.strip()]
REQUEST_TIMEOUT = int(os.environ.get('DOGGO_REQUEST_TIMEOUT_SECONDS', '25'))
TRUMP_POST_LIMIT = int(os.environ.get('DOGGO_TRUMP_POST_LIMIT', '12'))
TRUMP_EXCERPT_MAX = int(os.environ.get('DOGGO_TRUMP_EXCERPT_MAX', '220'))
TRUMP_TRANSLATE_MAX = int(os.environ.get('DOGGO_TRUMP_TRANSLATE_MAX', '2800'))
USER_AGENT = "doggo-dashboard-api/1.0 (+https://github.com/meteorcyclops/doggo-dashboard)"
SESSION_COOKIE_NAME = os.environ.get('CHAT_SESSION_COOKIE_NAME', 'koxuan_chat_session')
SESSION_COOKIE_SECURE = os.environ.get('CHAT_SESSION_COOKIE_SECURE', 'false').lower() in {'1', 'true', 'yes', 'on'}
SESSION_COOKIE_SAMESITE = os.environ.get('CHAT_SESSION_COOKIE_SAMESITE', 'Lax')
PERMANENT_SESSION_LIFETIME_SECONDS = int(os.environ.get('CHAT_SESSION_TTL_SECONDS', str(60 * 60 * 24 * 7)))
SUPABASE_URL = os.environ.get('CHAT_SUPABASE_URL', '').rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('CHAT_SUPABASE_SERVICE_ROLE_KEY', '')
SUPABASE_SCHEMA = os.environ.get('CHAT_SUPABASE_SCHEMA', 'public')
SUPABASE_STORAGE_BUCKET = os.environ.get('CHAT_SUPABASE_STORAGE_BUCKET', 'chat-uploads')
MAX_UPLOAD_BYTES = int(os.environ.get('CHAT_MAX_UPLOAD_BYTES', str(20 * 1024 * 1024)))

ANIMALS = ['🦊', '🦦', '🦋', '🐼', '🐶', '🐱', '🐺', '🐈', '🦭', '🐦', '🐰', '🦝', '🦔', '🐸']
TW_QUOTES_CACHE: dict[str, dict[str, Any]] = {}
TW = ZoneInfo('Asia/Taipei')
URL_RE = re.compile(r"https?://\\S+")
MAX_HEADLINES = 8
WEATHER_SPOTS = [
    {'key': 'shipai', 'label': '石牌', 'lat': 25.114, 'lon': 121.515},
    {'key': 'zhonghe', 'label': '中和', 'lat': 24.999, 'lon': 121.498},
    {'key': 'songshan', 'label': '松山', 'lat': 25.050, 'lon': 121.578},
]
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
SCRIPTS_DIR = ROOT_DIR / 'scripts'
FLIGHT_PREFERENCES = {
    'origin': 'TPE',
    'regions': ['日本', '韓國', '東南亞'],
    'budgetFlexible': True,
}
FLIGHT_WATCHLIST = [
    {'origin': 'TPE', 'destination': '東京', 'region': '日本', 'price': 7288, 'baseline': 9800, 'airline': '樂桃 / 虎航觀察', 'window': '5月上旬', 'reason': '日本線目前最有機會出現甜價'},
    {'origin': 'TPE', 'destination': '大阪', 'region': '日本', 'price': 7599, 'baseline': 10200, 'airline': '樂桃 / 捷星觀察', 'window': '5月中旬', 'reason': '關西線常有促銷，適合持續盯'},
    {'origin': 'TPE', 'destination': '福岡', 'region': '日本', 'price': 6880, 'baseline': 9300, 'airline': '虎航觀察', 'window': '5月上旬', 'reason': '福岡線常出現短打好價'},
    {'origin': 'TPE', 'destination': '沖繩', 'region': '日本', 'price': 5666, 'baseline': 7600, 'airline': '虎航 / 樂桃觀察', 'window': '平日短打', 'reason': '沖繩線很適合做輕旅行觀察'},
    {'origin': 'TPE', 'destination': '首爾', 'region': '韓國', 'price': 6399, 'baseline': 8200, 'airline': '德威 / 真航空觀察', 'window': '4月底至5月', 'reason': '韓國線近期價格帶偏甜'},
    {'origin': 'TPE', 'destination': '釜山', 'region': '韓國', 'price': 5899, 'baseline': 7800, 'airline': '釜山航空觀察', 'window': '5月平日', 'reason': '釜山線常有低調甜價'},
    {'origin': 'TPE', 'destination': '曼谷', 'region': '東南亞', 'price': 5988, 'baseline': 7800, 'airline': '亞航 / 泰獅航觀察', 'window': '5月', 'reason': '東南亞線價格相對輕盈'},
    {'origin': 'TPE', 'destination': '新加坡', 'region': '東南亞', 'price': 6999, 'baseline': 9200, 'airline': '酷航觀察', 'window': '5月中下旬', 'reason': '新加坡線近期有機會撿到促銷票'},
    {'origin': 'TPE', 'destination': '峴港', 'region': '東南亞', 'price': 6120, 'baseline': 8400, 'airline': '越捷觀察', 'window': '5月中旬', 'reason': '越南線近期有甜價空間'},
]

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_NAME=SESSION_COOKIE_NAME,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
    PERMANENT_SESSION_LIFETIME=PERMANENT_SESSION_LIFETIME_SECONDS,
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

if not SECRET_KEY:
    raise RuntimeError('CHAT_SECRET_KEY is required in production.')
if not ADMIN_TOKEN:
    raise RuntimeError('CHAT_ADMIN_TOKEN is required in production.')
if not SUPABASE_URL:
    raise RuntimeError('CHAT_SUPABASE_URL is required for Supabase-backed chat.')
if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError('CHAT_SUPABASE_SERVICE_ROLE_KEY is required for Supabase-backed chat.')


class SupabaseError(RuntimeError):
    pass


def _http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': USER_AGENT})
    return s


def _entry_time(entry: Any) -> float:
    if getattr(entry, 'published_parsed', None):
        try:
            return calendar.timegm(entry.published_parsed)
        except Exception:
            pass
    if getattr(entry, 'updated_parsed', None):
        try:
            return calendar.timegm(entry.updated_parsed)
        except Exception:
            pass
    return 0.0


def fetch_feed_live(urls: list[str]) -> dict[str, Any]:
    merged: list[tuple[float, dict[str, str]]] = []
    errors: list[str] = []
    session = _http_session()
    for raw_url in urls:
        url = raw_url.strip()
        if not url:
            continue
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            if getattr(parsed, 'bozo', False) and not parsed.entries:
                errors.append(f'{url}: parse')
                continue
            for entry in parsed.entries:
                title = (entry.get('title') or '').strip()
                link = (entry.get('link') or '').strip()
                if not title:
                    continue
                merged.append((_entry_time(entry), {
                    'title': title,
                    'url': link,
                    'time': (getattr(entry, 'published', None) or getattr(entry, 'updated', None) or ''),
                }))
        except Exception as exc:  # noqa: BLE001
            errors.append(f'{url}: {exc}')
    merged.sort(key=lambda item: item[0], reverse=True)
    payload: dict[str, Any] = {
        'source': ' + '.join(urls[:2]) if urls else '',
        'asOf': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'items': [item[1] for item in merged[:MAX_HEADLINES]],
    }
    if errors:
        payload['error'] = '; '.join(errors[:3])
    return payload


def summarize_us_quote(item: dict[str, Any], session_name: str) -> str:
    pct = float(item.get('changePct') or 0)
    symbol = item.get('symbol') or '這檔'
    if pct >= 3:
        return f'狗狗重點：{symbol} 今天衝得很兇，是今晚美股最熱的帶頭股之一。'
    if pct >= 1.5:
        return f'狗狗重點：{symbol} 明顯走強，今晚市場情緒偏偏多。'
    if pct <= -3:
        return f'狗狗重點：{symbol} 跌幅偏大，今晚這檔要特別留意。'
    if pct <= -1.5:
        return f'狗狗重點：{symbol} 明顯轉弱，今晚市場有點緊。'
    session_map = {
        'premarket': '盤前還在暖身',
        'market': '盤中還在觀察',
        'afterhours': '盤後還有餘波',
        'closed': '現在已經休市',
    }
    return f'狗狗重點：{symbol} 目前波動不算大，{session_map.get(session_name, "今晚先列進觀察名單")}。'


def fetch_us_quotes_live(symbols: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    as_of = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    for symbol in symbols:
        sym = symbol.strip().upper()
        if not sym:
            continue
        ticker = yf.Ticker(sym)
        try:
            hist = ticker.history(period='5d', interval='1d')
            if hist is None or hist.empty:
                errors.append(f'{sym}: empty history')
                continue
            close_series = [float(v) for v in hist['Close'].tail(8).tolist() if v == v]
            last = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else last
            change_pct = ((last - prev) / prev * 100.0) if prev else 0.0
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                info = {}
            items.append({
                'symbol': sym,
                'name': info.get('shortName') or info.get('longName') or sym,
                'price': round(last, 2),
                'changePct': round(change_pct, 2),
                'series': [round(v, 2) for v in close_series[-5:]],
            })
        except Exception as exc:  # noqa: BLE001
            errors.append(f'{sym}: {exc}')
    items.sort(key=lambda item: abs(float(item.get('changePct') or 0)), reverse=True)
    session_name = 'closed'
    now_ny = datetime.now(ZoneInfo('America/New_York'))
    mins = now_ny.hour * 60 + now_ny.minute
    if now_ny.weekday() < 5:
        if 4 * 60 <= mins < 9 * 60 + 30:
            session_name = 'premarket'
        elif 9 * 60 + 30 <= mins < 16 * 60:
            session_name = 'market'
        elif 16 * 60 <= mins < 20 * 60:
            session_name = 'afterhours'
    for item in items:
        item['dogSummary'] = summarize_us_quote(item, session_name)
    summary = '美股觀察清單整理中。'
    if items:
        leader = items[0]
        pct = float(leader.get('changePct') or 0)
        if pct >= 2:
            summary = f"{leader['symbol']} 漲幅最明顯，今天美股情緒偏熱。"
        elif pct <= -2:
            summary = f"{leader['symbol']} 波動最大且偏弱，美股情緒有點緊。"
        else:
            summary = f"{leader['symbol']} 目前最活躍，美股整體還在觀察區。"
    payload: dict[str, Any] = {'asOf': as_of, 'session': session_name, 'summary': summary, 'items': items}
    if errors and not items:
        payload['error'] = '; '.join(errors[:5])
    return payload


def weather_icon(weather_code: int | None, rain: float | None) -> str:
    if rain is not None and rain >= 60:
        return '☔'
    if weather_code in {0, 1}:
        return '☀️'
    if weather_code in {2, 3, 45, 48}:
        return '☁️'
    if weather_code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return '🌧️'
    if weather_code in {71, 73, 75, 85, 86}:
        return '❄️'
    return '🌤️'


def weather_outfit_advice(temp: float | None, rain: float | None) -> str:
    if temp is None:
        return '帶件薄外套，先看天空臉色。'
    if rain is not None and rain >= 60:
        if temp >= 26:
            return '短袖加摺傘，鞋子別太怕水。'
        if temp >= 20:
            return '薄外套加雨具，出門別穿太單薄。'
        return '外套加雨具，今天偏濕涼。'
    if temp >= 30:
        return '短袖就好，注意防曬和補水。'
    if temp >= 24:
        return '短袖或薄襯衫就夠，早晚可帶薄外套。'
    if temp >= 18:
        return '建議薄外套，體感比較穩。'
    return '建議外套，早晚會偏涼。'


def weather_feel_text(temp: float | None, rain: float | None) -> str:
    if temp is None:
        return '帶件薄外套，先看天空臉色。'
    if rain is not None and rain >= 60:
        if temp >= 26:
            return '短袖可，帶傘。'
        if temp >= 20:
            return '薄外套剛好，記得帶傘。'
        return '外套加雨具，今天偏濕涼。'
    if temp >= 30:
        return '悶熱，注意補水。'
    if temp >= 24:
        return '短袖可，早晚可帶薄外套。'
    if temp >= 18:
        return '薄外套剛好。'
    return '建議外套。'


def weather_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return '今天先看天空臉色，天氣資料還沒整理好。'
    max_rain = max((item.get('rainChance') or 0) for item in items)
    if max_rain >= 60:
        return '出門建議帶傘。'
    if max_rain >= 30:
        return '可能遇到零星雨。'
    return '今天大致穩。'


def commute_watch(items: list[dict[str, Any]]) -> str:
    if not items:
        return '三地天氣提醒還沒整理好。'
    rainiest = max(items, key=lambda item: float(item.get('rainChance') or 0))
    wet_spots = [item.get('label') for item in items if float(item.get('rainChance') or 0) >= 30]
    if float(rainiest.get('rainChance') or 0) >= 60:
        return f"三地裡最需要注意的是 {rainiest.get('label')}，降雨機率偏高；出門建議優先防這一區。"
    if wet_spots:
        return f"三地裡 {'、'.join([spot for spot in wet_spots if spot])} 比較可能遇到零星降雨，其它區域目前還算穩。"
    return '目前石牌、中和、松山三地都算穩，先不用太擔心下雨。'


def fetch_weather_live(spots: list[dict[str, Any]]) -> dict[str, Any]:
    session = _http_session()
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    for spot in spots:
        try:
            url = (
                'https://api.open-meteo.com/v1/forecast'
                f"?latitude={spot['lat']}&longitude={spot['lon']}"
                '&current=temperature_2m,weather_code,precipitation_probability'
                '&hourly=precipitation_probability,temperature_2m'
                '&forecast_hours=3&timezone=Asia%2FTaipei'
            )
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            current = data.get('current', {})
            hourly = data.get('hourly', {}) or {}
            temp = current.get('temperature_2m')
            rain = current.get('precipitation_probability')
            next_rain = hourly.get('precipitation_probability', [])[:3]
            next_temp = hourly.get('temperature_2m', [])[:3]
            items.append({
                'key': spot['key'],
                'label': spot['label'],
                'icon': weather_icon(current.get('weather_code'), float(rain) if rain is not None else None),
                'tempC': round(float(temp), 1) if temp is not None else None,
                'rainChance': int(round(float(rain))) if rain is not None else None,
                'weatherCode': current.get('weather_code'),
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
    payload: dict[str, Any] = {
        'asOf': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'items': items,
        'summary': weather_summary(items),
        'commuteWatch': commute_watch(items),
    }
    if errors:
        payload['error'] = '; '.join(errors[:3])
    return payload


def summarize_flight_deals(items: list[dict[str, Any]]) -> str:
    if not items:
        return '狗狗今天還沒找到值得先追的便宜航點。'
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


def fetch_flight_deals_live() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    origin = FLIGHT_PREFERENCES['origin']
    regions = set(FLIGHT_PREFERENCES['regions'])
    for route in FLIGHT_WATCHLIST:
        if route['origin'] != origin or route['region'] not in regions:
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
        'asOf': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'preferences': FLIGHT_PREFERENCES,
        'items': items,
        'summary': summarize_flight_deals(items),
    }


def split_trailing_url(text: str) -> tuple[str, str]:
    s = ' '.join(str(text).split())
    if not s:
        return '', ''
    matches = list(URL_RE.finditer(s))
    if not matches:
        return s, ''
    last = matches[-1]
    if last.end() != len(s):
        return s, ''
    return s[: last.start()].rstrip(' ：:，,\n\t'), last.group(0)


def polish_tw_zh(text: str) -> str:
    zh = ' '.join(str(text).split())
    replacements = {
        '視頻': '影片', '信息': '資訊', '导弹': '飛彈', '关税': '關稅', '协议': '協議',
        '美国': '美國', '特朗普': '川普', '總統唐納德·J·特朗普': '川普', '唐納德·J·特朗普總統': '川普',
    }
    for old, new in replacements.items():
        zh = zh.replace(old, new)
    zh = re.sub(r'\s+([，。！？])', r'\1', zh)
    return zh.strip()


def summarize_trump_post(item: dict[str, Any]) -> str:
    lower = str(item.get('excerpt') or '').lower()
    if 'iran' in lower or 'hormuz' in lower or 'oil' in lower:
        return '狗狗重點：這則偏能源與地緣政治訊號，語氣明顯帶警告意味。'
    if item.get('important'):
        return '狗狗重點：這則屬於高優先度貼文，建議先看原文和語氣。'
    return '狗狗重點：這則比較偏川普一貫的表態或宣傳型貼文。'


def fetch_trump_truth_live() -> dict[str, Any]:
    payload: dict[str, Any] = {
        'source': 'https://www.trumpstruth.org/ (third-party archive; not Truth Social)',
        'asOf': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'items': [],
    }
    import sys
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from trump_truth_tracker import fetch_posts, is_important  # type: ignore
    except Exception as exc:  # noqa: BLE001
        payload['error'] = f'import tracker: {exc}'
        return payload
    try:
        posts = fetch_posts(limit=TRUMP_POST_LIMIT)
    except Exception as exc:  # noqa: BLE001
        payload['error'] = str(exc)
        return payload

    translator = None
    try:
        translator = GoogleTranslator(source='en', target='zh-TW')
    except Exception:
        translator = None

    items: list[dict[str, Any]] = []
    for post in posts:
        content = (post.get('content') or '').strip()
        excerpt = content if len(content) <= TRUMP_EXCERPT_MAX else content[: TRUMP_EXCERPT_MAX - 1].rstrip() + '…'
        item: dict[str, Any] = {
            'postedAtTw': post.get('posted_at_tw') or '',
            'excerpt': excerpt,
            'url': (post.get('archive_link') or '').strip(),
        }
        if is_important(post):
            item['important'] = True
        body, trailing_url = split_trailing_url(excerpt)
        if trailing_url:
            item['linkUrl'] = trailing_url
        if translator and body and not body.startswith('http'):
            try:
                item['excerptZhTw'] = polish_tw_zh(translator.translate(body[:TRUMP_TRANSLATE_MAX]))
            except Exception:
                item['excerptZhTw'] = ''
        else:
            item['excerptZhTw'] = ''
        item['dogSummary'] = summarize_trump_post(item)
        items.append(item)
    payload['items'] = items
    return payload


def supabase_request(method: str, path: str, *, query: dict[str, Any] | None = None, json_body: dict[str, Any] | list[dict[str, Any]] | None = None, data: bytes | None = None, extra_headers: dict[str, str] | None = None, prefer: str | None = None) -> Any:
    url = f"{SUPABASE_URL}/rest/v1/{path.lstrip('/')}"
    if query:
        url = f"{url}?{parse.urlencode(query, doseq=True)}"

    headers = {
        'apikey': SUPABASE_SERVICE_ROLE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Accept-Profile': SUPABASE_SCHEMA,
        'Content-Profile': SUPABASE_SCHEMA,
    }
    if prefer:
        headers['Prefer'] = prefer
    if extra_headers:
        headers.update(extra_headers)

    body = data
    if json_body is not None:
        body = json.dumps(json_body).encode('utf-8')

    req = urllib_request.Request(url, method=method.upper(), headers=headers, data=body)
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8') if resp.headers.get('Content-Type', '').startswith('application/json') else resp.read()
            if raw in (b'', ''):
                return None
            if isinstance(raw, bytes):
                return raw
            return json.loads(raw)
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise SupabaseError(f'Supabase HTTP {exc.code}: {detail}') from exc
    except error.URLError as exc:
        raise SupabaseError(f'Supabase connection failed: {exc}') from exc


def fetch_one(path: str, query: dict[str, Any]) -> dict[str, Any] | None:
    rows = supabase_request('GET', path, query={**query, 'limit': 1}) or []
    return rows[0] if rows else None


def ensure_nickname() -> str:
    if 'nickname' not in session:
        session['nickname'] = secrets.choice(ANIMALS)
    return session['nickname']


def ensure_session_id() -> str:
    if 'chat_session_id' not in session:
        session['chat_session_id'] = secrets.token_hex(16)
    session.permanent = True
    return session['chat_session_id']


def current_room() -> dict[str, Any] | None:
    room_id = session.get('chat_room_id')
    if not room_id:
        return None
    return fetch_one('chat_rooms', {'id': f'eq.{room_id}'})


def require_access() -> dict[str, Any]:
    room = current_room()
    if room is None:
        abort(403)
    return room


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def invite_status(invite: dict[str, Any]) -> str | None:
    now = datetime.now(timezone.utc)
    if invite.get('revoked'):
        return '這個邀請連結已停用。'
    expires_at = parse_timestamp(invite.get('expires_at'))
    if expires_at and now > expires_at:
        return '這個邀請連結已過期。'
    max_uses = invite.get('max_uses')
    use_count = int(invite.get('use_count') or 0)
    if max_uses is not None and use_count >= int(max_uses):
        return '這個邀請連結已達使用上限。'
    return None


def create_invite(room_id: str, label: str = 'default', max_uses: int | None = None) -> str:
    token = secrets.token_urlsafe(24)
    payload = {
        'token': token,
        'room_id': room_id,
        'label': label,
        'max_uses': max_uses,
    }
    supabase_request('POST', 'chat_invites', json_body=payload, prefer='return=minimal')
    return token


def ensure_default_room() -> dict[str, Any]:
    room = fetch_one('chat_rooms', {'slug': f'eq.{DEFAULT_ROOM_SLUG}'})
    if room:
        return room
    payload = {
        'slug': DEFAULT_ROOM_SLUG,
        'title': '匿名小圈圈聊天室',
        'description': '用邀請連結進入，匿名但不裸奔。',
    }
    supabase_request('POST', 'chat_rooms', json_body=payload, prefer='return=representation')
    room = fetch_one('chat_rooms', {'slug': f'eq.{DEFAULT_ROOM_SLUG}'})
    if room is None:
        raise SupabaseError('Failed to create default room.')
    return room


def ensure_bootstrap_invite() -> None:
    room = ensure_default_room()
    existing = supabase_request('GET', 'chat_invites', query={'room_id': f"eq.{room['id']}", 'select': 'id', 'limit': 1}) or []
    if not existing:
        create_invite(room['id'], label='bootstrap')


def current_admin_token() -> str:
    return request.headers.get('X-Admin-Token', '') or request.args.get('token', '') or session.get('chat_admin_token', '')


def require_admin_token() -> None:
    if current_admin_token() != ADMIN_TOKEN:
        abort(401)


def increment_invite_use_count(invite: dict[str, Any]) -> None:
    next_count = int(invite.get('use_count') or 0) + 1
    supabase_request('PATCH', 'chat_invites', query={'id': f"eq.{invite['id']}"}, json_body={'use_count': next_count}, prefer='return=minimal')


def upsert_rate_limit(session_id: str) -> None:
    supabase_request(
        'POST',
        'chat_rate_limits',
        json_body={'session_id': session_id, 'last_post_at': datetime.now(timezone.utc).isoformat()},
        prefer='resolution=merge-duplicates,return=minimal',
    )


def ensure_bucket_public() -> None:
    req = urllib_request.Request(
        f'{SUPABASE_URL}/storage/v1/bucket',
        method='POST',
        headers={
            'apikey': SUPABASE_SERVICE_ROLE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            'Content-Type': 'application/json',
        },
        data=json.dumps({'id': SUPABASE_STORAGE_BUCKET, 'name': SUPABASE_STORAGE_BUCKET, 'public': True}).encode('utf-8'),
    )
    try:
        with urllib_request.urlopen(req, timeout=30):
            return
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        if 'already exists' in detail or 'duplicate key value' in detail:
            return
        raise SupabaseError(f'Supabase storage bucket create failed: {detail}') from exc


def upload_image(file_storage: Any, room_id: str) -> tuple[str, str]:
    content = file_storage.read()
    file_storage.stream.seek(0)
    if not content:
        raise ValueError('圖片內容是空的。')
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f'圖片不能超過 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB。')

    mime_type = file_storage.mimetype or mimetypes.guess_type(file_storage.filename or '')[0] or 'application/octet-stream'
    ext = mimetypes.guess_extension(mime_type) or '.bin'
    image_path = f'{room_id}/{int(time.time())}-{secrets.token_urlsafe(8)}{ext}'
    req = urllib_request.Request(
        f'{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{image_path}',
        method='POST',
        headers={
            'apikey': SUPABASE_SERVICE_ROLE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_ROLE_KEY}',
            'Content-Type': mime_type,
            'x-upsert': 'false',
        },
        data=content,
    )
    try:
        with urllib_request.urlopen(req, timeout=60):
            pass
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise SupabaseError(f'Supabase storage upload failed: {detail}') from exc

    public_url = f'{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{image_path}'
    return public_url, image_path


@app.after_request
def apply_security_headers(response: Any) -> Any:
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.route('/')
def index() -> Any:
    room = current_room()
    if room:
        ensure_nickname()
        ensure_session_id()
        return render_template(
            'index.html',
            nickname=session['nickname'],
            room=room,
            max_message_length=MAX_MESSAGE_LENGTH,
            max_upload_mb=max(1, MAX_UPLOAD_BYTES // (1024 * 1024)),
            admin_mode=session.get('chat_admin_token') == ADMIN_TOKEN,
            admin_token=session.get('chat_admin_token', ''),
        )
    return redirect('/enter')


@app.route('/enter', methods=['GET', 'POST'])
def enter() -> Any:
    error = None
    invite_token = (request.args.get('invite') or '').strip()
    if request.method == 'POST':
        invite_token = (request.form.get('token') or '').strip()

    if invite_token:
        invite = fetch_one('chat_invites', {'token': f'eq.{invite_token}'})
        if invite is None:
            error = '找不到這個邀請連結。'
        else:
            blocked_reason = invite_status(invite)
            if blocked_reason:
                error = blocked_reason
            else:
                room = fetch_one('chat_rooms', {'id': f"eq.{invite['room_id']}"})
                if room is None:
                    error = '邀請對應的聊天室不存在。'
                else:
                    increment_invite_use_count(invite)
                    session.clear()
                    session['chat_authorized'] = True
                    session['chat_room_id'] = room['id']
                    session['chat_invite_token'] = invite_token
                    admin_token = request.args.get('token', '') or request.form.get('admin_token', '')
                    if admin_token == ADMIN_TOKEN:
                        session['chat_admin_token'] = admin_token
                    ensure_nickname()
                    ensure_session_id()
                    return redirect('/')

    return render_template('enter.html', error=error, invite_token=invite_token)


@app.route('/logout', methods=['POST'])
def logout() -> Any:
    session.clear()
    return redirect('/enter')


@app.route('/api/me')
def me() -> Any:
    room = require_access()
    return jsonify({'nickname': ensure_nickname(), 'room': {'slug': room['slug'], 'title': room['title']}})


@app.route('/api/messages')
def list_messages() -> Any:
    room = require_access()
    rows = supabase_request(
        'GET',
        'chat_messages',
        query={
            'room_id': f"eq.{room['id']}",
            'deleted': 'eq.false',
            'select': 'id,nickname,body,image_url,created_at',
            'order': 'created_at.desc',
            'limit': MAX_MESSAGES,
        },
    ) or []
    items = list(reversed(rows))
    return jsonify({
        'items': items,
        'rateLimitSeconds': RATE_LIMIT_SECONDS,
        'maxMessageLength': MAX_MESSAGE_LENGTH,
        'maxUploadMb': max(1, MAX_UPLOAD_BYTES // (1024 * 1024)),
    })


@app.route('/api/messages', methods=['POST'])
def create_message() -> Any:
    room = require_access()
    body = ''
    image_url = None
    image_path = None

    if request.content_type and request.content_type.startswith('multipart/form-data'):
        body = (request.form.get('body') or '').strip()
        image_file = request.files.get('image')
    else:
        payload = request.get_json(silent=True) or {}
        body = (payload.get('body') or '').strip()
        image_file = None

    if len(body) > MAX_MESSAGE_LENGTH:
        return jsonify({'error': f'訊息不能超過 {MAX_MESSAGE_LENGTH} 字。'}), 400

    if image_file and image_file.filename:
        try:
            image_url, image_path = upload_image(image_file, room['id'])
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

    if not body and not image_url:
        return jsonify({'error': '文字或圖片至少要有一項。'}), 400

    session_id = ensure_session_id()
    now = datetime.now(timezone.utc)
    row = fetch_one('chat_rate_limits', {'session_id': f'eq.{session_id}'})
    if row:
        last_post_at = parse_timestamp(row.get('last_post_at'))
        if last_post_at and now.timestamp() - last_post_at.timestamp() < RATE_LIMIT_SECONDS:
            return jsonify({'error': f'發言太快了，請 {RATE_LIMIT_SECONDS} 秒後再試。'}), 429

    nickname = ensure_nickname()
    supabase_request(
        'POST',
        'chat_messages',
        json_body={'room_id': room['id'], 'nickname': nickname, 'body': body, 'image_url': image_url, 'image_path': image_path},
        prefer='return=minimal',
    )
    upsert_rate_limit(session_id)
    return jsonify({'ok': True})


@app.route('/api/messages/<message_id>', methods=['DELETE'])
def delete_message(message_id: str) -> Any:
    require_admin_token()
    supabase_request('PATCH', 'chat_messages', query={'id': f'eq.{message_id}'}, json_body={'deleted': True}, prefer='return=minimal')
    return jsonify({'ok': True})


def _cache_key_for_symbols(symbols: list[str]) -> str:
    return ','.join(symbols)


def _cached_tw_quotes(symbols: list[str]) -> dict[str, Any] | None:
    key = _cache_key_for_symbols(symbols)
    cached = TW_QUOTES_CACHE.get(key)
    if not cached:
        return None
    if time.time() - float(cached.get('ts') or 0) > TW_QUOTES_CACHE_SECONDS:
        TW_QUOTES_CACHE.pop(key, None)
        return None
    return cached.get('payload') if isinstance(cached.get('payload'), dict) else None


def _store_cached_tw_quotes(symbols: list[str], payload: dict[str, Any]) -> None:
    TW_QUOTES_CACHE[_cache_key_for_symbols(symbols)] = {'ts': time.time(), 'payload': payload}


def _tw_quote_name(symbol: str, info: dict[str, Any]) -> str:
    name_map = {
        '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2412': '中華電', '6505': '台塑化',
        '2308': '台達電', '2303': '聯電', '2881': '富邦金', '2882': '國泰金', '1303': '南亞',
        '1301': '台塑', '2002': '中鋼', '2886': '兆豐金', '2891': '中信金', '1216': '統一',
        '2382': '廣達', '2884': '玉山金', '2885': '元大金', '3711': '日月光投控', '2880': '華南金',
        '5880': '合庫金', '3045': '台灣大', '2883': '凱基金', '2207': '和泰車', '2912': '統一超',
        '3008': '大立光', '4904': '遠傳', '5871': '中租-KY', '6415': '矽力*-KY', '3034': '聯詠',
        '2892': '第一金', '1326': '台化', '2603': '長榮', '1101': '台泥', '2887': '台新金',
        '2327': '國巨', '2357': '華碩', '2379': '瑞昱', '4938': '和碩', '2408': '南亞科',
        '1590': '亞德客-KY', '3037': '欣興', '2356': '英業達', '2801': '彰銀', '2609': '陽明',
        '2615': '萬海', '8046': '南電', '0050': '元大台灣50', '0056': '元大高股息', '2606': '裕民',
    }
    return str(name_map.get(symbol) or info.get('shortName') or info.get('longName') or info.get('symbol') or symbol)


@app.route('/api/live-data')
def live_data() -> Any:
    scope = (request.args.get('scope') or 'all').strip().lower()
    payload: dict[str, Any] = {
        'generatedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'usQuotes': fetch_us_quotes_live(DOGGO_US_STOCK_SYMBOLS),
    }
    if scope != 'us-only':
        payload.update({
            'feed': fetch_feed_live(DOGGO_RSS_URLS),
            'weather': fetch_weather_live(WEATHER_SPOTS),
            'flightDeals': fetch_flight_deals_live(),
            'trumpTruth': fetch_trump_truth_live(),
        })
    return jsonify(payload)


@app.route('/api/tw-quotes')
def tw_quotes() -> Any:
    raw_symbols = (request.args.get('symbols') or '').strip()
    symbols = [s.strip() for s in raw_symbols.split(',') if s.strip()][:TW_QUOTES_MAX_SYMBOLS]
    if not symbols:
        return jsonify({'error': 'symbols is required'}), 400

    cached = _cached_tw_quotes(symbols)
    if cached is not None:
        return jsonify(cached)

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    as_of = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    for symbol in symbols:
        suffix = '.TW' if symbol.isdigit() or (len(symbol) == 4 and symbol[0] == '0') else '.TWO'
        ticker_symbol = symbol if '.' in symbol else f'{symbol}{suffix}'
        ticker = yf.Ticker(ticker_symbol)
        try:
            hist = ticker.history(period='2d', interval='1m', prepost=False)
            if hist is None or hist.empty:
                hist = ticker.history(period='5d', interval='1d')
            if hist is None or hist.empty:
                errors.append(f'{symbol}: empty history')
                continue

            close_series = hist['Close'].dropna()
            if close_series.empty:
                errors.append(f'{symbol}: empty close')
                continue

            last = float(close_series.iloc[-1])
            prev_close = None
            if 'Close' in hist and len(close_series) >= 2:
                prev_close = float(close_series.iloc[-2])
            try:
                fast = ticker.fast_info or {}
                prev_close = float(fast.get('previous_close') or fast.get('regular_market_previous_close') or prev_close or last)
                day_high = float(fast.get('day_high') or fast.get('regular_market_day_high') or last)
                day_low = float(fast.get('day_low') or fast.get('regular_market_day_low') or last)
            except Exception:
                prev_close = float(prev_close or last)
                high_series = hist['High'].dropna() if 'High' in hist else close_series
                low_series = hist['Low'].dropna() if 'Low' in hist else close_series
                day_high = float(high_series.iloc[-1]) if not high_series.empty else last
                day_low = float(low_series.iloc[-1]) if not low_series.empty else last

            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                info = {}

            change = last - prev_close
            change_pct = ((change / prev_close) * 100.0) if prev_close else 0.0
            series_tail = [round(float(v), 2) for v in close_series.tail(8).tolist() if v == v]
            items.append({
                'symbol': symbol,
                'name': _tw_quote_name(symbol, info),
                'price': round(last, 2),
                'change': round(change, 2),
                'changePct': round(change_pct, 2),
                'prevClose': round(prev_close, 2),
                'dayHigh': round(day_high, 2),
                'dayLow': round(day_low, 2),
                'series': series_tail,
            })
        except Exception as exc:  # noqa: BLE001
            errors.append(f'{symbol}: {exc}')

    payload: dict[str, Any] = {'asOf': as_of, 'items': items}
    if errors:
        payload['error'] = '; '.join(errors[:5])
    _store_cached_tw_quotes(symbols, payload)
    return jsonify(payload)


@app.route('/admin')
def admin() -> Any:
    require_admin_token()
    room = ensure_default_room()
    invites = supabase_request(
        'GET',
        'chat_invites',
        query={
            'room_id': f"eq.{room['id']}",
            'select': 'id,token,label,max_uses,use_count,expires_at,revoked,created_at',
            'order': 'created_at.desc',
        },
    ) or []
    base = request.host_url.rstrip('/')
    invite_items = []
    for invite in invites:
        item = dict(invite)
        item['url'] = f"{base}{url_for('enter')}?invite={invite['token']}"
        invite_items.append(item)
    return render_template('admin.html', room=room, invites=invite_items)


@app.route('/admin/invites', methods=['POST'])
def admin_create_invite() -> Any:
    token = request.headers.get('X-Admin-Token', '') or request.form.get('admin_token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'unauthorized'}), 401

    payload = request.get_json(silent=True) if request.is_json else None
    label = (payload or {}).get('label') if payload else request.form.get('label')
    label = (label or 'manual').strip()

    max_uses_raw = str((payload or {}).get('max_uses') if payload else (request.form.get('max_uses') or '')).strip()
    max_uses = int(max_uses_raw) if max_uses_raw else None
    if max_uses is not None and max_uses <= 0:
        return jsonify({'error': 'max_uses 必須大於 0'}), 400

    room = ensure_default_room()
    invite_token = create_invite(room['id'], label=label, max_uses=max_uses)
    base = request.host_url.rstrip('/')
    return jsonify({'ok': True, 'token': invite_token, 'url': f"{base}{url_for('enter')}?invite={invite_token}"})


@app.route('/healthz')
def healthz() -> Any:
    room = ensure_default_room()
    return jsonify({'ok': True, 'room': room['slug'], 'backend': 'supabase'})


with app.app_context():
    ensure_bucket_public()
    ensure_default_room()
    ensure_bootstrap_invite()


if __name__ == '__main__':
    port = int(os.environ.get('CHAT_PORT', '8787'))
    app.run(host='127.0.0.1', port=port, debug=False)
