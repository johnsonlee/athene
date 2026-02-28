"""Market timing integration — synthesize timing signals into stock scoring.

Combines 5 signals into a single market_timing_score (0-100) that influences
stock scoring via (a) dimension weight adjustment and (b) composite penalty
in unfavorable markets, modulated per-stock by defensive characteristics.

v19: Market Timing Integration

Signals:
    RFI level          (35%) — capital flow risk/safe balance
    Macro regime       (25%) — VIX + SPY/SMA200 + yield curve
    Credit spread vel. (20%) — LQD/TLT rate-of-change
    Breadth thrust     (15%) — sector trend flip rate
    VIX term structure  (5%) — VIX/VIX3M contango/backwardation

Timing zones:
    >= 62: favorable   — favor momentum (CT weight up)
    >= 45: neutral     — default weights
    >= 30: unfavorable — favor defense (DC weight up), mild penalty
    <  30: adverse     — strong defense, significant penalty
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.config import (
    TIMING_WEIGHT_RFI,
    TIMING_WEIGHT_MACRO,
    TIMING_WEIGHT_CREDIT,
    TIMING_WEIGHT_BREADTH,
    TIMING_WEIGHT_VIX_TS,
    TIMING_ZONE_FAVORABLE,
    TIMING_ZONE_NEUTRAL,
    TIMING_ZONE_UNFAVORABLE,
    TIMING_MAX_WEIGHT_SHIFT,
    TIMING_PENALTY_THRESHOLD,
    TIMING_MAX_PENALTY,
    TIMING_DC_MODULATION,
    WEIGHT_EARNINGS_VISIBILITY,
    WEIGHT_VALUATION_MARGIN,
    WEIGHT_CATALYST_TIMELINE,
    WEIGHT_DOWNSIDE_CONTROL,
)
from engine.scorer.absolute import metric_score
from engine.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Breakpoints for timing signal mapping (raw value -> 0-100 score)
# ---------------------------------------------------------------------------

# RFI level: tanh-normalized [-1, +1] -> 0-100
# panic (-0.8) is extreme fear -> low score (contrarian opportunity comes later)
# risk_on (+0.3) is bullish flow -> higher score
RFI_BREAKPOINTS = [
    (-1.0, 8),
    (-0.8, 15),
    (-0.6, 25),
    (-0.3, 38),
    (0.0, 50),
    (0.3, 68),
    (0.6, 80),
    (1.0, 90),
]

# Macro regime score: [-1, +1] -> 0-100
MACRO_REGIME_BREAKPOINTS = [
    (-1.0, 15),
    (-0.5, 30),
    (0.0, 50),
    (0.5, 70),
    (1.0, 85),
]

# Credit spread velocity (LQD/TLT 5d ROC): tightening (positive) is bearish
# Negative velocity = credit easing = bullish
CREDIT_VELOCITY_BREAKPOINTS = [
    (-0.03, 85),
    (-0.015, 78),
    (-0.005, 60),
    (0.0, 50),
    (0.005, 40),
    (0.015, 22),
    (0.03, 10),
]

# Breadth thrust: fraction of sectors flipping to uptrend over 22 days
# Positive thrust = broad-based recovery
BREADTH_THRUST_BREAKPOINTS = [
    (-0.36, 10),
    (-0.18, 15),
    (-0.05, 40),
    (0.0, 50),
    (0.05, 60),
    (0.18, 85),
    (0.36, 95),
]

# VIX term structure ratio (VIX/VIX3M):
# > 1.05 = backwardation (peak fear, often contrarian buy)
# < 0.85 = deep contango (complacency, risk of correction)
VIX_TERM_STRUCTURE_BREAKPOINTS = [
    (0.80, 65),
    (0.85, 60),
    (0.95, 50),
    (1.00, 45),
    (1.05, 20),
    (1.15, 10),
]


@dataclass
class TimingResult:
    """Result of market timing computation."""
    market_timing_score: float
    timing_zone: str
    weight_adjustments: dict[str, float]
    composite_penalty: float  # base penalty (before per-stock DC modulation)
    signal_contributions: dict[str, float]
    raw_signals: dict[str, Any]


def _extract_rfi(cf_window_results: dict[str, list] | None) -> float | None:
    """Extract latest RFI value from 1W capital flow window results."""
    if not cf_window_results:
        return None
    phases_1w = cf_window_results.get("1W", [])
    if not phases_1w:
        return None
    latest = phases_1w[-1] if isinstance(phases_1w, list) else None
    if latest is None:
        return None
    rfi = latest.get("rfi")
    if rfi is not None:
        return float(rfi)
    # Fallback: compute from risk_net / safe_net
    risk_net = latest.get("risk_net", 0)
    safe_net = latest.get("safe_net", 0)
    total = abs(risk_net) + abs(safe_net)
    if total > 0.5:
        return (risk_net - safe_net) / total
    return 0.0


def _extract_credit_velocity(leading_indicators: dict | None) -> float | None:
    """Extract latest credit spread 5d velocity from leading indicators."""
    if not leading_indicators:
        return None
    cs = leading_indicators.get("credit_spread", {})
    data = cs.get("data", [])
    if not data:
        return None
    latest = data[-1]
    return latest.get("velocity_5d")


def _extract_breadth_thrust(leading_indicators: dict | None) -> float | None:
    """Extract latest breadth thrust value from leading indicators."""
    if not leading_indicators:
        return None
    bt = leading_indicators.get("breadth_thrust", {})
    data = bt.get("data", [])
    if not data:
        return None
    latest = data[-1]
    return latest.get("thrust")


def _extract_vix_ts_ratio(leading_indicators: dict | None) -> float | None:
    """Extract latest VIX term structure ratio from leading indicators."""
    if not leading_indicators:
        return None
    vts = leading_indicators.get("vix_term_structure", {})
    data = vts.get("data", [])
    if not data:
        return None
    latest = data[-1]
    return latest.get("ratio")


def _extract_rfi_acceleration_signal(leading_indicators: dict | None) -> str | None:
    """Extract latest RFI acceleration signal for trap detection."""
    if not leading_indicators:
        return None
    rfi_acc = leading_indicators.get("rfi_acceleration", {})
    data = rfi_acc.get("data", [])
    if not data:
        return None
    return data[-1].get("signal")


def _classify_zone(score: float) -> str:
    """Classify timing score into a zone."""
    if score >= TIMING_ZONE_FAVORABLE:
        return "favorable"
    if score >= TIMING_ZONE_NEUTRAL:
        return "neutral"
    if score >= TIMING_ZONE_UNFAVORABLE:
        return "unfavorable"
    return "adverse"


def compute_market_timing(
    regime_info: dict[str, Any],
    cf_window_results: dict[str, list] | None = None,
    leading_indicators: dict | None = None,
) -> TimingResult:
    """Compute market timing score from multiple signals.

    Args:
        regime_info: Output from detect_regime() — contains regime_score.
        cf_window_results: Capital flow analysis results per window label.
        leading_indicators: Output from compute_leading_indicators().

    Returns:
        TimingResult with timing score, zone, weight adjustments, and penalty.
    """
    NEUTRAL = 50.0

    # --- Extract raw signal values ---
    rfi = _extract_rfi(cf_window_results)
    macro_score = regime_info.get("regime_score")  # [-1, +1]
    credit_vel = _extract_credit_velocity(leading_indicators)
    breadth = _extract_breadth_thrust(leading_indicators)
    vix_ratio = _extract_vix_ts_ratio(leading_indicators)

    raw_signals = {
        "rfi": rfi,
        "macro_regime_score": macro_score,
        "credit_velocity_5d": credit_vel,
        "breadth_thrust": breadth,
        "vix_ts_ratio": vix_ratio,
    }

    # --- Map each signal to 0-100 via breakpoints ---
    rfi_score = metric_score(rfi, RFI_BREAKPOINTS, NEUTRAL)
    macro_mapped = metric_score(macro_score, MACRO_REGIME_BREAKPOINTS, NEUTRAL)
    credit_mapped = metric_score(credit_vel, CREDIT_VELOCITY_BREAKPOINTS, NEUTRAL)
    breadth_mapped = metric_score(breadth, BREADTH_THRUST_BREAKPOINTS, NEUTRAL)
    vix_ts_mapped = metric_score(vix_ratio, VIX_TERM_STRUCTURE_BREAKPOINTS, NEUTRAL)

    # --- Trap signal avoidance (v13 backtest finding) ---
    # mild_risk_off -> risk_on has 50% hit rate and -3.42% avg return.
    # When RFI is in mild_risk_off zone AND rfi_acceleration shows "improving",
    # cap RFI contribution at 45 to prevent false optimism.
    rfi_acc_signal = _extract_rfi_acceleration_signal(leading_indicators)
    if rfi is not None and -0.3 < rfi < 0 and rfi_acc_signal == "improving":
        rfi_score = min(rfi_score, 45.0)
        log.info(f"Trap avoidance: RFI in mild_risk_off ({rfi:.3f}) with improving "
                 f"acceleration — capping RFI contribution at 45")

    signal_contributions = {
        "rfi": round(rfi_score, 2),
        "macro": round(macro_mapped, 2),
        "credit": round(credit_mapped, 2),
        "breadth": round(breadth_mapped, 2),
        "vix_ts": round(vix_ts_mapped, 2),
    }

    # --- Weighted composite ---
    market_timing_score = (
        TIMING_WEIGHT_RFI * rfi_score
        + TIMING_WEIGHT_MACRO * macro_mapped
        + TIMING_WEIGHT_CREDIT * credit_mapped
        + TIMING_WEIGHT_BREADTH * breadth_mapped
        + TIMING_WEIGHT_VIX_TS * vix_ts_mapped
    )

    timing_zone = _classify_zone(market_timing_score)

    # --- Weight adjustments (replaces old ±5% regime shift) ---
    timing_delta = (market_timing_score - 50.0) / 50.0  # [-1, +1]
    ct_shift = timing_delta * TIMING_MAX_WEIGHT_SHIFT
    dc_shift = -ct_shift

    weight_adjustments = {
        "earnings_visibility": WEIGHT_EARNINGS_VISIBILITY,
        "valuation_margin": WEIGHT_VALUATION_MARGIN,
        "catalyst_timeline": WEIGHT_CATALYST_TIMELINE + ct_shift,
        "downside_control": WEIGHT_DOWNSIDE_CONTROL + dc_shift,
    }

    # --- Base composite penalty (applied per-stock with DC modulation) ---
    if market_timing_score >= TIMING_PENALTY_THRESHOLD:
        base_penalty = 0.0
    else:
        base_penalty = (
            (TIMING_PENALTY_THRESHOLD - market_timing_score)
            / TIMING_PENALTY_THRESHOLD
        ) * TIMING_MAX_PENALTY

    log.info(f"Market timing: score={market_timing_score:.1f}, zone={timing_zone}, "
             f"base_penalty={base_penalty:.1f}")
    log.info(f"  Signals: RFI={rfi_score:.0f} Macro={macro_mapped:.0f} "
             f"Credit={credit_mapped:.0f} Breadth={breadth_mapped:.0f} "
             f"VIX_TS={vix_ts_mapped:.0f}")
    log.info(f"  Weights: CT={weight_adjustments['catalyst_timeline']:.0%} "
             f"DC={weight_adjustments['downside_control']:.0%}")

    return TimingResult(
        market_timing_score=round(market_timing_score, 2),
        timing_zone=timing_zone,
        weight_adjustments=weight_adjustments,
        composite_penalty=round(base_penalty, 2),
        signal_contributions=signal_contributions,
        raw_signals=raw_signals,
    )


def modulate_penalty(base_penalty: float, dc_score: float) -> float:
    """Modulate timing penalty per-stock based on downside control score.

    Defensive stocks (DC > 50) get up to TIMING_DC_MODULATION (40%) reduction.
    """
    if base_penalty <= 0:
        return 0.0
    reduction = max(0.0, (dc_score - 50.0) / 50.0) * TIMING_DC_MODULATION
    return base_penalty * (1.0 - reduction)
