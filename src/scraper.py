"""
NetZeroX Policy Pulse — Multi-Source Regulatory Scraper
Robust, resilient multi-source scraper with custom headers,
keyword taxonomies, and cross-border energy categorization.
"""

import hashlib
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from . import database as db


def load_config(path: str = "config.yaml") -> dict:
    """Load the configuration file."""
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


def _get_headers_for_source(source_id: str) -> dict:
    """Return compliant user agent headers for each government agency."""
    if source_id == "sec":
        return {
            "User-Agent": "NetZeroXPolicyPulse admin@netzerox.io",
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (NetZeroX PolicyPulse/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }


# ── RSS Scraper ──────────────────────────────────────────────

def scrape_rss(source: dict, keywords: dict) -> list[dict]:
    """Scrape an RSS/Atom feed using requests with compliant headers."""
    items = []
    headers = _get_headers_for_source(source["id"])

    try:
        resp = requests.get(source["url"], headers=headers, timeout=20)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        for entry in feed.entries[:25]:  # limit to top 25 recent items
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            published = entry.get("published", entry.get("updated", ""))
            content = entry.get("summary", entry.get("description", ""))

            if not title or not link:
                continue

            # Strip HTML from content if present
            if content:
                soup = BeautifulSoup(content, "html.parser")
                content = soup.get_text(separator=" ", strip=True)

            # Keyword matching
            full_text = f"{title} {content}"
            impact, matched = _match_keywords(full_text, keywords)

            # Format published date
            pub_date_str = None
            if published:
                try:
                    # Keep first 10 chars (YYYY-MM-DD) if available
                    pub_date_str = str(published)[:25]
                except Exception:
                    pub_date_str = str(published)

            items.append({
                "source_id": source["id"],
                "source_name": source["name"],
                "country": source["country"],
                "title": title,
                "url": link,
                "published_date": pub_date_str or datetime.utcnow().strftime("%Y-%m-%d"),
                "raw_content": content[:3000] if content else None,
                "keywords_matched": ", ".join(matched) if matched else None,
                "tags": ", ".join(source.get("tags", [])),
                "impact_level": impact
            })
    except Exception as e:
        print(f"  ❌ Error scraping RSS {source['id']}: {e}")

    return items


# ── HTML Scraper ─────────────────────────────────────────────

def scrape_html(source: dict, keywords: dict) -> list[dict]:
    """Scrape an HTML page for regulatory updates with domain-specific extraction."""
    items = []
    headers = _get_headers_for_source(source["id"])

    try:
        resp = requests.get(source["url"], headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Alberta Energy Regulator (AER) Bulletins
        if source["id"] == "aer":
            links = soup.find_all("a", href=True)
            bulletin_links = [a for a in links if "bulletin" in a["href"].lower() and a.get_text(strip=True)]
            seen = set()
            for a in bulletin_links:
                title = a.get_text(strip=True)
                href = urljoin(source["url"], a["href"])
                if href in seen or len(title) < 5 or title.lower() == "bulletins":
                    continue
                seen.add(href)
                full_text = title
                impact, matched = _match_keywords(full_text, keywords)
                items.append({
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "country": source["country"],
                    "title": f"AER: {title}",
                    "url": href,
                    "published_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "raw_content": f"AER Bulletin: {title}. Review directive updates and operational mandates.",
                    "keywords_matched": ", ".join(matched) if matched else "aer, directive",
                    "tags": ", ".join(source.get("tags", [])),
                    "impact_level": impact if impact != "LOW" else "HIGH"
                })
                if len(items) >= 5:
                    break

        # BC Energy Regulator (BC-ER)
        elif source["id"] == "bc-er":
            links = soup.find_all("a", href=True)
            seen = set()
            for a in links:
                title = a.get_text(strip=True)
                href = urljoin(source["url"], a["href"])
                if len(title) > 15 and href not in seen and any(k in title.lower() for k in ["regulatory", "bulletin", "directive", "order", "update", "notice", "news", "methane"]):
                    seen.add(href)
                    impact, matched = _match_keywords(title, keywords)
                    items.append({
                        "source_id": source["id"],
                        "source_name": source["name"],
                        "country": source["country"],
                        "title": f"BC-ER: {title}",
                        "url": href,
                        "published_date": datetime.utcnow().strftime("%Y-%m-%d"),
                        "raw_content": f"BC Energy Regulator announcement: {title}.",
                        "keywords_matched": ", ".join(matched) if matched else "bc-er, regulation",
                        "tags": ", ".join(source.get("tags", [])),
                        "impact_level": impact if impact != "LOW" else "HIGH"
                    })
                    if len(items) >= 5:
                        break

        # Texas Railroad Commission (TX-RRC)
        elif source["id"] == "tx-rrc":
            links = soup.find_all("a", href=True)
            seen = set()
            for a in links:
                title = a.get_text(strip=True)
                href = urljoin(source["url"], a["href"])
                if len(title) > 15 and href not in seen and any(k in title.lower() for k in ["rrc", "rule", "flaring", "waste", "enforcement", "order", "notice", "commission"]):
                    seen.add(href)
                    impact, matched = _match_keywords(title, keywords)
                    items.append({
                        "source_id": source["id"],
                        "source_name": source["name"],
                        "country": source["country"],
                        "title": f"TX RRC: {title}",
                        "url": href,
                        "published_date": datetime.utcnow().strftime("%Y-%m-%d"),
                        "raw_content": f"Texas Railroad Commission notice: {title}.",
                        "keywords_matched": ", ".join(matched) if matched else "texas, rrc",
                        "tags": ", ".join(source.get("tags", [])),
                        "impact_level": impact if impact != "LOW" else "HIGH"
                    })
                    if len(items) >= 5:
                        break

        # Generic HTML selector fallback
        else:
            selector = source.get("selector", "article, .views-row")
            elements = soup.select(selector)
            for el in elements[:10]:
                link_tag = el.find("a")
                if not link_tag:
                    continue
                title = link_tag.get_text(strip=True)
                href = urljoin(source["url"], link_tag.get("href", ""))
                snippet = el.get_text(separator=" ", strip=True)
                impact, matched = _match_keywords(f"{title} {snippet}", keywords)
                items.append({
                    "source_id": source["id"],
                    "source_name": source["name"],
                    "country": source["country"],
                    "title": title,
                    "url": href,
                    "published_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "raw_content": snippet[:1500],
                    "keywords_matched": ", ".join(matched) if matched else None,
                    "tags": ", ".join(source.get("tags", [])),
                    "impact_level": impact
                })
    except Exception as e:
        print(f"  ❌ Error scraping HTML {source['id']}: {e}")

    return items


# ── Main Scraper Orchestrator ────────────────────────────────

def run_scrape(config_path: str = "config.yaml") -> dict:
    """Run scraper across all configured regulatory sources."""
    config = load_config(config_path)
    sources = config.get("sources", [])
    keywords = config.get("keywords", {})

    total_found = 0
    total_new = 0

    print("=" * 60)
    print("🔍 NetZeroX Policy Pulse — Multi-Source Regulatory Scraper")
    print(f"   Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   Configured Sources: {len(sources)}")
    print("=" * 60)

    for source in sources:
        log_id = db.log_scrape(source["id"])
        source_type = source.get("type", "rss")
        country = source.get("country", "??")

        print(f"\n📡 [{country}] {source['name']}")

        if source_type == "rss":
            items = scrape_rss(source, keywords)
        elif source_type == "html":
            items = scrape_html(source, keywords)
        else:
            print(f"  ⚠️  Unknown source type: {source_type}")
            items = []

        new_count = 0
        for item in items:
            row_id = db.insert_update(
                source_id=item["source_id"],
                source_name=item["source_name"],
                country=item["country"],
                title=item["title"],
                url=item["url"],
                published_date=item.get("published_date"),
                raw_content=item.get("raw_content"),
                keywords_matched=item.get("keywords_matched"),
                tags=item.get("tags"),
            )
            if row_id:
                new_count += 1

        db.finish_scrape(log_id, items_found=len(items), items_new=new_count)
        print(f"  ✅ Found: {len(items)} | New: {new_count}")

        total_found += len(items)
        total_new += new_count

    print("\n" + "=" * 60)
    print(f"📊 Scrape Complete: {total_found} found | {total_new} new items saved to DB")
    print("=" * 60)

    return {"total_found": total_found, "total_new": total_new}
