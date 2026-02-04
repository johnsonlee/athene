"""Compute composite trend strength and classify trend state per sector."""

from __future__ import annotations

import pandas as pd

from engine.config import (
    TREND_WEIGHT_RELATIVE_STRENGTH,
    TREND_WEIGHT_BREADTH,
    TREND_WEIGHT_ANALYST_REVISIONS,
    TREND_WEIGHT_MOMENTUM,
    TREND_WEIGHT_VOLUME,
    TREND_STRONG_UPTREND,
    TREND_UPTREND,
    TREND_NEUTRAL,
    TREND_DOWNTREND,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)

_SIGNAL_WEIGHTS = {
    "relative_strength_score": TREND_WEIGHT_RELATIVE_STRENGTH,
    "breadth_score": TREND_WEIGHT_BREADTH,
    "analyst_revision_score": TREND_WEIGHT_ANALYST_REVISIONS,
    "momentum_score": TREND_WEIGHT_MOMENTUM,
    "volume_score": TREND_WEIGHT_VOLUME,
}


def _classify_trend(score: float) -> str:
    """Map composite score to trend state label."""
    if score >= TREND_STRONG_UPTREND:
        return "strong_uptrend"
    if score >= TREND_UPTREND:
        return "uptrend"
    if score >= TREND_NEUTRAL:
        return "neutral"
    if score >= TREND_DOWNTREND:
        return "downtrend"
    return "strong_downtrend"


def _primary_signal(row: pd.Series) -> str:
    """Identify the signal contributing most to deviation from neutral."""
    best_signal = "relative_strength"
    best_deviation = 0.0
    signal_names = {
        "relative_strength_score": "relative_strength",
        "breadth_score": "breadth",
        "analyst_revision_score": "analyst_revisions",
        "momentum_score": "momentum",
        "volume_score": "volume",
    }
    for col, name in signal_names.items():
        val = row.get(col, 50.0)
        weight = _SIGNAL_WEIGHTS.get(col, 0)
        deviation = abs(val - 50.0) * weight
        if deviation > best_deviation:
            best_deviation = deviation
            best_signal = name
    return best_signal


def score_sector_trends(trend_df: pd.DataFrame) -> pd.DataFrame:
    """Compute composite trend strength and classify trend state.

    Adds columns:
        trend_strength (0-100): weighted composite of 5 signal scores
        trend_state: 'strong_uptrend' | 'uptrend' | 'neutral' | 'downtrend' | 'strong_downtrend'
        primary_signal: name of strongest contributing signal
    """
    result = trend_df.copy()

    # Compute weighted composite
    result["trend_strength"] = sum(
        _SIGNAL_WEIGHTS[col] * result[col].fillna(50.0)
        for col in _SIGNAL_WEIGHTS
    ).round(1)

    # Classify trend state
    result["trend_state"] = result["trend_strength"].apply(_classify_trend)

    # Identify primary signal
    result["primary_signal"] = result.apply(_primary_signal, axis=1)

    log.info(f"Trend scoring complete: "
             f"{(result['trend_state'] == 'strong_uptrend').sum()} strong uptrend, "
             f"{(result['trend_state'] == 'uptrend').sum()} uptrend, "
             f"{(result['trend_state'] == 'neutral').sum()} neutral, "
             f"{(result['trend_state'] == 'downtrend').sum()} downtrend, "
             f"{(result['trend_state'] == 'strong_downtrend').sum()} strong downtrend")

    return result
