"""Detect significant alpha score changes with factor attribution."""

from __future__ import annotations

import json
import os
from typing import Dict, List

import pandas as pd

from engine.config import OUTPUT_DIR
from engine.utils.logger import get_logger

log = get_logger(__name__)

PREV_RANKINGS_FILE = os.path.join(OUTPUT_DIR, "rankings.json")

# Minimum alpha_score change to be considered significant
ALPHA_CHANGE_THRESHOLD = 5.0


def detect_changes(new_ranked: pd.DataFrame, universe: pd.DataFrame) -> List[Dict]:
    """Compare new rankings with previous rankings.json to find significant alpha_score changes.

    Includes factor attribution: identifies which of VM/EV/Timing drove the change.

    Returns:
        List of dicts with keys: ticker, name, direction, old_score, new_score,
        delta, rank, primary_driver, factor_deltas
    """
    prev = _load_previous()
    if not prev:
        log.info("No previous rankings found - skipping change detection")
        return []

    prev_map = {r["ticker"]: r for r in prev}

    # Universe name lookup
    name_map = {}
    if not universe.empty:
        name_map = dict(zip(universe["ticker"], universe["name"]))

    changes = []
    for ticker, row in new_ranked.iterrows():
        new_alpha = row.get("alpha_score")
        if new_alpha is None or pd.isna(new_alpha):
            continue

        old = prev_map.get(ticker)
        if not old:
            continue
        old_alpha = old.get("alpha_score")
        if old_alpha is None:
            continue

        delta = float(new_alpha) - float(old_alpha)
        if abs(delta) < ALPHA_CHANGE_THRESHOLD:
            continue

        direction = "improved" if delta > 0 else "declined"

        change: Dict = {
            "ticker": ticker,
            "name": name_map.get(ticker, ticker),
            "direction": direction,
            "old_score": round(float(old_alpha), 1),
            "new_score": round(float(new_alpha), 1),
            "delta": round(delta, 1),
            "rank": int(row.get("rank", 0)),
        }

        # Factor attribution: VM, EV, Timing
        factor_deltas = {}
        factors = [
            ("vm", "alpha_vm"),
            ("ev", "alpha_ev"),
            ("timing", "alpha_timing"),
        ]
        max_abs_delta = 0.0
        driver = None
        for name, key in factors:
            old_val = old.get(key)
            new_val = row.get(key)
            if old_val is not None and new_val is not None and pd.notna(new_val):
                d = round(float(new_val) - float(old_val), 1)
                factor_deltas[name] = d
                if abs(d) > max_abs_delta:
                    max_abs_delta = abs(d)
                    driver = name

        change["factor_deltas"] = factor_deltas
        change["primary_driver"] = driver

        changes.append(change)

    # Sort by absolute delta descending
    changes.sort(key=lambda c: abs(c["delta"]), reverse=True)

    log.info(f"Detected {len(changes)} significant alpha score changes (threshold: \u00b1{ALPHA_CHANGE_THRESHOLD})")
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
        return "No significant alpha score changes detected.\n"

    improved = [c for c in changes if c["direction"] == "improved"]
    declined = [c for c in changes if c["direction"] == "declined"]

    lines = ["# Alpha Score Changes\n"]
    lines.append(f"**{len(improved)} improved, {len(declined)} declined** ({len(changes)} total, threshold: \u00b1{ALPHA_CHANGE_THRESHOLD})\n")

    if improved:
        lines.append("## Improved\n")
        lines.append("| Ticker | Name | Old | New | \u0394 | VM | EV | Timing |")
        lines.append("|--------|------|-----|-----|---|----|----|--------|")
        for c in improved:
            fd = c.get("factor_deltas", {})
            lines.append(
                f"| **{c['ticker']}** | {c['name']} | {c['old_score']:.1f} | "
                f"{c['new_score']:.1f} | +{c['delta']:.1f} | "
                f"{_fmt_delta(fd.get('vm'))} | {_fmt_delta(fd.get('ev'))} | {_fmt_delta(fd.get('timing'))} |"
            )
        lines.append("")

    if declined:
        lines.append("## Declined\n")
        lines.append("| Ticker | Name | Old | New | \u0394 | VM | EV | Timing |")
        lines.append("|--------|------|-----|-----|---|----|----|--------|")
        for c in declined:
            fd = c.get("factor_deltas", {})
            lines.append(
                f"| **{c['ticker']}** | {c['name']} | {c['old_score']:.1f} | "
                f"{c['new_score']:.1f} | {c['delta']:.1f} | "
                f"{_fmt_delta(fd.get('vm'))} | {_fmt_delta(fd.get('ev'))} | {_fmt_delta(fd.get('timing'))} |"
            )
        lines.append("")

    return "\n".join(lines)


def _fmt_delta(val: float | None) -> str:
    """Format a factor delta with sign."""
    if val is None:
        return "\u2014"
    return f"+{val:.1f}" if val >= 0 else f"{val:.1f}"
