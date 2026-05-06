"""Three-factor multiplicative alpha scoring model.

Score = VM × EV × Timing / K

The model predicts forward excess return based on three factors:
  VM     — mispricing: how far is price from intrinsic value?
  EV     — fundamental support (with earnings direction): is the opportunity real?
  Timing — cycle position + reversal: when will the opportunity be realized?

All three factors must be present for a strong signal (multiplicative structure).
DC (downside control) is NOT part of scoring — it moves to position sizing.

Layer architecture:
  Layer 1: Score (this module) — pure alpha signal for ranking
  Layer 2: Position sizing (separate) — DC + market timing → capital allocation
"""

from __future__ import annotations

import pandas as pd

from engine.config import (
    ALPHA_MODEL_K,
    ALPHA_MODEL_TIMING_ALPHA,
    ALPHA_MODEL_DIRECTION_CENTER,
    ALPHA_MODEL_DIRECTION_RANGE,
    ALPHA_MODEL_EV_QUALITY_WEIGHT,
    ALPHA_MODEL_EV_GROWTH_WEIGHT,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)

NEUTRAL = 50.0


def _safe_get(df: pd.DataFrame | None, col: str, index: pd.Index) -> pd.Series:
    """Get column from DataFrame, reindex and fill NaN with NEUTRAL."""
    if df is not None and col in df.columns:
        return df[col].reindex(index).fillna(NEUTRAL)
    return pd.Series(NEUTRAL, index=index)


def compute_direction_multiplier(
    analyst_revision: pd.Series,
    growth_direction: pd.Series,
) -> pd.Series:
    """Map earnings direction signals to [0.2, 1.5] multiplier.

    Args:
        analyst_revision: normalized to [-1, 1]. Positive = upgrades.
        growth_direction: normalized to [-1, 1]. Positive = accelerating.

    Returns:
        Series of multiplier values in [0.2, 1.5].
        Center (0.85) when direction is neutral — slight discount for uncertainty.
    """
    raw = 0.5 * analyst_revision + 0.5 * growth_direction
    return ALPHA_MODEL_DIRECTION_CENTER + ALPHA_MODEL_DIRECTION_RANGE * raw


