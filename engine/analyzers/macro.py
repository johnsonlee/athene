"""Market regime detection from macro indicators.

Classifies the market environment as risk_on, neutral, or risk_off
based on VIX, S&P 500 trend vs SMA200, and yield curve slope.

Regime affects composite scoring by adjusting dimension weights:
- risk_on:  More weight on Catalyst Timeline (+5%), less on Downside Control (-5%)
- risk_off: More weight on Downside Control (+5%), less on Catalyst Timeline (-5%)
- neutral:  Default weights (no adjustment)
"""

from __future__ import annotations

from typing import Any, Dict

from engine.config import (
    WEIGHT_EARNINGS_VISIBILITY,
    WEIGHT_VALUATION_MARGIN,
    WEIGHT_CATALYST_TIMELINE,
    WEIGHT_DOWNSIDE_CONTROL,
    REGIME_WEIGHT_SHIFT,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)


def _vix_signal(vix: float | None) -> float:
    """VIX level -> signal in [-1, +1].  Low VIX = risk-on."""
    if vix is None:
        return 0.0
    if vix < 15:
        return 1.0
    if vix < 20:
        return 0.5
    if vix < 25:
        return 0.0
    if vix < 30:
        return -0.5
    return -1.0


def _sp500_signal(sp500_vs_sma200_pct: float | None) -> float:
    """S&P 500 distance from SMA200 -> signal in [-1, +1]."""
    if sp500_vs_sma200_pct is None:
        return 0.0
    pct = sp500_vs_sma200_pct
    if pct > 0.05:
        return 1.0
    if pct > 0.0:
        return 0.5
    if pct > -0.05:
        return -0.5
    return -1.0


def _yield_curve_signal(spread: float | None) -> float:
    """Yield curve spread (10Y - 3M, in pp) -> signal in [-1, +1].

    Positive spread = normal curve = risk-on.
    Inverted curve = risk-off.
    """
    if spread is None:
        return 0.0
    if spread > 1.0:
        return 1.0
    if spread > 0.5:
        return 0.5
    if spread > 0.0:
        return 0.0
    if spread > -0.5:
        return -0.5
    return -1.0


def detect_regime(macro_data: Dict[str, Any]) -> Dict[str, Any]:
    """Determine market regime from macro indicators.

    Returns:
        dict with keys:
        - regime: 'risk_on', 'neutral', or 'risk_off'
        - regime_score: float in [-1, +1]
        - individual signal values
        - weights: regime-adjusted dimension weights
    """
    vix = macro_data.get("vix")
    sp500_pct = macro_data.get("sp500_vs_sma200_pct")
    spread = macro_data.get("yield_curve_spread")

    vix_sig = _vix_signal(vix)
    sp500_sig = _sp500_signal(sp500_pct)
    yc_sig = _yield_curve_signal(spread)

    # Average available signals (skip None indicators)
    signals = []
    if vix is not None:
        signals.append(vix_sig)
    if sp500_pct is not None:
        signals.append(sp500_sig)
    if spread is not None:
        signals.append(yc_sig)

    regime_score = sum(signals) / len(signals) if signals else 0.0

    # Classify regime
    if regime_score >= 0.5:
        regime = "risk_on"
    elif regime_score <= -0.5:
        regime = "risk_off"
    else:
        regime = "neutral"

    # Regime-adjusted dimension weights
    # risk_on:  CT +shift, DC -shift  (favor catalysts)
    # risk_off: CT -shift, DC +shift  (favor defense)
    # neutral:  no change
    shift = REGIME_WEIGHT_SHIFT
    if regime == "risk_on":
        adj_ct = WEIGHT_CATALYST_TIMELINE + shift
        adj_dc = WEIGHT_DOWNSIDE_CONTROL - shift
    elif regime == "risk_off":
        adj_ct = WEIGHT_CATALYST_TIMELINE - shift
        adj_dc = WEIGHT_DOWNSIDE_CONTROL + shift
    else:
        adj_ct = WEIGHT_CATALYST_TIMELINE
        adj_dc = WEIGHT_DOWNSIDE_CONTROL

    result = {
        "regime": regime,
        "regime_score": round(regime_score, 3),
        "vix_signal": vix_sig,
        "sp500_signal": sp500_sig,
        "yield_curve_signal": yc_sig,
        "vix": vix,
        "sp500_close": macro_data.get("sp500_close"),
        "sp500_sma200": macro_data.get("sp500_sma200"),
        "sp500_vs_sma200_pct": sp500_pct,
        "tnx_yield": macro_data.get("tnx_yield"),
        "irx_yield": macro_data.get("irx_yield"),
        "yield_curve_spread": spread,
        "weights": {
            "earnings_visibility": WEIGHT_EARNINGS_VISIBILITY,
            "valuation_margin": WEIGHT_VALUATION_MARGIN,
            "catalyst_timeline": adj_ct,
            "downside_control": adj_dc,
        },
    }

    sp_str = f"{sp500_pct:+.3f}" if sp500_pct is not None else "N/A"
    yc_str = f"{spread:+.2f}pp" if spread is not None else "N/A"
    log.info(f"Market regime: {regime} (score={regime_score:+.3f}, "
             f"VIX={vix}, SP500%SMA200={sp_str}, YC={yc_str})")

    return result
