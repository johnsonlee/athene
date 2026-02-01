"""Technical analysis: trend, momentum, volatility, and volume sub-factors."""

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
    alignment_score = 0.0
    if sma_values:
        checks = 0
        passes = 0
        sorted_periods = sorted(sma_values.keys())
        # Price above each SMA
        for p in sorted_periods:
            checks += 1
            if latest_close > sma_values[p]:
                passes += 1
        # Shorter SMA above longer SMA
        for i in range(len(sorted_periods) - 1):
            checks += 1
            if sma_values[sorted_periods[i]] > sma_values[sorted_periods[i + 1]]:
                passes += 1
        alignment_score = passes / checks if checks > 0 else 0.0
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

    # --- Volatility: Bollinger Band position ---
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

    # --- Volume: current vs average ---
    if len(volume) >= 20:
        avg_vol = float(volume.tail(20).mean())
        latest_vol = float(volume.iloc[-1])
        if avg_vol > 0:
            result["volume_ratio"] = latest_vol / avg_vol
            result["avg_volume_20d"] = avg_vol

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


def compute_technical_subscores(df_z: pd.DataFrame) -> pd.DataFrame:
    """Given z-scored technical metrics, compute composite technical score.

    Expected z-scored columns: trend_alignment_z, rsi_score_z,
    macd_histogram_z, bb_position_z, volume_ratio_z
    """
    result = df_z.copy()

    # Trend sub-score
    trend_cols = ["trend_alignment_z"]
    available = [c for c in trend_cols if c in result.columns]
    result["trend_score"] = result[available].mean(axis=1) if available else 0.0

    # Momentum sub-score (RSI + MACD)
    momentum_cols = ["rsi_score_z", "macd_histogram_z"]
    available = [c for c in momentum_cols if c in result.columns]
    result["momentum_score"] = result[available].mean(axis=1) if available else 0.0

    # Volatility sub-score (BB position: higher = more bullish short-term)
    vol_cols = ["bb_position_z"]
    available = [c for c in vol_cols if c in result.columns]
    result["volatility_score"] = result[available].mean(axis=1) if available else 0.0

    # Volume sub-score
    volume_cols = ["volume_ratio_z"]
    available = [c for c in volume_cols if c in result.columns]
    result["volume_score"] = result[available].mean(axis=1) if available else 0.0

    # Composite technical score
    result["technical_score"] = (
        TECH_WEIGHT_TREND * result["trend_score"].fillna(0)
        + TECH_WEIGHT_MOMENTUM * result["momentum_score"].fillna(0)
        + TECH_WEIGHT_VOLATILITY * result["volatility_score"].fillna(0)
        + TECH_WEIGHT_VOLUME * result["volume_score"].fillna(0)
    )

    return result
