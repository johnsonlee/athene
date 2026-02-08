"""Qualitative four-dimension composite scoring model (v3+).

Replaces the previous 3-factor (fundamental/technical/sentiment) aggregation
with four investment-analysis dimensions:

    earningsVisibility  (30%)  = quality + growth
    valuationMargin     (25%)  = value
    catalystTimeline    (20%)  = trend + momentum + analyst + sentiment + volume
    downsideControl     (25%)  = safety + volatility

v7: Incorporates data completeness — applies a penalty to composite_score
when a large fraction of metrics are missing (data_completeness < 0.5).

v8: Added analyst revision momentum to Catalyst Timeline (20% of CT).
Reweighted CT: trend 25% + momentum 25% + analyst 20% + sentiment 15% + volume 15%.

v9: Accepts optional weight_overrides for macro regime-adjusted dimension weights.
Risk-on shifts +5% to CT from DC; risk-off shifts +5% to DC from CT.

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
    CT_WEIGHT_ANALYST,
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
from engine.scorer.ic_weights import load_ic_weights, ic_weighted_avg, log_ic_status
from engine.utils.logger import get_logger

log = get_logger(__name__)

NEUTRAL = 50.0

# Metric-level score columns to forward from fund_scored for IC tracking
_METRIC_SCORE_COLS = (
    "pe_score", "forward_pe_score", "pb_score", "ps_score",
    "roe_score", "roa_score", "margin_score",
    "rev_growth_score", "earn_growth_score",
    "debt_equity_score", "fcf_yield_score", "current_ratio_score",
)


def _val(series_or_scalar, default: float = NEUTRAL) -> pd.Series:
    """Ensure a Series with NaN filled to *default*."""
    if isinstance(series_or_scalar, pd.Series):
        return series_or_scalar.fillna(default)
    return pd.Series(dtype=float)


def compute_composite(
    fund_scored: pd.DataFrame,
    tech_scored: pd.DataFrame,
    sent_df: pd.DataFrame,
    analyst_scored: pd.DataFrame | None = None,
    weight_overrides: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Compute composite score via four qualitative dimensions.

    Accepts the fully-scored DataFrames (with sub-score columns) from the
    fundamental, technical, sentiment, and analyst analyzers.

    Args:
        weight_overrides: Optional dict mapping dimension name to weight.
            Used by macro regime detection to shift weights in risk-on/off.

    Returns:
        DataFrame indexed by ticker with dimension scores, legacy factor
        scores, composite_score, and weight columns.
    """
    # Resolve dimension weights (regime-adjusted or default)
    w_ev = (weight_overrides or {}).get("earnings_visibility", WEIGHT_EARNINGS_VISIBILITY)
    w_vm = (weight_overrides or {}).get("valuation_margin", WEIGHT_VALUATION_MARGIN)
    w_ct = (weight_overrides or {}).get("catalyst_timeline", WEIGHT_CATALYST_TIMELINE)
    w_dc = (weight_overrides or {}).get("downside_control", WEIGHT_DOWNSIDE_CONTROL)

    # Merge all sub-scores into a single frame
    all_tickers: set[str] = set()
    for df in (fund_scored, tech_scored, sent_df, analyst_scored):
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

    analyst = _get(analyst_scored, "analyst_score")

    # --- v7: Store building-block sub-scores for IC tracking ---
    result["value_score"] = value
    result["quality_score"] = quality
    result["growth_score"] = growth
    result["safety_score"] = safety
    result["trend_score"] = trend
    result["momentum_score"] = momentum
    result["volatility_score"] = volatility
    result["volume_score"] = volume
    result["analyst_score"] = analyst

    # --- v16: Forward metric-level scores for IC tracking ---
    for col in _METRIC_SCORE_COLS:
        if fund_scored is not None and col in fund_scored.columns:
            result[col] = fund_scored[col].reindex(result.index).fillna(NEUTRAL)

    # --- Four qualitative dimensions (all 0-100) ---
    # v16: IC-weighted sub-score aggregation within dimensions
    ic_w = load_ic_weights()

    ev_components = {"quality_score": quality, "growth_score": growth}
    ev = ic_weighted_avg(ev_components, ic_w)
    log_ic_status("EV", list(ev_components.keys()), ic_w)

    vm = VM_WEIGHT_VALUE * value

    ct_components = {
        "trend_score": trend, "momentum_score": momentum,
        "analyst_score": analyst,
    }
    ct = ic_weighted_avg(ct_components, ic_w)
    log_ic_status("CT", list(ct_components.keys()), ic_w)

    dc_components = {"safety_score": safety, "volatility_score": volatility}
    dc = ic_weighted_avg(dc_components, ic_w)
    log_ic_status("DC", list(dc_components.keys()), ic_w)

    result["earnings_visibility"] = ev
    result["valuation_margin"] = vm
    result["catalyst_timeline"] = ct
    result["downside_control"] = dc

    # --- Composite score (v9: uses regime-adjusted weights) ---
    result["composite_score"] = (
        w_ev * ev + w_vm * vm + w_ct * ct + w_dc * dc
    )

    # --- Dimension weights (v9: stores actual used weights, may differ from defaults) ---
    result["weight_earnings_visibility"] = w_ev
    result["weight_valuation_margin"] = w_vm
    result["weight_catalyst_timeline"] = w_ct
    result["weight_downside_control"] = w_dc

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

    # --- v7: Data completeness penalty ---
    # Combine fundamental and technical data completeness.  Sentiment has
    # only one metric (compound) so it doesn't affect completeness much.
    # Note: default to 0.0 (not NEUTRAL) — missing ticker = zero completeness.
    def _get_completeness(df: pd.DataFrame | None, col: str) -> pd.Series:
        if df is not None and col in df.columns:
            return df[col].reindex(result.index).fillna(0.0)
        return pd.Series(0.0, index=result.index)

    fund_comp = _get_completeness(fund_scored, "fund_data_completeness")
    tech_comp = _get_completeness(tech_scored, "tech_data_completeness")
    # Weight fundamental data slightly more (12 metrics vs 6 technical)
    data_completeness = 0.67 * fund_comp + 0.33 * tech_comp
    result["data_completeness"] = data_completeness

    # Apply penalty when data completeness is low.
    # Linear penalty: full 5-point penalty at 0% completeness,
    # zero penalty at ≥50% completeness.
    penalty = ((0.50 - data_completeness.clip(upper=0.50)) / 0.50) * 5.0
    result["composite_score"] = (result["composite_score"] - penalty).clip(lower=0.0)
    result["data_quality_penalty"] = penalty

    low_data = (data_completeness < 0.50).sum()
    if low_data > 0:
        log.info(f"Data completeness: {low_data} tickers below 50% "
                 f"(penalty applied, max {penalty.max():.1f} pts)")

    log.info(f"Composite scores computed for {len(result)} tickers "
             f"(4-dimension model, 0-100 scale)")
    return result
