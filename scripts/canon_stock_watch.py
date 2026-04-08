#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PRODUCT_NAME = "Canon RF45mm f/1.2 STM"
TARGET_PRICE = 12900
SITES = [
    {
        "key": "canon",
        "name": "Canon 官方商城",
        "url": "https://store.canon.com.tw/products/rf45mm-f12-stm",
    },
    {
        "key": "momo",
        "name": "momo",
        "url": "https://www.momoshop.com.tw/TP/TP0007614/goodsDetail/TP00076140001334",
    },
    {
        "key": "pchome",
        "name": "PChome 24h",
        "url": "https://24h.pchome.com.tw/prod/DGBSE8-A900JNA85",
    },
]
STATE_PATH = Path(__file__).resolve().parent.parent / "memory" / "canon-stock-watch.json"


def curl_text(url: str) -> str:
    return subprocess.check_output(
        ["curl", "-A", "Mozilla/5.0", "-fsSL", "--max-time", "20", url],
        text=True,
    )


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


def parse_canon(html: str) -> dict:
    inventory_matches = [int(x) for x in re.findall(r'"inventory_quantity"\s*:\s*(\d+)', html)]
    max_inventory = max(inventory_matches) if inventory_matches else None
    has_notify = "已售完，貨到通知我" in html or "notify_me_when_stock_arrives" in html
    sold_out = any(token in html for token in ["sold_out", "out_of_stock", "已售完"])
    in_stock = bool(max_inventory and max_inventory > 0 and not has_notify and not sold_out)
    return {
        "inventory": max_inventory,
        "in_stock": in_stock,
        "note": "頁面顯示可登記貨到通知" if has_notify else "",
    }


def parse_momo(html: str) -> dict:
    sold_out = any(token in html for token in ["已售完", "貨到通知我", "暫無供貨"])
    can_cart = "加入購物車" in html
    preorder = "預購" in html
    price_match = re.search(r'"price":"?([0-9,]+)"?', html)
    price = int(price_match.group(1).replace(',', '')) if price_match else None
    price_ok = price is not None and price <= TARGET_PRICE
    in_stock = can_cart and not sold_out and price_ok
    if price is not None and price > TARGET_PRICE:
        note = f"價格偏高，目前 {price}"
    elif preorder and in_stock:
        note = "預購中"
    elif sold_out:
        note = "已售完或不可直接下單"
    else:
        note = ""
    return {"inventory": None, "in_stock": in_stock, "note": note}


def parse_pchome(html: str) -> dict:
    availability = re.search(r'"availability":"([^"]+)"', html)
    has_notify = "有貨通知我" in html
    in_stock = bool(availability and availability.group(1).endswith("InStock") and not has_notify)
    sold_out = "已售完" in html or "OutOfStock" in html or has_notify
    note = "頁面顯示有貨通知我" if has_notify else ("24h到貨" if "24h到貨" in html and in_stock else ("已售完" if sold_out else ""))
    return {"inventory": None, "in_stock": in_stock and not sold_out, "note": note}


def parse_site(site_key: str, html: str) -> dict:
    if site_key == "canon":
        return parse_canon(html)
    if site_key == "momo":
        return parse_momo(html)
    if site_key == "pchome":
        return parse_pchome(html)
    raise ValueError(site_key)


def main() -> int:
    state = load_state()
    prev_sites = state.get("sites", {})
    current_sites = {}
    alerts = []

    for site in SITES:
        html = curl_text(site["url"])
        status = parse_site(site["key"], html)
        current_sites[site["key"]] = status
        prev_in_stock = prev_sites.get(site["key"], {}).get("in_stock")
        if status["in_stock"] and prev_in_stock is not True:
            alerts.append({**site, **status})

    save_state({"sites": current_sites})

    if not alerts:
        print("NO_REPLY")
        return 0

    print("Canon 補貨提醒")
    print(f"- 商品: {PRODUCT_NAME}")
    for alert in alerts:
        detail = f"，{alert['note']}" if alert.get('note') else ""
        print(f"- {alert['name']}: 疑似可下單{detail}")
        print(f"  {alert['url']}")
    print("- 建議: 盡快點進去確認，商品頁可能隨時變動")
    return 0


if __name__ == "__main__":
    sys.exit(main())
