"""Technical analysis: trend, momentum, volatility, and volume sub-factors.

v6: MACD normalized by price, volume direction-aware, BB width + historical
    volatility for true vol measurement, trend alignment margin-weighted.
"""

from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
import pandas_ta as ta

from engine.config import (
    SMA_PERIODS,
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    BB_PERIOD,
    BB_STD,
    TECH_WEIGHT_TREND,
    TECH_WEIGHT_MOMENTUM,
    TECH_WEIGHT_VOLATILITY,
    TECH_WEIGHT_VOLUME,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)


def _margin_score(val: float, ref: float) -> float:
    """Score how far *val* is above *ref* as a 0-1 value.

    Maps percentage margin to [0, 1]:
      +20% or more above → 1.0
      exactly at ref     → 0.5
      -20% or more below → 0.0
    """
    if ref == 0:
        return 0.5
    pct = (val - ref) / abs(ref)
    clamped = max(-0.20, min(0.20, pct))
    return (clamped + 0.20) / 0.40


def _compute_indicators(df: pd.DataFrame) -> dict:
    """Compute technical indicators for a single ticker's OHLCV DataFrame."""
    close = df["Close"]
    volume = df["Volume"]
    high = df["High"]
    low = df["Low"]
    result = {}

    if len(close) < 20:
        return result

    latest_close = float(close.iloc[-1])
    result["close"] = latest_close

    # --- Trend: SMA alignment ---
    sma_values = {}
    sma_series: dict[int, pd.Series] = {}
    for period in SMA_PERIODS:
        if len(close) >= period:
            sma = ta.sma(close, length=period)
            if sma is not None and not sma.empty:
                sma_values[period] = float(sma.iloc[-1])
                sma_series[period] = sma
                result[f"sma_{period}"] = sma_values[period]

    # Bullish alignment: price > SMA20 > SMA50 > SMA200
    # v6: margin-weighted — degree above/below SMA matters, not just sign
    alignment_score = 0.0
    if sma_values:
        margin_scores = []
        sorted_periods = sorted(sma_values.keys())
        # Price above each SMA (weighted by margin)
        for p in sorted_periods:
            margin_scores.append(_margin_score(latest_close, sma_values[p]))
        # Shorter SMA above longer SMA (weighted by margin)
        for i in range(len(sorted_periods) - 1):
            margin_scores.append(
                _margin_score(sma_values[sorted_periods[i]], sma_values[sorted_periods[i + 1]])
            )
        alignment_score = sum(margin_scores) / len(margin_scores) if margin_scores else 0.0
    result["trend_alignment"] = alignment_score

    # --- MA20/50 directional signal: position + slope ---
    # gap = (MA20 - MA50) / MA50 captures regime (positive = MA20 above MA50)
    # slope = change in gap over 10 days captures momentum of the crossover
    _MA_SLOPE_LOOKBACK = 10
    if 20 in sma_series and 50 in sma_series:
        s20, s50 = sma_series[20], sma_series[50]
        gap_now = (float(s20.iloc[-1]) - float(s50.iloc[-1])) / float(s50.iloc[-1])
        result["ma_gap"] = gap_now
        if len(s20) > _MA_SLOPE_LOOKBACK and len(s50) > _MA_SLOPE_LOOKBACK:
            s50_prev = float(s50.iloc[-1 - _MA_SLOPE_LOOKBACK])
            if s50_prev != 0:
                gap_prev = (float(s20.iloc[-1 - _MA_SLOPE_LOOKBACK]) - s50_prev) / s50_prev
                result["ma_gap_slope"] = gap_now - gap_prev

    # --- Momentum: RSI ---
    rsi = ta.rsi(close, length=RSI_PERIOD)
    if rsi is not None and not rsi.empty:
        rsi_val = float(rsi.iloc[-1])
        result["rsi"] = rsi_val
        # Normalize RSI to -1..1 (50 = neutral)
        result["rsi_score"] = (rsi_val - 50) / 50

    # --- Momentum: MACD ---
    macd_df = ta.macd(close, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    if macd_df is not None and not macd_df.empty:
        macd_hist_col = [c for c in macd_df.columns if "h" in c.lower() or "hist" in c.lower()]
        macd_line_col = [c for c in macd_df.columns if "macd" in c.lower() and "s" not in c.lower() and "h" not in c.lower()]
        if macd_hist_col:
            result["macd_histogram"] = float(macd_df[macd_hist_col[0]].iloc[-1])
        if macd_line_col:
            result["macd_line"] = float(macd_df[macd_line_col[0]].iloc[-1])

    # v6: normalize MACD histogram by close price (remove price-level bias)
    if "macd_histogram" in result and latest_close > 0:
        result["macd_histogram_pct"] = (result["macd_histogram"] / latest_close) * 100

    # --- Volatility: Bollinger Bands ---
    bbands = ta.bbands(close, length=BB_PERIOD, std=BB_STD)
    if bbands is not None and not bbands.empty:
        upper_col = [c for c in bbands.columns if "bbu" in c.lower()]
        lower_col = [c for c in bbands.columns if "bbl" in c.lower()]
        if upper_col and lower_col:
            upper = float(bbands[upper_col[0]].iloc[-1])
            lower = float(bbands[lower_col[0]].iloc[-1])
            width = upper - lower
            if width > 0:
                # %B: 0 = at lower band, 1 = at upper band
                bb_position = (latest_close - lower) / width
                result["bb_position"] = bb_position
                result["bb_upper"] = upper
                result["bb_lower"] = lower
            # v6: BB bandwidth — true volatility measure
            mid_col = [c for c in bbands.columns if "bbm" in c.lower()]
            if mid_col:
                mid = float(bbands[mid_col[0]].iloc[-1])
                if mid > 0:
                    result["bb_width"] = (upper - lower) / mid

    # v6: Historical volatility (annualized std of 20-day returns)
    if len(close) >= 21:
        daily_returns = close.pct_change().dropna()
        if len(daily_returns) >= 20:
            recent_returns = daily_returns.tail(20)
            result["hist_volatility"] = float(recent_returns.std() * np.sqrt(252))

    # --- Volume: current vs average ---
    if len(volume) >= 20:
        avg_vol = float(volume.tail(20).mean())
        latest_vol = float(volume.iloc[-1])
        if avg_vol > 0:
            result["volume_ratio"] = latest_vol / avg_vol
            result["avg_volume_20d"] = avg_vol

    # v6: signed volume ratio (positive on up-day, negative on down-day)
    if len(close) >= 2 and "volume_ratio" in result:
        prev_close = float(close.iloc[-2])
        if prev_close > 0:
            daily_ret = (latest_close - prev_close) / prev_close
            result["daily_return"] = daily_ret
            if abs(daily_ret) > 1e-4:
                result["signed_volume_ratio"] = result["volume_ratio"] * (1 if daily_ret > 0 else -1)
            else:
                result["signed_volume_ratio"] = 0.0  # flat day → neutral

    # --- KDJ ---
    stoch = ta.stoch(high, low, close, k=14, d=3)
    if stoch is not None and not stoch.empty:
        k_col = [c for c in stoch.columns if "k" in c.lower()]
        d_col = [c for c in stoch.columns if "d" in c.lower()]
        if k_col:
            result["stoch_k"] = float(stoch[k_col[0]].iloc[-1])
        if d_col:
            result["stoch_d"] = float(stoch[d_col[0]].iloc[-1])

    # --- Reversal signals (cycle turning point detection) ---

    # MACD reversal: histogram improving from negative territory
    if "macd_histogram" in result:
        macd_hist_series = None
        if macd_df is not None and macd_hist_col:
            macd_hist_series = macd_df[macd_hist_col[0]].dropna()
        if macd_hist_series is not None and len(macd_hist_series) >= 10:
            curr_hist = float(macd_hist_series.iloc[-1])
            hist_5d = float(macd_hist_series.iloc[-6])
            # Rate of change in histogram (positive = improving)
            if abs(hist_5d) > 1e-8:
                result["macd_reversal_raw"] = (curr_hist - hist_5d) / abs(hist_5d)
            else:
                result["macd_reversal_raw"] = 0.0
            # Also store whether histogram crossed zero recently
            signs = macd_hist_series.tail(10).apply(lambda x: 1 if x > 0 else -1)
            sign_changes = (signs.diff().abs() > 0).sum()
            result["macd_zero_cross_count"] = int(sign_changes)

    # KDJ reversal: K crossing above D (golden cross), especially from oversold
    if "stoch_k" in result and "stoch_d" in result:
        k_val = result["stoch_k"]
        d_val = result["stoch_d"]
        # Current K-D spread (positive = bullish)
        result["kdj_spread"] = k_val - d_val
        # Check for recent golden cross (K was below D, now above)
        if stoch is not None and not stoch.empty:
            k_col_name = [c for c in stoch.columns if "k" in c.lower()]
            d_col_name = [c for c in stoch.columns if "d" in c.lower()]
            if k_col_name and d_col_name:
                k_s = stoch[k_col_name[0]].dropna()
                d_s = stoch[d_col_name[0]].dropna()
                if len(k_s) >= 6 and len(d_s) >= 6:
                    # Was K < D five days ago?
                    past_bearish = float(k_s.iloc[-6]) < float(d_s.iloc[-6])
                    now_bullish = k_val > d_val
                    result["kdj_golden_cross"] = 1.0 if (past_bearish and now_bullish) else 0.0

    # RSI reversal: recovering from oversold territory
    if rsi is not None and not rsi.empty and len(rsi.dropna()) >= 10:
        rsi_clean = rsi.dropna()
        rsi_current = float(rsi_clean.iloc[-1])
        rsi_min_10d = float(rsi_clean.tail(10).min())
        # Recovery = how much RSI has risen from its 10-day low
        # Only meaningful if the low was in oversold territory (< 35)
        if rsi_min_10d < 35:
            result["rsi_recovery"] = rsi_current - rsi_min_10d
        else:
            result["rsi_recovery"] = 0.0
        result["rsi_10d_min"] = rsi_min_10d

    # Pullback proximity: price near key SMA support
    if sma_values and latest_close > 0:
        # Distance to nearest support SMA (as % of price)
        distances = {}
        for period, sma_val in sma_values.items():
            dist_pct = (latest_close - sma_val) / latest_close * 100
            # Only consider SMAs below price (support) or slightly above (pullback to)
            if -5 <= dist_pct <= 10:  # within -5% to +10% of SMA
                distances[period] = abs(dist_pct)
        if distances:
            # Closest SMA within range
            result["pullback_proximity"] = min(distances.values())
        else:
            result["pullback_proximity"] = 99.0  # far from any support

    return result


def analyze_technical(prices: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute technical indicators for all tickers.

    Returns:
        DataFrame indexed by ticker with indicator columns.
    """
    records = []
    for ticker, df in prices.items():
        try:
            indicators = _compute_indicators(df)
            if indicators:
                indicators["ticker"] = ticker
                records.append(indicators)
        except Exception as e:
            log.warning(f"Technical analysis failed for {ticker}: {e}")

    result = pd.DataFrame(records)
    if not result.empty:
        result = result.set_index("ticker")

    log.info(f"Technical analysis complete for {len(result)} tickers")
    return result


def compute_technical_subscores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical sub-factor scores using absolute metric scoring (0-100).

    v6: MACD uses price-normalized histogram, volume is direction-aware,
    volatility uses BB width + historical vol instead of BB position.

    v7: Also computes ``tech_data_completeness`` (0-1) measuring what
    fraction of scored technical metrics have real data.
    """
    from engine.scorer.absolute import (
        score_trend_alignment, score_rsi, score_macd_histogram,
        score_bb_width, score_hist_volatility, score_directional_volume,
    )

    result = df.copy()

    # Trend sub-score (trend_alignment 0-1 → 0-100, now margin-weighted)
    result["trend_score"] = result["trend_alignment"].apply(score_trend_alignment) if "trend_alignment" in result.columns else 50.0

    # Momentum sub-score: avg(rsi_score, macd_score)
    result["rsi_abs_score"] = result["rsi"].apply(score_rsi) if "rsi" in result.columns else 50.0
    # v6: use price-normalized MACD histogram (% of close)
    result["macd_abs_score"] = result["macd_histogram_pct"].apply(score_macd_histogram) if "macd_histogram_pct" in result.columns else 50.0
    result["momentum_score"] = result[["rsi_abs_score", "macd_abs_score"]].mean(axis=1)

    # Volatility sub-score: avg(bb_width, hist_vol) — true volatility (v6)
    bb_w = result["bb_width"].apply(score_bb_width) if "bb_width" in result.columns else pd.Series(50.0, index=result.index)
    hv = result["hist_volatility"].apply(score_hist_volatility) if "hist_volatility" in result.columns else pd.Series(50.0, index=result.index)
    result["volatility_score"] = (bb_w + hv) / 2

    # Volume sub-score: direction-aware (v6)
    result["volume_score"] = result["signed_volume_ratio"].apply(score_directional_volume) if "signed_volume_ratio" in result.columns else 50.0

    # --- Reversal sub-scores (cycle turning point signals) ---
    from engine.scorer.absolute import metric_score

    # MACD reversal: histogram improving from negative
    # Breakpoints: -0.5 (worsening) -> 10, 0 (flat) -> 40, 0.5 (improving) -> 65, 1.5 (strong turn) -> 90
    _MACD_REV_BP = [(-1.0, 5), (-0.5, 10), (0.0, 40), (0.5, 65), (1.0, 80), (2.0, 95)]
    if "macd_reversal_raw" in result.columns:
        result["macd_reversal_score"] = result["macd_reversal_raw"].apply(
            lambda x: metric_score(x, _MACD_REV_BP, missing_default=40.0)
        )
    else:
        result["macd_reversal_score"] = 40.0

    # Zero-cross bonus: if MACD crossed zero in last 10 bars, boost
    if "macd_zero_cross_count" in result.columns:
        # Cross happened -> add up to 10 points
        result["macd_reversal_score"] = result["macd_reversal_score"] + (
            result["macd_zero_cross_count"].clip(upper=2) * 5
        )
        result["macd_reversal_score"] = result["macd_reversal_score"].clip(0, 100)

    # KDJ reversal: K-D spread + golden cross
    # K-D spread: -20 -> 10, 0 -> 45, 10 -> 65, 25 -> 85
    _KDJ_SPREAD_BP = [(-30, 5), (-15, 20), (0, 45), (10, 65), (20, 80), (30, 90)]
    if "kdj_spread" in result.columns:
        base_kdj = result["kdj_spread"].apply(
            lambda x: metric_score(x, _KDJ_SPREAD_BP, missing_default=45.0)
        )
    else:
        base_kdj = pd.Series(45.0, index=result.index)

    # Golden cross bonus: +15 points if K crossed above D recently
    if "kdj_golden_cross" in result.columns:
        base_kdj = base_kdj + result["kdj_golden_cross"] * 15

    # Oversold bonus: if K < 30 or recently was, add up to 10 points
    if "stoch_k" in result.columns:
        oversold_bonus = ((50 - result["stoch_k"].clip(lower=20, upper=50)) / 30 * 10).clip(lower=0)
        base_kdj = base_kdj + oversold_bonus

    result["kdj_reversal_score"] = base_kdj.clip(0, 100)

    # RSI reversal: recovery from oversold
    # Recovery points: 0 -> 30, 5 -> 50, 15 -> 75, 30 -> 95
    _RSI_REC_BP = [(0, 30), (5, 50), (10, 65), (20, 80), (35, 95)]
    if "rsi_recovery" in result.columns:
        result["rsi_reversal_score"] = result["rsi_recovery"].apply(
            lambda x: metric_score(x, _RSI_REC_BP, missing_default=30.0)
        )
    else:
        result["rsi_reversal_score"] = 30.0

    # Pullback proximity: closer to SMA support = higher score
    # Distance: 0% (at SMA) -> 90, 2% -> 70, 5% -> 50, 10% -> 30, >10% -> 20
    _PULLBACK_BP = [(0, 90), (1, 80), (2, 70), (5, 50), (10, 30), (20, 15)]
    if "pullback_proximity" in result.columns:
        result["pullback_proximity_score"] = result["pullback_proximity"].apply(
            lambda x: metric_score(x, _PULLBACK_BP, missing_default=30.0)
        )
    else:
        result["pullback_proximity_score"] = 30.0

    # Composite reversal score (weighted average)
    result["reversal_score"] = (
        0.35 * result["macd_reversal_score"]
        + 0.30 * result["kdj_reversal_score"]
        + 0.25 * result["rsi_reversal_score"]
        + 0.10 * result["pullback_proximity_score"]
    )

    # MA20/50 directional signal ∈ (-1, +1)
    # Calibrated from 521 tickers × 1593 days (IC grid search, 22d horizon):
    #   k_gap=3, k_slope=30, w_gap=0.3 → IC=-0.0255 (p≈0, contrarian effect)
    # IC is negative: high signal (MA20 above MA50) predicts lower forward returns.
    # Signal is therefore used as a contrarian cycle indicator — bearish MA regime
    # means more mean-reversion upside, consistent with the reversal gate logic.
    import math
    if "ma_gap" in result.columns:
        gap_norm = result["ma_gap"].apply(lambda x: math.tanh(3 * x) if pd.notna(x) else 0.0)
        if "ma_gap_slope" in result.columns:
            slope_norm = result["ma_gap_slope"].apply(lambda x: math.tanh(30 * x) if pd.notna(x) else 0.0)
        else:
            slope_norm = pd.Series(0.0, index=result.index)
        result["ma_trend_signal"] = 0.3 * gap_norm + 0.7 * slope_norm
    else:
        result["ma_trend_signal"] = pd.Series(0.0, index=result.index)

    # Composite technical score (weighted, already 0-100)
    result["technical_score"] = (
        TECH_WEIGHT_TREND * result["trend_score"].fillna(50)
        + TECH_WEIGHT_MOMENTUM * result["momentum_score"].fillna(50)
        + TECH_WEIGHT_VOLATILITY * result["volatility_score"].fillna(50)
        + TECH_WEIGHT_VOLUME * result["volume_score"].fillna(50)
    )

    # --- v7: Data completeness ---
    _TECH_SCORED_COLS = [
        "trend_alignment",       # trend
        "rsi", "macd_histogram_pct",  # momentum
        "bb_width", "hist_volatility",  # volatility
        "signed_volume_ratio",   # volume
    ]
    present = pd.DataFrame(index=result.index)
    for col in _TECH_SCORED_COLS:
        if col in result.columns:
            present[col] = result[col].notna().astype(float)
        else:
            present[col] = 0.0
    result["tech_data_completeness"] = present.mean(axis=1)

    return result
