"""Separate rating (absolute) and ranking (relative) systems.

Rating: Absolute quality tier based on the stock's own composite score.
Ranking: Relative position by composite score for comparison.
"""

from __future__ import annotations

import json
import os

import pandas as pd

from engine.config import (
    SCORE_STRONG_BUY,
    SCORE_BUY,
    SCORE_HOLD_LOWER,
    SCORE_SELL,
    TIER_HYSTERESIS,
    TIER_LABELS,
    TIER_COLORS,
    OUTPUT_DIR,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)


def _assign_rating(score: float) -> str:
    """Assign rating tier based on absolute score thresholds."""
    if score >= SCORE_STRONG_BUY:
        return "strong_buy"
    if score >= SCORE_BUY:
        return "buy"
    if score >= SCORE_HOLD_LOWER:
        return "hold"
    if score >= SCORE_SELL:
        return "sell"
    return "strong_sell"


# Tier ordering for hysteresis comparison
_TIER_ORDER = ["strong_buy", "buy", "hold", "sell", "strong_sell"]
_TIER_BOUNDARIES = {
    ("strong_buy", "buy"): SCORE_STRONG_BUY,
    ("buy", "hold"): SCORE_BUY,
    ("hold", "sell"): SCORE_HOLD_LOWER,
    ("sell", "strong_sell"): SCORE_SELL,
}


def _apply_hysteresis(score: float, new_tier: str, prev_tier: str | None) -> str:
    """Apply hysteresis to prevent oscillation at tier boundaries.

    To change tier, the score must cross the boundary by ±TIER_HYSTERESIS points.
    For multi-tier jumps, steps through each boundary one at a time and stops
    at the furthest tier the score can reach with margin.
    """
    if prev_tier is None or prev_tier == new_tier:
        return new_tier

    prev_idx = _TIER_ORDER.index(prev_tier) if prev_tier in _TIER_ORDER else -1
    new_idx = _TIER_ORDER.index(new_tier) if new_tier in _TIER_ORDER else -1

    if prev_idx < 0 or new_idx < 0:
        return new_tier

    # Build ordered boundary list: [(idx_upper, idx_lower, threshold), ...]
    boundaries = []
    for (upper, lower), threshold in _TIER_BOUNDARIES.items():
        boundaries.append((_TIER_ORDER.index(upper), _TIER_ORDER.index(lower), threshold))
    boundaries.sort(key=lambda b: b[0])  # sort by tier index

    # Upgrading (moving to better tier = lower index)
    if new_idx < prev_idx:
        # Walk from prev_tier upward, checking each boundary
        current = prev_idx
        for idx_upper, idx_lower, threshold in reversed(boundaries):
            if idx_lower > current or idx_upper >= current:
                continue
            # This boundary is between idx_upper and idx_lower
            if score >= threshold + TIER_HYSTERESIS:
                current = idx_upper  # Crossed with margin -> advance
            else:
                break  # Blocked at this boundary
        return _TIER_ORDER[current]

    # Downgrading (moving to worse tier = higher index)
    if new_idx > prev_idx:
        # Walk from prev_tier downward, checking each boundary
        current = prev_idx
        for idx_upper, idx_lower, threshold in boundaries:
            if idx_upper < current or idx_lower <= current:
                continue
            # This boundary is between idx_upper and idx_lower
            if score <= threshold - TIER_HYSTERESIS:
                current = idx_lower  # Crossed with margin -> advance
            else:
                break  # Blocked at this boundary
        return _TIER_ORDER[current]

    return new_tier


def _load_previous_tiers() -> dict[str, str]:
    """Load previous tier assignments from history.json (latest date)."""
    history_path = os.path.join(OUTPUT_DIR, "history.json")
    if not os.path.exists(history_path):
        return {}
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
        if not history:
            return {}
        latest_date = sorted(history.keys())[-1]
        daily = history[latest_date]
        return {ticker: data.get("tier", "") for ticker, data in daily.items() if data.get("tier")}
    except Exception as e:
        log.warning(f"Failed to load previous tiers: {e}")
        return {}


def assign_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Assign absolute rating tiers and relative rankings.

    Rating: absolute (score thresholds, with hysteresis).
    Ranking: relative (position by composite score).

    Adds columns: rank, percentile, tier, tier_label, tier_color
    """
    result = df.copy()

    # Fill NaN composite scores with 50 (neutral)
    result["composite_score"] = result["composite_score"].fillna(50.0)

    # Relative ranking: 1 = highest composite score
    result["rank"] = result["composite_score"].rank(ascending=False, method="min").astype(int)
    result = result.sort_values("rank")

    # Percentile (0-1, higher = better)
    result["percentile"] = result["composite_score"].rank(pct=True).fillna(0.5)

    # Absolute rating with hysteresis
    prev_tiers = _load_previous_tiers()

    tiers = []
    raw_tiers = []
    for ticker, row in result.iterrows():
        score = row["composite_score"]
        raw_tier = _assign_rating(score)
        prev_tier = prev_tiers.get(str(ticker))
        tier = _apply_hysteresis(score, raw_tier, prev_tier)
        tiers.append(tier)
        raw_tiers.append(raw_tier)

    result["tier"] = tiers
    result["tier_raw"] = raw_tiers
    result["tier_label"] = result["tier"].map(TIER_LABELS)
    result["tier_color"] = result["tier"].map(TIER_COLORS)

    # Log tier distribution
    dist = result["tier_label"].value_counts()
    log.info(f"Tier distribution (absolute):\n{dist.to_string()}")

    return result
