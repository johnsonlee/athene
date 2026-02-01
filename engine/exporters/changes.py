"""Detect rating tier changes with factor attribution."""

from __future__ import annotations

import json
import os
from typing import Dict, List

import pandas as pd

from engine.config import OUTPUT_DIR, WEIGHT_FUNDAMENTAL, WEIGHT_TECHNICAL, WEIGHT_SENTIMENT
from engine.utils.logger import get_logger

log = get_logger(__name__)

PREV_RANKINGS_FILE = os.path.join(OUTPUT_DIR, "rankings.json")


def detect_changes(new_ranked: pd.DataFrame, universe: pd.DataFrame) -> List[Dict]:
    """Compare new rankings with previously saved rankings.json to find tier changes.

    Includes factor attribution: identifies primary driver of each change.

    Returns:
        List of dicts with keys: ticker, name, old_tier, new_tier,
        old_rank, new_rank, composite_score, primary_driver, deltas
    """
    prev = _load_previous()
    if not prev:
        log.info("No previous rankings found - skipping change detection")
        return []

    prev_map = {r["ticker"]: r for r in prev}
    prev_history = _load_previous_subscores()

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
            change: Dict = {
                "ticker": ticker,
                "name": name_map.get(ticker, ticker),
                "old_tier": old_tier,
                "new_tier": new_tier,
                "old_rank": old.get("rank", 0),
                "new_rank": int(row.get("rank", 0)),
                "composite_score": float(row.get("composite_score", 0)),
            }

            # Factor attribution
            prev_sub = prev_history.get(str(ticker), {})
            if prev_sub:
                deltas = {}
                factors = [
                    ("fundamental", "fundamental_score", WEIGHT_FUNDAMENTAL),
                    ("technical", "technical_score", WEIGHT_TECHNICAL),
                    ("sentiment", "sentiment_score", WEIGHT_SENTIMENT),
                ]
                max_delta = 0.0
                driver = None
                for name, key, weight in factors:
                    old_val = prev_sub.get(key)
                    new_val = row.get(key)
                    if old_val is not None and new_val is not None and pd.notna(new_val):
                        d = (float(new_val) - float(old_val)) * weight
                        deltas[name] = round(d, 2)
                        if abs(d) > max_delta:
                            max_delta = abs(d)
                            driver = name

                change["deltas"] = deltas
                change["primary_driver"] = driver

            changes.append(change)

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


def _load_previous_subscores() -> dict[str, dict]:
    """Load previous sub-scores from history.json (latest date)."""
    history_path = os.path.join(OUTPUT_DIR, "history.json")
    if not os.path.exists(history_path):
        return {}
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
        if not history:
            return {}
        latest_date = sorted(history.keys())[-1]
        return history[latest_date]
    except Exception as e:
        log.warning(f"Failed to load previous sub-scores: {e}")
        return {}


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
        lines.append("| Ticker | Name | Old | New | Score | Driver |")
        lines.append("|--------|------|-----|-----|-------|--------|")
        for c in upgrades:
            driver = c.get("primary_driver", "")
            lines.append(
                f"| **{c['ticker']}** | {c['name']} | {_label(c['old_tier'])} | "
                f"{_label(c['new_tier'])} | {c['composite_score']:.1f} | {driver} |"
            )
        lines.append("")

    if downgrades:
        lines.append("## Downgrades\n")
        lines.append("| Ticker | Name | Old | New | Score | Driver |")
        lines.append("|--------|------|-----|-----|-------|--------|")
        for c in downgrades:
            driver = c.get("primary_driver", "")
            lines.append(
                f"| **{c['ticker']}** | {c['name']} | {_label(c['old_tier'])} | "
                f"{_label(c['new_tier'])} | {c['composite_score']:.1f} | {driver} |"
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
