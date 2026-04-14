"""Three-factor multiplicative alpha scoring model.

Score = (VM% × EV% × Timing% / ALPHA_SCORE_NORM) × 100

Each factor is normalized to [0, 100] by dividing by its theoretical max:
  VM_raw     ∈ [0, 130] → VM     = VM_raw     / 130 × 100
  EV_raw     ∈ [0, 150] → EV     = EV_raw     / 150 × 100
  Timing_raw ∈ [0, 100] → Timing = Timing_raw (already in [0, 100])

The raw multiplicative product is then rescaled by ALPHA_SCORE_NORM so that top
stocks reach ~90+. Without this rescaling, no stock ever reaches 100 because the
theoretical joint max (VM=100% AND EV=100% AND Timing=100%) is effectively
unreachable — historically the best products are ~29 on the 0-100 product scale.

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
    ALPHA_MODEL_TIMING_ALPHA,
    ALPHA_MODEL_DIRECTION_CENTER,
    ALPHA_MODEL_DIRECTION_RANGE,
    ALPHA_MODEL_EV_QUALITY_WEIGHT,
    ALPHA_MODEL_EV_GROWTH_WEIGHT,
    ALPHA_SCORE_NORM,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)

NEUTRAL = 50.0

# Theoretical maximums for normalization.
# VM_raw = pe_base × growth_adj × 0.6 + fcf × 0.4; max at pe=100, growth_adj=1.5, fcf=100
GROWTH_ADJ_MAX = 1.5
VM_MAX = 100.0 * GROWTH_ADJ_MAX * 0.6 + 100.0 * 0.4  # = 130.0
# EV_raw = visibility × direction_multiplier; max at visibility=100, multiplier=CENTER+RANGE
EV_MAX = 100.0 * (ALPHA_MODEL_DIRECTION_CENTER + ALPHA_MODEL_DIRECTION_RANGE)  # = 150.0
# Timing_raw = reversal × (α + (1-α) × cycle_upside/100); max at reversal=100, cycle_upside=100
TIMING_MAX = 100.0


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

    # Composite VM: growth-adjusted PE (60%) + FCF yield (40%), raw ∈ [0, 130]
    # Normalize by VM_MAX (130) to get percentage in [0, 100].
    vm_raw = pe_base * growth_adj * 0.6 + fcf_yield_s * 0.4
    vm = (vm_raw / VM_MAX * 100).clip(0, 100)
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

    # EV_raw ∈ [0, 150], normalize by EV_MAX (150) to percentage in [0, 100].
    ev_raw = visibility * multiplier
    ev = (ev_raw / EV_MAX * 100).clip(0, 100)
    result["alpha_ev"] = ev

    # --- Factor 3: Timing (Cycle Position + Reversal) ---
    trend = _safe_get(tech_scored, "trend_score", idx)
    reversal = _safe_get(tech_scored, "reversal_score", idx)

    cycle_upside = 100 - trend  # high trend → low upside remaining
    # Reversal-gated timing: reversal activates cycle_upside, not additive blend.
    # timing = reversal * [α + (1-α) * cycle_upside / 100]
    # - reversal=0 → timing=0 (no reversal signal = don't buy, regardless of upside)
    # - cycle_upside amplifies reversal, not replaces it
    # - α = baseline reversal contribution; (1-α) = how much cycle_upside can amplify
    # Timing is already in [0, 100] (TIMING_MAX = 100), no normalization needed.
    timing = reversal * (timing_alpha + (1 - timing_alpha) * cycle_upside / 100)
    result["alpha_timing"] = timing

    # --- Score: (VM% × EV% × Timing% / ALPHA_SCORE_NORM) × 100 ---
    # Raw product is in [0, 100] theoretically but historically peaks around 29
    # because a stock can rarely be simultaneously top on all three factors.
    # Rescale by ALPHA_SCORE_NORM (≈ historical max) so top stocks reach ~90+.
    raw_product = (vm / 100) * (ev / 100) * (timing / 100) * 100
    result["alpha_score"] = (raw_product / ALPHA_SCORE_NORM * 100).clip(0, 100)

    # --- Logging ---
    log.info(
        f"Alpha model: {len(result)} tickers, "
        f"score range=[{result['alpha_score'].min():.1f}, {result['alpha_score'].max():.1f}], "
        f"mean={result['alpha_score'].mean():.1f}, std={result['alpha_score'].std():.1f}"
    )
    log.info(
        f"  VM: [{vm.min():.1f}, {vm.max():.1f}] (pe_adj=[{(pe_base * growth_adj).min():.1f}, {(pe_base * growth_adj).max():.1f}], fcf=[{fcf_yield_s.min():.0f}, {fcf_yield_s.max():.0f}]), "
        f"EV: [{ev.min():.1f}, {ev.max():.1f}], "
        f"Timing: [{timing.min():.1f}, {timing.max():.1f}], "
        f"multiplier: [{multiplier.min():.2f}, {multiplier.max():.2f}]"
    )

    n_above_50 = (result["alpha_score"] > 50).sum()
    n_below_20 = (result["alpha_score"] < 20).sum()
    log.info(f"  Distribution: {n_above_50} above 50, {n_below_20} below 20")

    return result
