"""Generate Atom feed with daily rating changes for RSS subscription."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

from engine.config import OUTPUT_DIR
from engine.utils.logger import get_logger

log = get_logger(__name__)

FEED_FILE = os.path.join(OUTPUT_DIR, "feed.xml")
SITE_URL = "https://athene.johnsonlee.io"


def generate_feed(changes: list[dict], date: str) -> str:
    """Generate an Atom feed XML file with rating changes.

    Args:
        changes: list of dicts with keys: ticker, name, old_tier, new_tier,
                 old_rank, new_rank, composite_score
        date: run date string (YYYY-MM-DD)

    Returns:
        Path to the generated feed.xml
    """
    now = datetime.now(timezone.utc).isoformat()

    feed = Element("feed", xmlns="http://www.w3.org/2005/Atom")
    SubElement(feed, "title").text = "Athene Stock Screener - Rating Changes"
    SubElement(feed, "subtitle").text = "Daily rating changes for S&P 500 + NASDAQ 100 stocks"
    SubElement(feed, "id").text = f"{SITE_URL}/feed.xml"
    SubElement(feed, "updated").text = now

    link_self = SubElement(feed, "link")
    link_self.set("href", f"{SITE_URL}/data/feed.xml")
    link_self.set("rel", "self")
    link_self.set("type", "application/atom+xml")

    link_alt = SubElement(feed, "link")
    link_alt.set("href", SITE_URL)
    link_alt.set("rel", "alternate")
    link_alt.set("type", "text/html")

    author = SubElement(feed, "author")
    SubElement(author, "name").text = "Athene Bot"

    # Load existing entries from previous feed (keep last 30 days)
    existing_entries = _load_existing_entries()

    # Create new entry for today's changes
    if changes:
        entry = _create_entry(changes, date, now)
        existing_entries.insert(0, entry)

    # Keep only last 30 entries
    existing_entries = existing_entries[:30]

    for entry_elem in existing_entries:
        feed.append(entry_elem)

    # Write feed
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    indent(feed, space="  ")
    tree = ElementTree(feed)
    tree.write(FEED_FILE, encoding="unicode", xml_declaration=True)

    log.info(f"Feed generated with {len(existing_entries)} entries at {FEED_FILE}")
    return FEED_FILE


def _load_existing_entries() -> list[Element]:
    """Load existing entry elements from previous feed.xml."""
    if not os.path.exists(FEED_FILE):
        return []
    try:
        from xml.etree.ElementTree import parse
        tree = parse(FEED_FILE)
        root = tree.getroot()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        return list(root.findall("atom:entry", ns))
    except Exception:
        return []


def _create_entry(changes: list[dict], date: str, now: str) -> Element:
    """Create an Atom entry element for a day's rating changes."""
    entry = Element("entry")

    upgrades = [c for c in changes if _tier_rank(c["new_tier"]) < _tier_rank(c["old_tier"])]
    downgrades = [c for c in changes if _tier_rank(c["new_tier"]) > _tier_rank(c["old_tier"])]

    SubElement(entry, "title").text = (
        f"{date}: {len(upgrades)} upgrades, {len(downgrades)} downgrades "
        f"({len(changes)} total changes)"
    )
    SubElement(entry, "id").text = f"{SITE_URL}/changes/{date}"
    SubElement(entry, "updated").text = now

    link = SubElement(entry, "link")
    link.set("href", f"{SITE_URL}/screener")
    link.set("rel", "alternate")

    # Build HTML content
    lines = [f"<h2>Rating Changes for {date}</h2>"]

    if upgrades:
        lines.append("<h3>Upgrades</h3><ul>")
        for c in upgrades:
            lines.append(
                f'<li><strong>{c["ticker"]}</strong>: '
                f'{_tier_label(c["old_tier"])} → {_tier_label(c["new_tier"])} '
                f'(score: {c["composite_score"]:.2f})</li>'
            )
        lines.append("</ul>")

    if downgrades:
        lines.append("<h3>Downgrades</h3><ul>")
        for c in downgrades:
            lines.append(
                f'<li><strong>{c["ticker"]}</strong>: '
                f'{_tier_label(c["old_tier"])} → {_tier_label(c["new_tier"])} '
                f'(score: {c["composite_score"]:.2f})</li>'
            )
        lines.append("</ul>")

    content = SubElement(entry, "content")
    content.set("type", "html")
    content.text = "\n".join(lines)

    return entry


TIER_ORDER = ["strong_buy", "buy", "hold", "sell", "strong_sell"]
TIER_LABEL_MAP = {
    "strong_buy": "Strong Buy",
    "buy": "Buy",
    "hold": "Hold",
    "sell": "Sell",
    "strong_sell": "Strong Sell",
}


def _tier_rank(tier: str) -> int:
    try:
        return TIER_ORDER.index(tier)
    except ValueError:
        return 99


def _tier_label(tier: str) -> str:
    return TIER_LABEL_MAP.get(tier, tier)
