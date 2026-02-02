"""Qualitative four-dimension composite scoring model (v3).

Replaces the previous 3-factor (fundamental/technical/sentiment) aggregation
with four investment-analysis dimensions:

    earningsVisibility  (30%)  = quality + growth
    valuationMargin     (25%)  = value
    catalystTimeline    (20%)  = trend + momentum + sentiment + volume
    downsideControl     (25%)  = safety + volatility

All scores remain on the 0-100 absolute scale.
"""

from __future__ import annotations

import pandas as pd

from engine.config import (
    WEIGHT_EARNINGS_VISIBILITY,
    WEIGHT_VALUATION_MARGIN,
    WEIGHT_CATALYST_TIMELINE,
    WEIGHT_DOWNSIDE_CONTROL,
    EV_WEIGHT_QUALITY,
    EV_WEIGHT_GROWTH,
    VM_WEIGHT_VALUE,
    CT_WEIGHT_TREND,
    CT_WEIGHT_MOMENTUM,
    CT_WEIGHT_SENTIMENT,
    CT_WEIGHT_VOLUME,
    DC_WEIGHT_SAFETY,
    DC_WEIGHT_VOLATILITY,
    # Legacy weights for backward-compat factor scores
    WEIGHT_FUNDAMENTAL,
    WEIGHT_TECHNICAL,
    WEIGHT_SENTIMENT,
    FUND_WEIGHT_VALUE,
    FUND_WEIGHT_QUALITY,
    FUND_WEIGHT_GROWTH,
    FUND_WEIGHT_SAFETY,
    TECH_WEIGHT_TREND,
    TECH_WEIGHT_MOMENTUM,
    TECH_WEIGHT_VOLATILITY,
    TECH_WEIGHT_VOLUME,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)

NEUTRAL = 50.0


def _val(series_or_scalar, default: float = NEUTRAL) -> pd.Series:
    """Ensure a Series with NaN filled to *default*."""
    if isinstance(series_or_scalar, pd.Series):
        return series_or_scalar.fillna(default)
    return pd.Series(dtype=float)


def compute_composite(
    fund_scored: pd.DataFrame,
    tech_scored: pd.DataFrame,
    sent_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute composite score via four qualitative dimensions.

    Accepts the fully-scored DataFrames (with sub-score columns) from the
    fundamental, technical, and sentiment analyzers.

    Returns:
        DataFrame indexed by ticker with dimension scores, legacy factor
        scores, composite_score, and weight columns.
    """
    # Merge all sub-scores into a single frame
    all_tickers: set[str] = set()
    for df in (fund_scored, tech_scored, sent_df):
        if df is not None and not df.empty:
            all_tickers.update(df.index)

    all_tickers_sorted = sorted(all_tickers)
    result = pd.DataFrame(index=all_tickers_sorted)
    result.index.name = "ticker"

    # Pull sub-scores (fill missing with neutral 50)
    def _get(df: pd.DataFrame | None, col: str) -> pd.Series:
        if df is not None and col in df.columns:
            return df[col].reindex(result.index).fillna(NEUTRAL)
        return pd.Series(NEUTRAL, index=result.index)

    # --- Building-block sub-scores ---
    quality = _get(fund_scored, "quality_score")
    growth = _get(fund_scored, "growth_score")
    value = _get(fund_scored, "value_score")
    safety = _get(fund_scored, "safety_score")

    trend = _get(tech_scored, "trend_score")
    momentum = _get(tech_scored, "momentum_score")
    volatility = _get(tech_scored, "volatility_score")
    volume = _get(tech_scored, "volume_score")

    sentiment = _get(sent_df, "sentiment_score")

    # --- Four qualitative dimensions (all 0-100) ---
    ev = EV_WEIGHT_QUALITY * quality + EV_WEIGHT_GROWTH * growth
    vm = VM_WEIGHT_VALUE * value
    ct = (CT_WEIGHT_TREND * trend + CT_WEIGHT_MOMENTUM * momentum
          + CT_WEIGHT_SENTIMENT * sentiment + CT_WEIGHT_VOLUME * volume)
    dc = DC_WEIGHT_SAFETY * safety + DC_WEIGHT_VOLATILITY * volatility

    result["earnings_visibility"] = ev
    result["valuation_margin"] = vm
    result["catalyst_timeline"] = ct
    result["downside_control"] = dc

    # --- Composite score ---
    result["composite_score"] = (
        WEIGHT_EARNINGS_VISIBILITY * ev
        + WEIGHT_VALUATION_MARGIN * vm
        + WEIGHT_CATALYST_TIMELINE * ct
        + WEIGHT_DOWNSIDE_CONTROL * dc
    )

    # --- Dimension weights (fixed, but stored for display/export) ---
    result["weight_earnings_visibility"] = WEIGHT_EARNINGS_VISIBILITY
    result["weight_valuation_margin"] = WEIGHT_VALUATION_MARGIN
    result["weight_catalyst_timeline"] = WEIGHT_CATALYST_TIMELINE
    result["weight_downside_control"] = WEIGHT_DOWNSIDE_CONTROL

    # --- Legacy 3-factor scores (for backward compat in frontend/history) ---
    result["fundamental_score"] = (
        FUND_WEIGHT_VALUE * value
        + FUND_WEIGHT_QUALITY * quality
        + FUND_WEIGHT_GROWTH * growth
        + FUND_WEIGHT_SAFETY * safety
    )
    result["technical_score"] = (
        TECH_WEIGHT_TREND * trend
        + TECH_WEIGHT_MOMENTUM * momentum
        + TECH_WEIGHT_VOLATILITY * volatility
        + TECH_WEIGHT_VOLUME * volume
    )
    result["sentiment_score"] = sentiment

    # Legacy weight columns
    result["weight_fundamental"] = WEIGHT_FUNDAMENTAL
    result["weight_technical"] = WEIGHT_TECHNICAL
    result["weight_sentiment"] = WEIGHT_SENTIMENT

    log.info(f"Composite scores computed for {len(result)} tickers "
             f"(4-dimension model, 0-100 scale)")
    return result