def compute_alpha_score(
    fund_scored: pd.DataFrame,
    tech_scored: pd.DataFrame,
    analyst_scored: pd.DataFrame | None = None,
    timing_alpha: float = ALPHA_MODEL_TIMING_ALPHA,
) -> pd.DataFrame:
    """Compute three-factor multiplicative alpha score.

    Runs in parallel with legacy factor_model — does NOT replace it.

    Args:
        fund_scored: DataFrame with value_score, quality_score, growth_score columns.
        tech_scored: DataFrame with trend_score, reversal_score columns.
        analyst_scored: DataFrame with revision_momentum_score column.
        timing_alpha: weight of reversal vs cycle_upside in timing. Default 0.5.

    Returns:
        DataFrame indexed by ticker with:
          - alpha_score: final score [0, 100]
          - alpha_vm, alpha_ev, alpha_timing: component values
          - alpha_visibility, alpha_multiplier: EV sub-components
    """
    # Build common index from all inputs
    all_tickers: set[str] = set()
    for df in (fund_scored, tech_scored, analyst_scored):
        if df is not None and not df.empty:
            all_tickers.update(df.index)
    idx = pd.Index(sorted(all_tickers))
    result = pd.DataFrame(index=idx)
    result.index.name = "ticker"

    # --- Factor 1: VM (Mispricing) ---
    # Growth-adjusted forward PE + FCF yield. No PB (anti-signal for tech).
    #
    # Three inputs, each answering a different question:
    #   pe_score       → Is the current price expensive?
    #   growth_adj     → Can growth support this price? (high growth = PE discount)
    #   fcf_yield_score → Does the company generate real cash?
    #
    # vm = pe_score * growth_adj * 0.6 + fcf_yield_score * 0.4

    # Use forward PE when available (forward-looking), fall back to trailing PE
    forward_pe_s = _safe_get(fund_scored, "forward_pe_score", idx)
    trailing_pe_s = _safe_get(fund_scored, "pe_score", idx)
    # Forward PE defaults to NEUTRAL (50) when missing — use trailing as fallback
    pe_base = forward_pe_s.copy()
    missing_forward = (forward_pe_s == NEUTRAL) & (trailing_pe_s != NEUTRAL)
    pe_base[missing_forward] = trailing_pe_s[missing_forward]

    # Growth adjustment: high growth → PE looks cheaper (multiplier > 1)
    # earn_growth_score ∈ [0, 100] → growth_adj ∈ [0.5, 1.5]
    earn_growth_s = _safe_get(fund_scored, "earn_growth_score", idx)
    growth_adj = 0.5 + earn_growth_s / 100.0

    # FCF yield score: cash generation ability
    fcf_yield_s = _safe_get(fund_scored, "fcf_yield_score", idx)

    # Composite VM: growth-adjusted PE (60%) + FCF yield (40%)
    vm = pe_base * growth_adj * 0.6 + fcf_yield_s * 0.4
    result["alpha_vm"] = vm
    result["alpha_vm_pe_base"] = pe_base
    result["alpha_vm_growth_adj"] = growth_adj
    result["alpha_vm_fcf"] = fcf_yield_s

    # --- Factor 2: EV (Fundamental Support with Direction) ---
    quality = _safe_get(fund_scored, "quality_score", idx)
    growth = _safe_get(fund_scored, "growth_score", idx)
    visibility = ALPHA_MODEL_EV_QUALITY_WEIGHT * quality + ALPHA_MODEL_EV_GROWTH_WEIGHT * growth
    result["alpha_visibility"] = visibility

    # Direction multiplier: analyst revision + growth direction → [0.2, 1.5]
    # Analyst revision: use revision_momentum_score (0-100) → map to [-1, 1]
    revision_raw = _safe_get(analyst_scored, "revision_momentum_score", idx)
    analyst_revision = (revision_raw - 50) / 50  # [0, 100] → [-1, 1]

    # Growth direction: use growth_score as proxy → map to [-1, 1]
    # growth_score > 50 = positive growth, < 50 = negative
    growth_direction = (growth - 50) / 50  # [0, 100] → [-1, 1]

    multiplier = compute_direction_multiplier(analyst_revision, growth_direction)
    result["alpha_multiplier"] = multiplier

    ev = visibility * multiplier  # [0, 150]
    result["alpha_ev"] = ev

    # --- Factor 3: Timing (MA20/50 regime + Reversal) ---
    reversal = _safe_get(tech_scored, "reversal_score", idx)

    # MA20/50 directional signal ∈ (-1, +1):
    #   +1 = strong bullish (MA20 well above MA50 and rising)
    #    0 = neutral / crossover zone
    #   -1 = strong bearish (MA20 well below MA50 and falling)
    # Map to [0, 1] as a regime amplifier: bullish → boosts timing, bearish → suppresses it.
    # Reversal gate preserved: reversal=0 → timing=0 regardless of regime.
    ma_signal = _safe_get(tech_scored, "ma_trend_signal", idx)  # (-1, +1); 0.0 if missing
    ma_factor = (ma_signal + 1) / 2  # (0, 1); 0.5 = neutral crossover zone
    # timing = reversal * [α + (1-α) * ma_factor]
    # - α (timing_alpha): baseline reversal weight — timing is always at least α × reversal
    # - (1-α) × ma_factor: regime amplification on top (0 when bearish, 0.5 when neutral, 1 when bullish)
    timing = reversal * (timing_alpha + (1 - timing_alpha) * ma_factor)  # [0, 100]
    result["alpha_timing"] = timing
    result["alpha_ma_signal"] = ma_signal

    # --- Score: VM × EV × Timing / K ---
    raw_score = (vm * ev * timing) / ALPHA_MODEL_K
    result["alpha_score"] = raw_score.clip(0, 100)

    # --- Logging ---
    log.info(
        f"Alpha model: {len(result)} tickers, "
        f"score range=[{result['alpha_score'].min():.1f}, {result['alpha_score'].max():.1f}], "
        f"mean={result['alpha_score'].mean():.1f}, std={result['alpha_score'].std():.1f}"
    )
    log.info(
        f"  VM: [{vm.min():.1f}, {vm.max():.1f}] (pe_adj=[{(pe_base * growth_adj).min():.1f}, {(pe_base * growth_adj).max():.1f}], fcf=[{fcf_yield_s.min():.0f}, {fcf_yield_s.max():.0f}]), "
        f"EV: [{ev.min():.1f}, {ev.max():.1f}], "
        f"Timing: [{timing.min():.1f}, {timing.max():.1f}] (ma_signal=[{ma_signal.min():.2f}, {ma_signal.max():.2f}]), "
        f"multiplier: [{multiplier.min():.2f}, {multiplier.max():.2f}]"
    )

    n_above_50 = (result["alpha_score"] > 50).sum()
    n_below_20 = (result["alpha_score"] < 20).sum()
    log.info(f"  Distribution: {n_above_50} above 50, {n_below_20} below 20")

    return result
