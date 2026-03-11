"""Generate Atom feed with daily alpha score changes for RSS subscription."""

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
    """Generate an Atom feed XML file with alpha score changes.

    Args:
        changes: list of dicts with keys: ticker, name, direction, old_score,
                 new_score, delta, rank, primary_driver, factor_deltas
        date: run date string (YYYY-MM-DD)

    Returns:
        Path to the generated feed.xml
    """
    now = datetime.now(timezone.utc).isoformat()

    feed = Element("feed", xmlns="http://www.w3.org/2005/Atom")
    SubElement(feed, "title").text = "Athene - Alpha Score Changes"
    SubElement(feed, "subtitle").text = "Daily alpha score changes for S&P 500 + NASDAQ 100 stocks"
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

    # Load existing entries, but skip legacy tier-based feeds
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
    """Create an Atom entry element for a day's alpha score changes."""
    entry = Element("entry")

    improved = [c for c in changes if c["direction"] == "improved"]
    declined = [c for c in changes if c["direction"] == "declined"]

    SubElement(entry, "title").text = (
        f"{date}: {len(improved)} improved, {len(declined)} declined "
        f"({len(changes)} total)"
    )
    SubElement(entry, "id").text = f"{SITE_URL}/changes/{date}"
    SubElement(entry, "updated").text = now

    link = SubElement(entry, "link")
    link.set("href", f"{SITE_URL}/screener")
    link.set("rel", "alternate")

    # Build HTML content
    lines = [f"<h2>Alpha Score Changes for {date}</h2>"]

    if improved:
        lines.append("<h3>Improved</h3><ul>")
        for c in improved:
            lines.append(_format_change_html(c, "+"))
        lines.append("</ul>")

    if declined:
        lines.append("<h3>Declined</h3><ul>")
        for c in declined:
            lines.append(_format_change_html(c, ""))
        lines.append("</ul>")

    content = SubElement(entry, "content")
    content.set("type", "html")
    content.text = "\n".join(lines)

    return entry


def _format_change_html(c: dict, sign_prefix: str) -> str:
    """Format a single change as an HTML list item with factor deltas."""
    fd = c.get("factor_deltas", {})
    factors = []
    for name in ("vm", "ev", "timing"):
        val = fd.get(name)
        if val is not None:
            s = f"+{val:.1f}" if val >= 0 else f"{val:.1f}"
            factors.append(f"{name.upper()} {s}")
    factor_str = f" [{', '.join(factors)}]" if factors else ""
    delta_str = f"+{c['delta']:.1f}" if c["delta"] >= 0 else f"{c['delta']:.1f}"
    return (
        f'<li><strong>{c["ticker"]}</strong>: '
        f'{c["old_score"]:.1f} &rarr; {c["new_score"]:.1f} '
        f'({delta_str}){factor_str}</li>'
    )
