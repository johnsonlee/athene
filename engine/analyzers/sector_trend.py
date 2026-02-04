"""Sector-level trend signal analysis.

Computes 5 trend signals per sector from ETF prices, stock breadth,
and analyst revision data:

    Relative Strength (35%) — sector ETF return vs SPY
    Breadth            (25%) — % of sector stocks above SMA50/SMA200
    Analyst Revisions  (15%) — aggregate upgrade/downgrade ratio
    Momentum           (15%) — ETF RSI + SMA alignment
    Volume             (10%) — directional ETF volume ratio
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from engine.config import SECTOR_ETFS, SPY_TICKER, TREND_HISTORY_SAMPLE_INTERVAL
from engine.scorer.absolute import metric_score
from engine.utils.logger import get_logger

log = get_logger(__name__)

# --- Relative strength breakpoints (excess return -> 0-100) ---
# Positive excess return = sector outperforming SPY
_RS_BREAKPOINTS = [
    (-0.20, 5),
    (-0.10, 20),
    (-0.05, 35),
    (0.00, 50),
    (0.05, 65),
    (0.10, 80),
    (0.20, 95),
]

# --- Analyst net revision ratio breakpoints ---
_ANALYST_NET_BREAKPOINTS = [
    (-1.0, 10),
    (-0.5, 25),
    (0.0, 50),
    (0.5, 75),
    (1.0, 90),
]

# --- RSI breakpoints (moderate is best for trend health) ---
_RSI_TREND_BREAKPOINTS = [
    (20, 15),
    (30, 35),
    (40, 55),
    (50, 70),
    (60, 75),
    (70, 65),
    (80, 40),
    (90, 15),
]

# --- Volume ratio breakpoints (directional) ---
_VOLUME_BREAKPOINTS = [
    (-2.5, 15),
    (-1.5, 30),
    (0.0, 50),
    (1.0, 65),
    (1.5, 72),
    (2.5, 85),
]


def _compute_return(prices: pd.DataFrame, trading_days: int) -> float | None:
    """Compute return over the last N trading days."""
    if prices is None or len(prices) < trading_days + 1:
        return None
    close = prices["Close"]
    current = float(close.iloc[-1])
    past = float(close.iloc[-min(trading_days, len(close))])
    if past == 0:
        return None
    return (current - past) / past


def _compute_sma(prices: pd.DataFrame, period: int) -> float | None:
    """Compute SMA of close prices."""
    if prices is None or len(prices) < period:
        return None
    return float(prices["Close"].tail(period).mean())


def _compute_rsi(prices: pd.DataFrame, period: int = 14) -> float | None:
    """Compute RSI from close prices."""
    if prices is None or len(prices) < period + 1:
        return None
    close = prices["Close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100 - (100 / (1 + rs)))


def _margin_score(val: float, ref: float) -> float:
    """Score how far val is above ref as 0-1 value (same as technical.py)."""
    if ref == 0:
        return 0.5
    pct = (val - ref) / abs(ref)
    clamped = max(-0.20, min(0.20, pct))
    return (clamped + 0.20) / 0.40


def _compute_relative_strength(
    etf_prices: pd.DataFrame, spy_prices: pd.DataFrame
) -> Dict[str, Any]:
    """Compute relative strength scores across 1M/3M/6M horizons."""
    result: Dict[str, Any] = {}

    horizons = [
        ("1m", 21, 0.50),
        ("3m", 63, 0.30),
        ("6m", 126, 0.20),
    ]

    scores = []
    for label, days, weight in horizons:
        etf_ret = _compute_return(etf_prices, days)
        spy_ret = _compute_return(spy_prices, days)
        if etf_ret is not None and spy_ret is not None:
            excess = etf_ret - spy_ret
            result[f"rs_{label}"] = round(excess, 4)
            score = metric_score(excess, _RS_BREAKPOINTS)
            scores.append((score, weight))
        else:
            result[f"rs_{label}"] = None

    if scores:
        total_weight = sum(w for _, w in scores)
        result["relative_strength_score"] = round(
            sum(s * w for s, w in scores) / total_weight, 1
        )
    else:
        result["relative_strength_score"] = 50.0

    return result


def _compute_breadth(
    sector_name: str,
    stock_prices: Dict[str, pd.DataFrame],
    universe: pd.DataFrame,
) -> Dict[str, Any]:
    """Compute breadth (% of stocks above SMA50/SMA200) for a sector."""
    result: Dict[str, Any] = {}

    # Get tickers in this sector
    sector_tickers = universe.loc[universe["sector"] == sector_name, "ticker"].tolist()
    if not sector_tickers:
        result["breadth_sma50"] = None
        result["breadth_sma200"] = None
        result["breadth_score"] = 50.0
        result["stock_count"] = 0
        return result

    above_sma50 = 0
    above_sma200 = 0
    counted_50 = 0
    counted_200 = 0

    for ticker in sector_tickers:
        prices = stock_prices.get(ticker)
        if prices is None or prices.empty:
            continue
        close = float(prices["Close"].iloc[-1])

        sma50 = _compute_sma(prices, 50)
        if sma50 is not None:
            counted_50 += 1
            if close > sma50:
                above_sma50 += 1

        sma200 = _compute_sma(prices, 200)
        if sma200 is not None:
            counted_200 += 1
            if close > sma200:
                above_sma200 += 1

    pct_50 = above_sma50 / counted_50 if counted_50 > 0 else 0.5
    pct_200 = above_sma200 / counted_200 if counted_200 > 0 else 0.5

    result["breadth_sma50"] = round(pct_50, 3)
    result["breadth_sma200"] = round(pct_200, 3)
    # Score: 0-100, weighted average of both breadth measures
    result["breadth_score"] = round(0.5 * pct_50 * 100 + 0.5 * pct_200 * 100, 1)
    result["stock_count"] = len(sector_tickers)

    return result


def _compute_analyst_revisions(
    sector_name: str,
    analyst_data: Dict[str, Any],
    universe: pd.DataFrame,
) -> Dict[str, Any]:
    """Aggregate analyst upgrades/downgrades across sector stocks."""
    from engine.collectors.analyst import _classify_revision

    result: Dict[str, Any] = {}

    sector_tickers = universe.loc[universe["sector"] == sector_name, "ticker"].tolist()

    upgrades = 0
    downgrades = 0

    for ticker in sector_tickers:
        data = analyst_data.get(ticker)
        if data is None:
            continue
        for rev in data.get("revisions", []):
            classification = _classify_revision(
                rev.get("action", ""),
                rev.get("from_grade", ""),
                rev.get("to_grade", ""),
            )
            if classification == "upgrade":
                upgrades += 1
            elif classification == "downgrade":
                downgrades += 1

    total = upgrades + downgrades
    if total > 0:
        net_ratio = (upgrades - downgrades) / total
    else:
        net_ratio = 0.0

    result["analyst_upgrades"] = upgrades
    result["analyst_downgrades"] = downgrades
    result["analyst_net"] = round(net_ratio, 3)
    result["analyst_revision_score"] = round(
        metric_score(net_ratio, _ANALYST_NET_BREAKPOINTS), 1
    )

    return result


def _compute_momentum(etf_prices: pd.DataFrame) -> Dict[str, Any]:
    """Compute ETF momentum: RSI + SMA alignment."""
    result: Dict[str, Any] = {}

    rsi = _compute_rsi(etf_prices)
    result["etf_rsi"] = round(rsi, 1) if rsi is not None else None

    # RSI score
    rsi_score = metric_score(rsi, _RSI_TREND_BREAKPOINTS) if rsi is not None else 50.0

    # SMA alignment score (close vs SMA50, close vs SMA200, SMA50 vs SMA200)
    close = float(etf_prices["Close"].iloc[-1])
    sma50 = _compute_sma(etf_prices, 50)
    sma200 = _compute_sma(etf_prices, 200)

    alignment_scores = []
    if sma50 is not None:
        alignment_scores.append(_margin_score(close, sma50))
    if sma200 is not None:
        alignment_scores.append(_margin_score(close, sma200))
    if sma50 is not None and sma200 is not None:
        alignment_scores.append(_margin_score(sma50, sma200))

    alignment = (sum(alignment_scores) / len(alignment_scores) * 100) if alignment_scores else 50.0

    # Momentum = 50% RSI + 50% alignment
    result["momentum_score"] = round(0.5 * rsi_score + 0.5 * alignment, 1)

    return result


def _compute_volume(etf_prices: pd.DataFrame) -> Dict[str, Any]:
    """Compute directional volume ratio for ETF."""
    result: Dict[str, Any] = {}

    if len(etf_prices) < 21:
        result["volume_ratio"] = None
        result["volume_score"] = 50.0
        return result

    volume = etf_prices["Volume"]
    close = etf_prices["Close"]
    avg_vol = float(volume.tail(20).mean())
    latest_vol = float(volume.iloc[-1])

    if avg_vol > 0:
        vol_ratio = latest_vol / avg_vol
    else:
        vol_ratio = 1.0

    # Directional: positive on up-day, negative on down-day
    if len(close) >= 2:
        daily_ret = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2])
        if abs(daily_ret) > 1e-4:
            signed_ratio = vol_ratio * (1 if daily_ret > 0 else -1)
        else:
            signed_ratio = 0.0
    else:
        signed_ratio = 0.0

    result["volume_ratio"] = round(vol_ratio, 2)
    result["volume_score"] = round(
        metric_score(signed_ratio, _VOLUME_BREAKPOINTS), 1
    )

    return result


def analyze_sector_trends(
    etf_prices: Dict[str, pd.DataFrame],
    stock_prices: Dict[str, pd.DataFrame],
    universe: pd.DataFrame,
    analyst_data: Dict[str, Any],
) -> pd.DataFrame:
    """Compute per-sector trend signals.

    Returns:
        DataFrame indexed by sector name with signal columns.
    """
    spy_prices = etf_prices.get(SPY_TICKER)
    if spy_prices is None or spy_prices.empty:
        log.warning("No SPY data available, relative strength will be neutral")

    records = []

    for etf_ticker, sector_name in SECTOR_ETFS.items():
        etf_df = etf_prices.get(etf_ticker)
        if etf_df is None or etf_df.empty:
            log.warning(f"No ETF data for {etf_ticker} ({sector_name}), skipping")
            continue

        record: Dict[str, Any] = {
            "sector": sector_name,
            "etf_ticker": etf_ticker,
            "etf_close": round(float(etf_df["Close"].iloc[-1]), 2),
        }

        # SMA values for display
        sma50 = _compute_sma(etf_df, 50)
        sma200 = _compute_sma(etf_df, 200)
        record["etf_sma50"] = round(sma50, 2) if sma50 is not None else None
        record["etf_sma200"] = round(sma200, 2) if sma200 is not None else None

        # 1. Relative Strength
        if spy_prices is not None and not spy_prices.empty:
            rs = _compute_relative_strength(etf_df, spy_prices)
        else:
            rs = {"rs_1m": None, "rs_3m": None, "rs_6m": None, "relative_strength_score": 50.0}
        record.update(rs)

        # 2. Breadth
        breadth = _compute_breadth(sector_name, stock_prices, universe)
        record.update(breadth)

        # 3. Analyst Revisions
        analyst = _compute_analyst_revisions(sector_name, analyst_data, universe)
        record.update(analyst)

        # 4. Momentum
        momentum = _compute_momentum(etf_df)
        record.update(momentum)

        # 5. Volume
        volume = _compute_volume(etf_df)
        record.update(volume)

        records.append(record)

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("sector")

    log.info(f"Sector trend analysis complete for {len(df)} sectors")
    return df


# ---------------------------------------------------------------------------
# Historical trend computation (for RRG chart trails)
# ---------------------------------------------------------------------------

def _rolling_rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute rolling RSI as a full Series."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _margin_score_vec(val: pd.Series, ref: pd.Series) -> pd.Series:
    """Vectorized margin_score: how far val is above ref, mapped to 0-1."""
    pct = (val - ref) / ref.abs().replace(0, np.nan)
    clamped = pct.clip(-0.20, 0.20)
    return (clamped + 0.20) / 0.40


def _score_series(series: pd.Series, breakpoints: list) -> pd.Series:
    """Apply piecewise-linear metric_score to each element of a Series."""
    return series.apply(lambda x: metric_score(x, breakpoints) if pd.notna(x) else np.nan)


def compute_trend_history(
    etf_prices: Dict[str, pd.DataFrame],
    sample_interval: int | None = None,
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Compute historical RS and momentum scores for RRG chart trails.

    Uses only ETF price data (no stock breadth or analyst data needed).
    Samples every ``sample_interval`` trading days (~weekly by default).

    Returns:
        { date_str: { sector_name: { rs_score, momentum_score } } }
    """
    if sample_interval is None:
        sample_interval = TREND_HISTORY_SAMPLE_INTERVAL

    spy_df = etf_prices.get(SPY_TICKER)
    if spy_df is None or spy_df.empty:
        log.warning("No SPY data for trend history computation")
        return {}

    spy_close = spy_df["Close"]

    # Pre-compute SPY rolling returns
    spy_ret_1m = spy_close.pct_change(21)
    spy_ret_3m = spy_close.pct_change(63)
    spy_ret_6m = spy_close.pct_change(126)

    history: Dict[str, Dict[str, Dict[str, float]]] = {}

    for etf_ticker, sector_name in SECTOR_ETFS.items():
        etf_df = etf_prices.get(etf_ticker)
        if etf_df is None or etf_df.empty:
            continue

        close = etf_df["Close"]

        # --- RS Score (vectorized) ---
        etf_ret_1m = close.pct_change(21)
        etf_ret_3m = close.pct_change(63)
        etf_ret_6m = close.pct_change(126)

        excess_1m = etf_ret_1m - spy_ret_1m
        excess_3m = etf_ret_3m - spy_ret_3m
        excess_6m = etf_ret_6m - spy_ret_6m

        s1m = _score_series(excess_1m, _RS_BREAKPOINTS)
        s3m = _score_series(excess_3m, _RS_BREAKPOINTS)
        s6m = _score_series(excess_6m, _RS_BREAKPOINTS)

        # Weighted average with NaN-safe re-normalization
        m1, m3, m6 = s1m.notna(), s3m.notna(), s6m.notna()
        num = s1m.fillna(0) * 0.50 * m1 + s3m.fillna(0) * 0.30 * m3 + s6m.fillna(0) * 0.20 * m6
        den = 0.50 * m1 + 0.30 * m3 + 0.20 * m6
        rs_score = num / den.replace(0, np.nan)

        # --- Momentum Score (vectorized) ---
        rsi = _rolling_rsi_series(close)
        rsi_score = _score_series(rsi, _RSI_TREND_BREAKPOINTS)

        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()

        a1 = _margin_score_vec(close, sma50)
        a2 = _margin_score_vec(close, sma200)
        a3 = _margin_score_vec(sma50, sma200)

        am1, am2, am3 = a1.notna(), a2.notna(), a3.notna()
        align_sum = a1.fillna(0) * am1 + a2.fillna(0) * am2 + a3.fillna(0) * am3
        align_cnt = am1.astype(int) + am2.astype(int) + am3.astype(int)
        alignment = (align_sum / align_cnt.replace(0, np.nan)) * 100

        momentum_score = 0.5 * rsi_score + 0.5 * alignment

        # --- Sample at intervals ---
        both_valid = rs_score.notna() & momentum_score.notna()
        valid_idx = rs_score.index[both_valid]
        sample_idx = valid_idx[::sample_interval]

        for date in sample_idx:
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]
            if date_str not in history:
                history[date_str] = {}
            history[date_str][sector_name] = {
                "rs_score": round(float(rs_score.loc[date]), 1),
                "momentum_score": round(float(momentum_score.loc[date]), 1),
            }

    log.info(f"Trend history computed: {len(history)} dates, up to {len(SECTOR_ETFS)} sectors")
    return history
