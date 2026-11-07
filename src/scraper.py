"""
NetZeroX Policy Pulse — Multi-Source Scraper
Fetches regulatory updates from 8 US/Canada sources.
Supports RSS feeds (feedparser) and HTML pages (BeautifulSoup).
"""

import hashlib
import re
from datetime import datetime
from typing import Optional

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from . import database as db


# ── Configuration ────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> dict:
    """Load the config file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def _match_keywords(text: str, keywords: dict) -> tuple[str, list[str]]:
    """Check text against keyword lists. Returns (highest_level, matched_keywords)."""
    text_lower = text.lower()
    matched = []

    for kw in keywords.get("critical", []):
        if kw.lower() in text_lower:
            matched.append(kw)
    if matched:
        return "CRITICAL", matched

    for kw in keywords.get("high", []):
        if kw.lower() in text_lower:
            matched.append(kw)
    if matched:
        return "HIGH", matched

    for kw in keywords.get("medium", []):
        if kw.lower() in text_lower:
            matched.append(kw)
    if matched:
        return "MEDIUM", matched

    return "LOW", []


# ── RSS Scraper ──────────────────────────────────────────────

def scrape_rss(source: dict, keywords: dict) -> list[dict]:
    """Scrape an RSS/Atom feed and return structured items."""
    items = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            title = entry.get("title", "Untitled")
            link = entry.get("link", "")
            published = entry.get("published", entry.get("updated", ""))
            content = entry.get("summary", entry.get("description", ""))

            # Strip HTML from content
            if content:
                soup = BeautifulSoup(content, "html.parser")
                content = soup.get_text(separator=" ", strip=True)

            # Keyword matching
            full_text = f"{title} {content}"
            impact, matched = _match_keywords(full_text, keywords)

            items.append({
                "source_id": source["id"],
                "source_name": source["name"],
                "country": source["country"],
                "title": title.strip(),
                "url": link.strip(),
                "published_date": published,
                "raw_content": content[:2000] if content else None,
                "keywords_matched": ", ".join(matched) if matched else None,
                "tags": ", ".join(source.get("tags", [])),
            })
    except Exception as e:
        print(f"  ❌ Error scraping RSS {source['id']}: {e}")

    return items


# ── HTML Scraper ─────────────────────────────────────────────

def scrape_html(source: dict, keywords: dict) -> list[dict]:
    """Scrape an HTML page for regulatory updates."""
    items = []
    headers = {
        "User-Agent": "NetZeroX-PolicyPulse/0.1 (Regulatory Intelligence)"
    }
    try:
        resp = requests.get(source["url"], headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Use the configured CSS selector to find items
        selector = source.get("selector", "article, .views-row")
        elements = soup.select(selector)

        for el in elements[:20]:  # Limit to 20 items per page
            # Try to find a link and title
            link_tag = el.find("a")
            if not link_tag:
                continue

            title = link_tag.get_text(strip=True)
            href = link_tag.get("href", "")

            # Make relative URLs absolute
            if href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(source["url"])
                href = f"{parsed.scheme}://{parsed.netloc}{href}"

            # Get surrounding text as content
            content = el.get_text(separator=" ", strip=True)

            # Keyword matching
            full_text = f"{title} {content}"
            impact, matched = _match_keywords(full_text, keywords)

            if title and href:
                items.append({
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "country": source["country"],
                    "title": title[:300],
                    "url": href,
                    "published_date": None,
                    "raw_content": content[:2000] if content else None,
                    "keywords_matched": ", ".join(matched) if matched else None,
                    "tags": ", ".join(source.get("tags", [])),
                })
    except Exception as e:
        print(f"  ❌ Error scraping HTML {source['id']}: {e}")

    return items


# ── Master Scrape Orchestrator ───────────────────────────────

def run_scrape(config_path: str = "config.yaml"):
    """Run the full scrape across all configured sources."""
    config = load_config(config_path)
    keywords = config.get("keywords", {})
    sources = config.get("sources", [])

    print("=" * 60)
    print(f"🔍 NetZeroX Policy Pulse — Scraper Run")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Sources: {len(sources)}")
    print("=" * 60)

    total_found = 0
    total_new = 0

    for source in sources:
        source_id = source["id"]
        source_type = source["type"]
        log_id = db.log_scrape(source_id)

        print(f"\n📡 [{source['country']}] {source['name']}")

        try:
            if source_type == "rss":
                items = scrape_rss(source, keywords)
            elif source_type == "html":
                items = scrape_html(source, keywords)
            else:
                print(f"  ⚠️  Unknown type: {source_type}")
                db.finish_scrape(log_id, 0, 0, "error", f"Unknown type: {source_type}")
                continue

            new_count = 0
            for item in items:
                row_id = db.insert_update(**item)
                if row_id is not None:
                    new_count += 1

            total_found += len(items)
            total_new += new_count

            print(f"  ✅ Found: {len(items)} | New: {new_count}")
            db.finish_scrape(log_id, len(items), new_count)

        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            db.finish_scrape(log_id, 0, 0, "error", str(e))

    print("\n" + "=" * 60)
    print(f"📊 Total: {total_found} found | {total_new} new items stored")
    print("=" * 60)

    return {"total_found": total_found, "total_new": total_new}


# ── CLI Entry Point ──────────────────────────────────────────
if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.dirname(__file__)))
    db.init_db()
    run_scrape()
