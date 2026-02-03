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
    for period in SMA_PERIODS:
        if len(close) >= period:
            sma = ta.sma(close, length=period)
            if sma is not None and not sma.empty:
                sma_values[period] = float(sma.iloc[-1])
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

    # Composite technical score (weighted, already 0-100)
    result["technical_score"] = (
        TECH_WEIGHT_TREND * result["trend_score"].fillna(50)
        + TECH_WEIGHT_MOMENTUM * result["momentum_score"].fillna(50)
        + TECH_WEIGHT_VOLATILITY * result["volatility_score"].fillna(50)
        + TECH_WEIGHT_VOLUME * result["volume_score"].fillna(50)
    )

    return result
