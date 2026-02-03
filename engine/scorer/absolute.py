"""Absolute metric scoring via piecewise linear interpolation.

Each raw metric is mapped to a 0-100 score using domain-specific breakpoints.
This replaces z-score normalization for rating computation.

v5: Generalized sector-aware breakpoints for Technology, Healthcare, Utilities,
    Real Estate, Energy (beyond the v4 Financial-only adjustment).
    Added forward PE, FCF yield, and current ratio scoring.

v6: Technical scoring overhaul — MACD normalized by price, volume scored with
    directional context, BB width + historical vol for true volatility, trend
    alignment weighted by margin distance.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

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
# Default breakpoint tables (used when no sector override exists)
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
FORWARD_PE_BREAKPOINTS: Breakpoints = [
    (0, 15), (8, 88), (13, 75), (20, 60), (28, 42), (45, 20), (80, 5),
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
FCF_YIELD_BREAKPOINTS: Breakpoints = [
    (-0.05, 10), (0, 30), (0.03, 55), (0.06, 72), (0.10, 88),
]
CURRENT_RATIO_BREAKPOINTS: Breakpoints = [
    (0.5, 15), (1.0, 45), (1.5, 68), (2.0, 80), (3.0, 85),
]

# -- Technical: Momentum --
RSI_BREAKPOINTS: Breakpoints = [
    (15, 35), (30, 50), (45, 68), (55, 75), (65, 68), (75, 40), (85, 20),
]
MACD_HISTOGRAM_PCT_BREAKPOINTS: Breakpoints = [
    (-1.5, 20), (-0.5, 35), (-0.1, 45), (0.0, 50), (0.1, 55), (0.5, 65), (1.5, 80),
]

# -- Technical: Volatility (v6: true volatility measures) --
BB_WIDTH_BREAKPOINTS: Breakpoints = [
    (0.02, 88), (0.05, 72), (0.10, 55), (0.15, 38), (0.25, 20),
]
HIST_VOLATILITY_BREAKPOINTS: Breakpoints = [
    (0.10, 88), (0.20, 72), (0.30, 52), (0.45, 35), (0.70, 18),
]

# -- Technical: Volume (v6: direction-aware) --
DIRECTIONAL_VOLUME_BREAKPOINTS: Breakpoints = [
    (-2.5, 15), (-1.5, 28), (-1.0, 40), (0, 50), (1.0, 60), (1.5, 72), (2.5, 85),
]


# ---------------------------------------------------------------------------
# Sector-specific breakpoint overrides
# ---------------------------------------------------------------------------
# Each sector maps metric names to alternative breakpoint tables.
# If a metric is not in the override, the default breakpoints are used.

_SECTOR_OVERRIDES: Dict[str, Dict[str, Breakpoints]] = {
    # -- Financial: leverage is structural, low PE/PB is normal --
    "Financial": {
        "pe": [(0, 15), (5, 70), (8, 60), (12, 52), (18, 42), (25, 30), (50, 15)],
        "forward_pe": [(0, 15), (5, 68), (8, 58), (12, 50), (18, 40), (25, 28), (50, 12)],
        "pb": [(0.3, 75), (0.8, 62), (1.5, 52), (2.5, 40), (4, 25), (8, 15)],
        "debt_equity": [(0, 60), (50, 55), (100, 50), (200, 47), (400, 42)],
    },
    # -- Technology: higher valuation multiples are structural (asset-light, high-growth) --
    "Technology": {
        "pe": [(0, 15), (12, 85), (20, 70), (30, 55), (45, 35), (70, 15), (100, 5)],
        "forward_pe": [(0, 15), (10, 82), (18, 68), (28, 50), (40, 30), (65, 12)],
        "pb": [(0.5, 85), (2, 72), (5, 55), (10, 38), (20, 20), (40, 10)],
        "ps": [(1, 85), (3, 72), (8, 55), (15, 38), (25, 20), (40, 10)],
    },
    # -- Healthcare: biotech negative PE is normal (R&D phase); pharma has moderate multiples --
    "Healthcare": {
        "pe": [(0, 20), (10, 82), (18, 68), (28, 50), (45, 28), (80, 10)],
        "forward_pe": [(0, 20), (8, 80), (15, 68), (25, 48), (40, 25), (70, 8)],
    },
    # -- Utilities: low PE, low growth, higher D/E are all structural --
    "Utilities": {
        "pe": [(0, 15), (10, 82), (15, 68), (20, 52), (28, 35), (40, 18)],
        "forward_pe": [(0, 15), (8, 80), (13, 66), (18, 50), (25, 32), (38, 15)],
        "revenue_growth": [(-0.05, 15), (0, 50), (0.03, 65), (0.06, 78), (0.10, 88)],
        "earnings_growth": [(-0.10, 15), (0, 50), (0.05, 65), (0.10, 80), (0.20, 90)],
        "debt_equity": [(0, 85), (60, 72), (120, 55), (200, 40), (350, 20)],
    },
    # -- Real Estate: high leverage is structural (similar to financials) --
    "Real Estate": {
        "pe": [(0, 15), (10, 78), (20, 62), (35, 42), (55, 22), (80, 10)],
        "forward_pe": [(0, 15), (8, 75), (18, 60), (30, 40), (50, 20), (75, 8)],
        "debt_equity": [(0, 70), (50, 62), (100, 52), (200, 42), (400, 30)],
    },
    # -- Energy: cyclical earnings make trailing PE unreliable at cycle extremes --
    "Energy": {
        "pe": [(0, 15), (5, 72), (10, 62), (18, 50), (30, 35), (50, 18)],
        "forward_pe": [(0, 15), (5, 70), (10, 60), (16, 48), (28, 32), (45, 15)],
    },
}

# Mapping from various sector name variants to canonical override keys.
_SECTOR_ALIASES: Dict[str, str] = {
    "Financials": "Financial",
    "Financial Services": "Financial",
    "Information Technology": "Technology",
    "Technology": "Technology",
    "Health Care": "Healthcare",
    "Healthcare": "Healthcare",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
    "Energy": "Energy",
}


def _resolve_sector(sector: str | None) -> str | None:
    """Resolve a raw sector name to its canonical override key (or None)."""
    if sector is None:
        return None
    return _SECTOR_ALIASES.get(sector)


def _get_breakpoints(metric: str, sector: str | None, default: Breakpoints) -> Breakpoints:
    """Look up sector-specific breakpoints, falling back to *default*."""
    canonical = _resolve_sector(sector)
    if canonical and canonical in _SECTOR_OVERRIDES:
        overrides = _SECTOR_OVERRIDES[canonical]
        if metric in overrides:
            return overrides[metric]
    return default


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_pe(value: float | None, sector: str | None = None) -> float:
    """Score PE ratio (lower is better, negative PE -> 10)."""
    if value is not None and not (isinstance(value, float) and np.isnan(value)):
        if value < 0:
            # Negative PE is less penalized for Healthcare (biotech R&D phase)
            if _resolve_sector(sector) == "Healthcare":
                return 20.0
            return 10.0
    bp = _get_breakpoints("pe", sector, PE_BREAKPOINTS)
    return metric_score(value, bp)


def score_forward_pe(value: float | None, sector: str | None = None) -> float:
    """Score forward PE (lower is better, negative -> 10)."""
    if value is not None and not (isinstance(value, float) and np.isnan(value)):
        if value < 0:
            if _resolve_sector(sector) == "Healthcare":
                return 20.0
            return 10.0
    bp = _get_breakpoints("forward_pe", sector, FORWARD_PE_BREAKPOINTS)
    return metric_score(value, bp)


def score_pb(value: float | None, sector: str | None = None) -> float:
    bp = _get_breakpoints("pb", sector, PB_BREAKPOINTS)
    return metric_score(value, bp)


def score_ps(value: float | None, sector: str | None = None) -> float:
    bp = _get_breakpoints("ps", sector, PS_BREAKPOINTS)
    return metric_score(value, bp)


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


def score_revenue_growth(value: float | None, sector: str | None = None) -> float:
    bp = _get_breakpoints("revenue_growth", sector, REVENUE_GROWTH_BREAKPOINTS)
    return metric_score(value, bp)


def score_earnings_growth(value: float | None, sector: str | None = None) -> float:
    bp = _get_breakpoints("earnings_growth", sector, EARNINGS_GROWTH_BREAKPOINTS)
    return metric_score(value, bp)


def score_debt_equity(value: float | None, sector: str | None = None) -> float:
    bp = _get_breakpoints("debt_equity", sector, DEBT_EQUITY_BREAKPOINTS)
    return metric_score(value, bp)


def score_fcf_yield(value: float | None) -> float:
    """Score FCF yield (FCF / market cap). Higher is better."""
    return metric_score(value, FCF_YIELD_BREAKPOINTS)


def score_current_ratio(value: float | None) -> float:
    """Score current ratio. Values around 1.5-2.0 are healthy."""
    return metric_score(value, CURRENT_RATIO_BREAKPOINTS)


# -- Technical scoring (v6: normalized & direction-aware) --

def score_rsi(value: float | None) -> float:
    return metric_score(value, RSI_BREAKPOINTS)


def score_bb_width(value: float | None) -> float:
    """BB bandwidth (upper-lower)/mid — true volatility. Lower = calmer = higher score."""
    return metric_score(value, BB_WIDTH_BREAKPOINTS)


def score_hist_volatility(value: float | None) -> float:
    """Annualized historical volatility. Lower = calmer = higher score."""
    return metric_score(value, HIST_VOLATILITY_BREAKPOINTS)


def score_directional_volume(value: float | None) -> float:
    """Signed volume ratio (volume_ratio * sign(return)). Positive = bullish confirmation."""
    return metric_score(value, DIRECTIONAL_VOLUME_BREAKPOINTS)


def score_trend_alignment(value: float | None) -> float:
    """Trend alignment is already 0-1; map to 0-100."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 50.0
    return max(0.0, min(100.0, value * 100.0))


def score_macd_histogram(value: float | None) -> float:
    """MACD histogram normalized by price (% of close). Uses piecewise breakpoints."""
    return metric_score(value, MACD_HISTOGRAM_PCT_BREAKPOINTS)


def score_sentiment(compound: float | None) -> float:
    """Sentiment compound (-1 to +1) -> 0-100."""
    if compound is None or (isinstance(compound, float) and np.isnan(compound)):
        return 50.0
    return max(0.0, min(100.0, (compound + 1.0) * 50.0))
