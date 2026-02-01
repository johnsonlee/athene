"""Rank tickers by composite score and assign tier labels."""

from __future__ import annotations

import pandas as pd

from engine.config import (
    TIER_STRONG_BUY,
    TIER_BUY,
    TIER_HOLD_LOWER,
    TIER_SELL,
    TIER_LABELS,
    TIER_COLORS,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)


def assign_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Assign tier labels based on composite_score percentile rank.

    Adds columns: rank, percentile, tier, tier_label, tier_color

    Returns:
        DataFrame sorted by rank (best first).
    """
    result = df.copy()

    # Rank: 1 = highest composite score
    result["rank"] = result["composite_score"].rank(ascending=False, method="min").astype(int)
    result = result.sort_values("rank")

    # Percentile (0-1, higher = better)
    n = len(result)
    result["percentile"] = result["composite_score"].rank(pct=True)

    # Assign tiers
    def _tier(pct: float) -> str:
        if pct >= TIER_STRONG_BUY:
            return "strong_buy"
        elif pct >= TIER_BUY:
            return "buy"
        elif pct >= TIER_HOLD_LOWER:
            return "hold"
        elif pct >= TIER_SELL:
            return "sell"
        else:
            return "strong_sell"

    result["tier"] = result["percentile"].apply(_tier)
    result["tier_label"] = result["tier"].map(TIER_LABELS)
    result["tier_color"] = result["tier"].map(TIER_COLORS)

    # Log tier distribution
    dist = result["tier_label"].value_counts()
    log.info(f"Tier distribution:\n{dist.to_string()}")

    return result
