#!/usr/bin/env python3
"""Small dependency-free release gate for the public Doggo site."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.h2_count = 0
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}
        self.json_ld: list[str] = []
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "h1":
            self.h1_count += 1
        elif tag == "h2":
            self.h2_count += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = values.get("name") or values.get("property")
            if key:
                self.meta[key] = values.get("content", "")
        elif tag == "link" and values.get("rel"):
            self.links[values["rel"]] = values.get("href", "")
        elif tag == "script" and values.get("type") == "application/ld+json":
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._json_ld_parts is not None:
            self.json_ld.append("".join(self._json_ld_parts).strip())
            self._json_ld_parts = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    index_path = DOCS / "index.html"
    parser = PageParser()
    parser.feed(index_path.read_text(encoding="utf-8"))

    require(parser.h1_count == 1, f"expected one H1, found {parser.h1_count}", errors)
    require(parser.h2_count >= 5, f"expected useful H2 structure, found {parser.h2_count}", errors)
    require("狗狗情報小屋" in parser.title, "page title is not product-specific", errors)
    require(bool(parser.meta.get("description")), "meta description is missing", errors)
    require(parser.links.get("canonical") == "https://dog.xuan.tw/", "canonical URL is incorrect", errors)
    require(bool(parser.meta.get("og:title")), "Open Graph title is missing", errors)
    require(parser.meta.get("og:image") == "https://dog.xuan.tw/og.png", "Open Graph image is incorrect", errors)
    require(bool(parser.meta.get("twitter:card")), "Twitter card metadata is missing", errors)
    require(bool(parser.json_ld), "JSON-LD is missing", errors)
    for raw in parser.json_ld:
        try:
            json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON-LD: {exc}")

    required_files = ["404.html", "robots.txt", "sitemap.xml", "og.png", "style.css", "ui.js", "guestbook.js"]
    for filename in required_files:
        require((DOCS / filename).is_file(), f"missing docs/{filename}", errors)

    robots = (DOCS / "robots.txt").read_text(encoding="utf-8")
    sitemap = (DOCS / "sitemap.xml").read_text(encoding="utf-8")
    require("Sitemap: https://dog.xuan.tw/sitemap.xml" in robots, "robots sitemap entry is missing", errors)
    require("<loc>https://dog.xuan.tw/</loc>" in sitemap, "sitemap canonical URL is missing", errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("PASS: static site release gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
