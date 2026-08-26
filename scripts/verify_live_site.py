#!/usr/bin/env python3
"""Dependency-free post-deploy smoke test for dog.xuan.tw."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import time
import urllib.error
import urllib.request


BASE_URL = os.environ.get("DOGGO_BASE_URL", "https://dog.xuan.tw").rstrip("/")
CACHE_BUSTER = str(int(time.time()))


def request(path: str, expected_status: int = 200, bust: bool = False) -> tuple[bytes, dict[str, str]]:
    suffix = f"{'&' if '?' in path else '?'}release_check={CACHE_BUSTER}" if bust else ""
    req = urllib.request.Request(
        f"{BASE_URL}{path}{suffix}",
        headers={"User-Agent": "doggo-release-gate/1.0"},
    )
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        body = response.read()
        status = response.status
        headers = {key.lower(): value for key, value in response.headers.items()}
    if status != expected_status:
        raise RuntimeError(f"{path}: expected HTTP {expected_status}, got {status}")
    return body, headers


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    html_raw, home_headers = request("/", bust=True)
    html = html_raw.decode("utf-8")
    require("狗狗情報小屋｜今天先看什麼" in html, "production title marker is missing")
    require("狀態與同步為展示資料" in html, "demo-data disclaimer is missing")
    require("cdn.jsdelivr.net" not in html, "third-party animation script is still deployed")
    require("style.css?v=75" in html and "ui.js?v=75" in html, "versioned assets are not deployed")
    require("https://dog.xuan.tw/og.png?v=75" in html, "versioned social preview is not deployed")
    csp = home_headers.get("content-security-policy", "")
    require("default-src 'self'" in csp and "object-src 'none'" in csp, "enforced CSP is missing")

    asset_checks = {
        "/style.css?v=75": "text/css",
        "/ui.js?v=75": "text/javascript",
        "/guestbook.js?v=75": "text/javascript",
        "/favicon.svg?v=75": "image/svg+xml",
        "/og.png": "image/png",
        "/robots.txt": "text/plain",
        "/sitemap.xml": "xml",
    }
    for path, content_type in asset_checks.items():
        body, headers = request(path, bust=True)
        require(body, f"{path}: empty response")
        require(content_type in headers.get("content-type", ""), f"{path}: incorrect content type")
        if path.startswith("/ui.js"):
            require(b"triggerDataRefresh" not in body and b"/api/refresh-data" not in body, "old refresh POST code is still deployed")

    missing_body, _ = request("/release-gate-missing-page", expected_status=404, bust=True)
    require("迷路了｜狗狗情報小屋" in missing_body.decode("utf-8"), "custom 404 page is missing")

    for path in [
        "/api/live-data",
        "/api/tw-quotes?symbols=2330",
        "/api/us-quotes",
        "/api/feed",
        "/api/weather",
        "/api/flight-deals",
        "/api/trump-truth",
    ]:
        body, headers = request(path)
        require("application/json" in headers.get("content-type", ""), f"{path}: not JSON")
        json.loads(body)

    request("/api/refresh-data", expected_status=405)
    data_raw, _ = request("/data.json", bust=True)
    data = json.loads(data_raw)
    generated_at = datetime.fromisoformat(data["generatedAt"].replace("Z", "+00:00"))
    age_seconds = (datetime.now(timezone.utc) - generated_at).total_seconds()
    require(age_seconds < 1800, f"data.json is stale ({int(age_seconds)} seconds old)")
    require(len(data.get("quotes", {}).get("items", [])) > 0, "data.json has no quote items")

    print("PASS: live doggo release gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
