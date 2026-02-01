"""Detect rating tier changes by comparing with previous rankings."""

from __future__ import annotations

import json
import os
from typing import Dict, List

import pandas as pd

from engine.config import OUTPUT_DIR
from engine.utils.logger import get_logger

log = get_logger(__name__)

PREV_RANKINGS_FILE = os.path.join(OUTPUT_DIR, "rankings.json")


def detect_changes(new_ranked: pd.DataFrame, universe: pd.DataFrame) -> List[Dict]:
    """Compare new rankings with previously saved rankings.json to find tier changes.

    Returns:
        List of dicts with keys: ticker, name, old_tier, new_tier,
        old_rank, new_rank, composite_score
    """
    prev = _load_previous()
    if not prev:
        log.info("No previous rankings found - skipping change detection")
        return []

    # Build lookup from previous
    prev_map = {r["ticker"]: r for r in prev}

    # Universe name lookup
    name_map = {}
    if not universe.empty:
        name_map = dict(zip(universe["ticker"], universe["name"]))

    changes = []
    for ticker, row in new_ranked.iterrows():
        new_tier = row.get("tier", "")
        old = prev_map.get(ticker)
        if not old:
            continue
        old_tier = old.get("tier", "")
        if old_tier and new_tier and old_tier != new_tier:
            changes.append({
                "ticker": ticker,
                "name": name_map.get(ticker, ticker),
                "old_tier": old_tier,
                "new_tier": new_tier,
                "old_rank": old.get("rank", 0),
                "new_rank": int(row.get("rank", 0)),
                "composite_score": float(row.get("composite_score", 0)),
            })

    log.info(f"Detected {len(changes)} rating changes")
    return changes


def _load_previous() -> list[dict]:
    """Load previous rankings.json."""
    if not os.path.exists(PREV_RANKINGS_FILE):
        return []
    try:
        with open(PREV_RANKINGS_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Failed to load previous rankings: {e}")
        return []


def format_changes_markdown(changes: List[Dict]) -> str:
    """Format changes as GitHub-flavored markdown for Job Summary."""
    if not changes:
        return "No rating changes detected.\n"

    upgrades = [c for c in changes if _tier_rank(c["new_tier"]) < _tier_rank(c["old_tier"])]
    downgrades = [c for c in changes if _tier_rank(c["new_tier"]) > _tier_rank(c["old_tier"])]

    lines = [f"# Rating Changes\n"]
    lines.append(f"**{len(upgrades)} upgrades, {len(downgrades)} downgrades** ({len(changes)} total)\n")

    if upgrades:
        lines.append("## Upgrades\n")
        lines.append("| Ticker | Name | Old | New | Score |")
        lines.append("|--------|------|-----|-----|-------|")
        for c in upgrades:
            lines.append(
                f"| **{c['ticker']}** | {c['name']} | {_label(c['old_tier'])} | "
                f"{_label(c['new_tier'])} | {c['composite_score']:.4f} |"
            )
        lines.append("")

    if downgrades:
        lines.append("## Downgrades\n")
        lines.append("| Ticker | Name | Old | New | Score |")
        lines.append("|--------|------|-----|-----|-------|")
        for c in downgrades:
            lines.append(
                f"| **{c['ticker']}** | {c['name']} | {_label(c['old_tier'])} | "
                f"{_label(c['new_tier'])} | {c['composite_score']:.4f} |"
            )
        lines.append("")

    return "\n".join(lines)


TIER_ORDER = ["strong_buy", "buy", "hold", "sell", "strong_sell"]
TIER_LABELS = {
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

def _label(tier: str) -> str:
    return TIER_LABELS.get(tier, tier)
