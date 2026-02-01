"""Absolute metric scoring via piecewise linear interpolation.

Each raw metric is mapped to a 0-100 score using domain-specific breakpoints.
This replaces z-score normalization for rating computation.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


Breakpoints = List[Tuple[float, float]]


def metric_score(value: float | None, breakpoints: Breakpoints) -> float:
    """Map a raw metric value to 0-100 via piecewise linear interpolation.

    Args:
        value: Raw metric value.  None / NaN -> 50 (neutral).
        breakpoints: List of (raw_value, score) pairs sorted by raw_value.

    Returns:
        Score in [0, 100].
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 50.0

    if not breakpoints:
        return 50.0

    # Clamp below / above
    if value <= breakpoints[0][0]:
        return float(breakpoints[0][1])
    if value >= breakpoints[-1][0]:
        return float(breakpoints[-1][1])

    # Piecewise linear interpolation
    for i in range(len(breakpoints) - 1):
        x0, y0 = breakpoints[i]
        x1, y1 = breakpoints[i + 1]
        if x0 <= value <= x1:
            t = (value - x0) / (x1 - x0) if x1 != x0 else 0.0
            return float(y0 + t * (y1 - y0))

    return float(breakpoints[-1][1])


# ---------------------------------------------------------------------------
# Breakpoint tables for every scored metric
# ---------------------------------------------------------------------------

# -- Fundamental: Value --
PE_BREAKPOINTS: Breakpoints = [
    (0, 15), (8, 90), (15, 75), (22, 60), (30, 40), (50, 20), (100, 5),
]
PB_BREAKPOINTS: Breakpoints = [
    (0.3, 90), (1, 80), (2, 65), (3, 50), (5, 30), (10, 15),
]
PS_BREAKPOINTS: Breakpoints = [
    (0.5, 90), (1, 80), (3, 60), (6, 40), (12, 20),
]

# -- Fundamental: Quality --
ROE_BREAKPOINTS: Breakpoints = [
    (0, 20), (0.08, 45), (0.15, 65), (0.20, 78), (0.30, 90),
]
ROA_BREAKPOINTS: Breakpoints = [
    (0, 20), (0.03, 40), (0.07, 60), (0.12, 78), (0.18, 90),
]
PROFIT_MARGIN_BREAKPOINTS: Breakpoints = [
    (0, 20), (0.05, 40), (0.12, 60), (0.20, 78), (0.30, 90),
]

# -- Fundamental: Growth --
REVENUE_GROWTH_BREAKPOINTS: Breakpoints = [
    (-0.15, 10), (0, 40), (0.08, 60), (0.15, 75), (0.30, 90),
]
EARNINGS_GROWTH_BREAKPOINTS: Breakpoints = [
    (-0.20, 10), (0, 40), (0.10, 60), (0.20, 78), (0.40, 92),
]

# -- Fundamental: Safety --
DEBT_EQUITY_BREAKPOINTS: Breakpoints = [
    (0, 90), (40, 75), (80, 55), (130, 35), (250, 15),
]

# -- Technical: Momentum --
RSI_BREAKPOINTS: Breakpoints = [
    (15, 35), (30, 50), (45, 68), (55, 75), (65, 68), (75, 40), (85, 20),
]

# -- Technical: Volatility --
BB_POSITION_BREAKPOINTS: Breakpoints = [
    (0, 50), (0.2, 65), (0.5, 75), (0.7, 65), (0.9, 35), (1.0, 20),
]

# -- Technical: Volume --
VOLUME_RATIO_BREAKPOINTS: Breakpoints = [
    (0.3, 25), (0.7, 45), (1.0, 55), (1.5, 72), (2.5, 85),
]


def score_pe(value: float | None) -> float:
    """Score PE ratio (lower is better, negative PE -> 10)."""
    if value is not None and not (isinstance(value, float) and np.isnan(value)):
        if value < 0:
            return 10.0
    return metric_score(value, PE_BREAKPOINTS)


def score_pb(value: float | None) -> float:
    return metric_score(value, PB_BREAKPOINTS)


def score_ps(value: float | None) -> float:
    return metric_score(value, PS_BREAKPOINTS)


def score_roe(value: float | None) -> float:
    if value is not None and not (isinstance(value, float) and np.isnan(value)):
        if value < 0:
            return 10.0
    return metric_score(value, ROE_BREAKPOINTS)


def score_roa(value: float | None) -> float:
    if value is not None and not (isinstance(value, float) and np.isnan(value)):
        if value < 0:
            return 10.0
    return metric_score(value, ROA_BREAKPOINTS)


def score_profit_margin(value: float | None) -> float:
    if value is not None and not (isinstance(value, float) and np.isnan(value)):
        if value < 0:
            return 10.0
    return metric_score(value, PROFIT_MARGIN_BREAKPOINTS)


def score_revenue_growth(value: float | None) -> float:
    return metric_score(value, REVENUE_GROWTH_BREAKPOINTS)


def score_earnings_growth(value: float | None) -> float:
    return metric_score(value, EARNINGS_GROWTH_BREAKPOINTS)


def score_debt_equity(value: float | None) -> float:
    return metric_score(value, DEBT_EQUITY_BREAKPOINTS)


def score_rsi(value: float | None) -> float:
    return metric_score(value, RSI_BREAKPOINTS)


def score_bb_position(value: float | None) -> float:
    return metric_score(value, BB_POSITION_BREAKPOINTS)


def score_volume_ratio(value: float | None) -> float:
    return metric_score(value, VOLUME_RATIO_BREAKPOINTS)


def score_trend_alignment(value: float | None) -> float:
    """Trend alignment is already 0-1; map to 0-100."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 50.0
    return max(0.0, min(100.0, value * 100.0))


def score_macd_histogram(value: float | None) -> float:
    """MACD histogram: positive -> bullish (70), negative -> bearish (30), near zero -> neutral (50)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 50.0
    if value > 0.5:
        return 70.0
    if value < -0.5:
        return 30.0
    # Linear interpolation around zero
    return 50.0 + (value / 0.5) * 20.0


def score_sentiment(compound: float | None) -> float:
    """Sentiment compound (-1 to +1) -> 0-100."""
    if compound is None or (isinstance(compound, float) and np.isnan(compound)):
        return 50.0
    return max(0.0, min(100.0, (compound + 1.0) * 50.0))
