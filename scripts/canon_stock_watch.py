#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PRODUCT_NAME = "Canon RF45mm f/1.2 STM"
PRODUCT_URL = "https://store.canon.com.tw/products/rf45mm-f12-stm"
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


def parse_status(html: str) -> dict:
    inventory_matches = [int(x) for x in re.findall(r'"inventory_quantity"\s*:\s*(\d+)', html)]
    available_match = re.search(r'"available"\s*:\s*(true|false)', html)
    sold_out = any(token in html for token in ["已售完", "sold_out", "out_of_stock"])
    title_match = re.search(r'<title>\s*(.*?)\s*</title>', html, re.S)

    max_inventory = max(inventory_matches) if inventory_matches else None
    available = available_match.group(1) == "true" if available_match else None
    in_stock = bool((max_inventory is not None and max_inventory > 0) or (available is True and not sold_out))

    return {
        "title": title_match.group(1).strip() if title_match else PRODUCT_NAME,
        "inventory": max_inventory,
        "available": available,
        "sold_out": sold_out,
        "in_stock": in_stock,
    }


def main() -> int:
    html = curl_text(PRODUCT_URL)
    status = parse_status(html)
    state = load_state()
    prev_in_stock = state.get("in_stock")

    save_state(status)

    if not status["in_stock"]:
        print("NO_REPLY")
        return 0

    if prev_in_stock is True:
        print("NO_REPLY")
        return 0

    inventory_text = str(status["inventory"]) if status["inventory"] is not None else "未知"
    print("Canon 補貨提醒")
    print(f"- 商品: {PRODUCT_NAME}")
    print(f"- 狀態: 目前疑似可下單，庫存數: {inventory_text}")
    print(f"- 連結: {PRODUCT_URL}")
    print("- 建議: 盡快點進去確認，官方商城頁面可能會隨時變動")
    return 0


if __name__ == "__main__":
    sys.exit(main())
