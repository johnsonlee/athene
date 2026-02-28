"""Qualitative four-dimension composite scoring model (v3+).

Replaces the previous 3-factor (fundamental/technical/sentiment) aggregation
with four investment-analysis dimensions:

    earningsVisibility  (15%)  = growth(70%) + quality(30%)
    valuationMargin     (15%)  = value (reduced — near-zero IC)
    catalystTimeline    (40%)  = trend(55%) + momentum(45%)
    downsideControl     (30%)  = volatility(65%) + safety(35%)

v18: IC-driven rebalance. Weights restructured based on forward-return IC evidence.
v19: Market timing integration — timing-adjusted weights and per-stock composite
     penalty modulated by defensive characteristics.

All scores remain on the 0-100 absolute scale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from engine.analyzers.market_timing import TimingResult

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
    # v17: cyclical risk in DC
    DC_WEIGHT_SAFETY_V17,
    DC_WEIGHT_VOLATILITY_V17,
    DC_WEIGHT_CYCLICAL_RISK,
    CYCLICAL_SECTORS,
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
    # Jurisdiction risk
    JURISDICTION_RISK,
    TICKER_JURISDICTION,
    # v17: commodity risk
    COMMODITY_RISK,
    TICKER_COMMODITY_RISK,
    # v18: trend gate
    TREND_GATE_THRESHOLD,
    TREND_GATE_MAX_PENALTY,
    TREND_GATE_SOFT_THRESHOLD,
    TREND_GATE_SOFT_PENALTY,
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
    cyclical_risk: pd.Series | None = None,
    sectors: pd.Series | None = None,
    timing: "TimingResult | None" = None,
) -> pd.DataFrame:
    """Compute composite score via four qualitative dimensions.

    Accepts the fully-scored DataFrames (with sub-score columns) from the
    fundamental, technical, sentiment, and analyst analyzers.

    Args:
        weight_overrides: Optional dict mapping dimension name to weight.
            Used by macro regime detection to shift weights in risk-on/off.
            Superseded by timing when provided.
        timing: Optional TimingResult from market_timing module. When provided,
            uses timing-adjusted weights (supersedes weight_overrides) and
            applies per-stock composite penalty modulated by DC score.

    Returns:
        DataFrame indexed by ticker with dimension scores, legacy factor
        scores, composite_score, and weight columns.
    """
    # v19: timing-adjusted weights supersede weight_overrides
    if timing is not None:
        _wo = timing.weight_adjustments
    else:
        _wo = weight_overrides or {}

    # Resolve dimension weights
    w_ev = _wo.get("earnings_visibility", WEIGHT_EARNINGS_VISIBILITY)
    w_vm = _wo.get("valuation_margin", WEIGHT_VALUATION_MARGIN)
    w_ct = _wo.get("catalyst_timeline", WEIGHT_CATALYST_TIMELINE)
    w_dc = _wo.get("downside_control", WEIGHT_DOWNSIDE_CONTROL)

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
    # v18: IC-driven composition — weights reflect actual predictive power
    ic_w = load_ic_weights()

    # EV: growth-led (v18: quality reduced from 60% to 30%, growth raised to 70%)
    ev = EV_WEIGHT_GROWTH * growth + EV_WEIGHT_QUALITY * quality
    log.info(f"EV composition: growth={EV_WEIGHT_GROWTH:.0%}, quality={EV_WEIGHT_QUALITY:.0%}")

    # VM: value only (unchanged)
    vm = VM_WEIGHT_VALUE * value

    # CT: trend + momentum only (v18: analyst removed, IR -0.19)
    ct = CT_WEIGHT_TREND * trend + CT_WEIGHT_MOMENTUM * momentum
    log.info(f"CT composition: trend={CT_WEIGHT_TREND:.0%}, momentum={CT_WEIGHT_MOMENTUM:.0%}")

    # DC: volatility-led (v18: volatility raised from 40% to 65%)
    dc = DC_WEIGHT_VOLATILITY * volatility + DC_WEIGHT_SAFETY * safety
    log.info(f"DC composition: volatility={DC_WEIGHT_VOLATILITY:.0%}, safety={DC_WEIGHT_SAFETY:.0%}")

    # --- v17: Cyclical risk — blend into DC for cyclical-sector tickers ---
    if cyclical_risk is not None:
        cyc = cyclical_risk.reindex(result.index).fillna(NEUTRAL)
        result["cyclical_risk_score"] = cyc

        # Build a sector lookup
        _sec_map: dict[str, str] = {}
        if sectors is not None:
            _sec_map = sectors.to_dict() if isinstance(sectors, pd.Series) else sectors

        # For cyclical tickers: DC = 0.50*safety + 0.30*volatility + 0.20*cyclical_risk
        # For non-cyclical: DC stays as is (safety + volatility only)
        _n_cycl = 0
        for ticker in result.index:
            sec = _sec_map.get(ticker)
            if sec and sec in CYCLICAL_SECTORS:
                dc.at[ticker] = (
                    DC_WEIGHT_SAFETY_V17 * safety.at[ticker]
                    + DC_WEIGHT_VOLATILITY_V17 * volatility.at[ticker]
                    + DC_WEIGHT_CYCLICAL_RISK * cyc.at[ticker]
                )
                _n_cycl += 1
        if _n_cycl:
            log.info(f"Cyclical risk blended into DC for {_n_cycl} ticker(s)")
    else:
        result["cyclical_risk_score"] = pd.Series(NEUTRAL, index=result.index)

    # --- Jurisdiction risk: apply DC penalty for high-risk domiciles ---
    _n_penalized = 0
    for ticker in result.index:
        jur_key = TICKER_JURISDICTION.get(ticker)
        if jur_key and jur_key in JURISDICTION_RISK:
            penalty_pts = JURISDICTION_RISK[jur_key]["dc_penalty"]
            dc.at[ticker] = max(0.0, dc.at[ticker] + penalty_pts)
            _n_penalized += 1
    if _n_penalized:
        log.info(f"Jurisdiction DC penalty applied to {_n_penalized} ticker(s)")

    # --- v17: Commodity risk: apply DC penalty for commodity-specific risks ---
    _n_commodity = 0
    for ticker in result.index:
        com_key = TICKER_COMMODITY_RISK.get(ticker)
        if com_key and com_key in COMMODITY_RISK:
            penalty_pts = COMMODITY_RISK[com_key]["dc_penalty"]
            dc.at[ticker] = max(0.0, dc.at[ticker] + penalty_pts)
            _n_commodity += 1
    if _n_commodity:
        log.info(f"Commodity DC penalty applied to {_n_commodity} ticker(s)")

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

    # --- v18: Trend gate — penalize stocks in clear downtrends ---
    # Prevents value traps: cheap stocks in downtrends shouldn't rank high.
    # Two tiers: hard penalty for deep downtrend, soft penalty for weak trend.
    trend_gate_penalty = pd.Series(0.0, index=result.index)
    for ticker in result.index:
        t_score = trend.at[ticker] if ticker in trend.index else 50.0
        if t_score < TREND_GATE_THRESHOLD:
            # Deep downtrend: linear penalty up to max
            severity = (TREND_GATE_THRESHOLD - t_score) / TREND_GATE_THRESHOLD
            trend_gate_penalty.at[ticker] = severity * TREND_GATE_MAX_PENALTY
        elif t_score < TREND_GATE_SOFT_THRESHOLD:
            # Weak trend: proportional soft penalty
            severity = (TREND_GATE_SOFT_THRESHOLD - t_score) / (TREND_GATE_SOFT_THRESHOLD - TREND_GATE_THRESHOLD)
            trend_gate_penalty.at[ticker] = severity * TREND_GATE_SOFT_PENALTY

    result["composite_score"] = (result["composite_score"] - trend_gate_penalty).clip(lower=0.0)
    result["trend_gate_penalty"] = trend_gate_penalty

    n_gated = (trend_gate_penalty > 0).sum()
    if n_gated > 0:
        log.info(f"Trend gate: {n_gated} tickers penalized "
                 f"(max penalty {trend_gate_penalty.max():.1f} pts)")

    # --- v19: Market timing penalty — per-stock, modulated by DC score ---
    if timing is not None and timing.composite_penalty > 0:
        from engine.analyzers.market_timing import modulate_penalty
        timing_penalty = pd.Series(0.0, index=result.index)
        for ticker in result.index:
            dc_val = dc.at[ticker] if ticker in dc.index else NEUTRAL
            timing_penalty.at[ticker] = modulate_penalty(timing.composite_penalty, dc_val)
        result["composite_score"] = (result["composite_score"] - timing_penalty).clip(lower=0.0)
        result["timing_penalty"] = timing_penalty
        result["market_timing_score"] = timing.market_timing_score
        result["timing_zone"] = timing.timing_zone
        n_penalized = (timing_penalty > 0).sum()
        log.info(f"Timing penalty: {n_penalized} tickers penalized "
                 f"(base={timing.composite_penalty:.1f}, "
                 f"max applied={timing_penalty.max():.1f} pts, "
                 f"zone={timing.timing_zone})")
    else:
        result["timing_penalty"] = 0.0
        result["market_timing_score"] = timing.market_timing_score if timing else 50.0
        result["timing_zone"] = timing.timing_zone if timing else "neutral"

    log.info(f"Composite scores computed for {len(result)} tickers "
             f"(4-dimension model, 0-100 scale)")
    return result
