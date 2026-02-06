"""Collect OHLCV price data via yfinance batch download."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import yfinance as yf

from engine.config import PRICE_HISTORY_DAYS, BATCH_SIZE
from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)


def collect_prices_daily(tickers: list[str], target_date: str) -> Dict[str, dict]:
    """Download OHLCV for the latest trading day up to *target_date*.

    Fetches 5 calendar days ending at target_date+1 so that the target
    date (or the most recent trading day before it) is included.

    Returns:
        dict mapping ticker -> {Open, High, Low, Close, Volume} for
        the latest available row.
    """
    target = pd.Timestamp(target_date)
    start = (target - timedelta(days=5)).strftime("%Y-%m-%d")
    end = (target + timedelta(days=1)).strftime("%Y-%m-%d")

    result: Dict[str, dict] = {}

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        log.info(f"Downloading daily prices: batch {i // BATCH_SIZE + 1} ({len(batch)} tickers)")
        rate_limiter.wait()

        try:
            data = yf.download(
                batch,
                start=start,
                end=end,
                group_by="ticker",
                threads=True,
                progress=False,
            )
        except Exception as e:
            log.error(f"Batch download failed: {e}")
            continue

        if data.empty:
            continue

        if len(batch) == 1:
            ticker = batch[0]
            df = data.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna()
            if not df.empty:
                last = df.iloc[-1]
                result[ticker] = {
                    "Open": float(last["Open"]),
                    "High": float(last["High"]),
                    "Low": float(last["Low"]),
                    "Close": float(last["Close"]),
                    "Volume": int(last["Volume"]),
                }
        else:
            for ticker in batch:
                try:
                    df = data[ticker].copy() if ticker in data.columns.get_level_values(0) else pd.DataFrame()
                    if not df.empty:
                        df = df.dropna(how="all")
                        if not df.empty:
                            last = df.iloc[-1]
                            result[ticker] = {
                                "Open": float(last["Open"]),
                                "High": float(last["High"]),
                                "Low": float(last["Low"]),
                                "Close": float(last["Close"]),
                                "Volume": int(last["Volume"]),
                            }
                except (KeyError, Exception) as e:
                    log.warning(f"No price data for {ticker}: {e}")

    log.info(f"Daily price data collected for {len(result)}/{len(tickers)} tickers")
    return result


def collect_prices(tickers: list[str], start_date: str | None = None, end_date: str | None = None) -> Dict[str, pd.DataFrame]:
    """Download daily OHLCV for all tickers in batches.

    Args:
        tickers: List of ticker symbols.
        start_date: Start date (YYYY-MM-DD). Defaults to now - PRICE_HISTORY_DAYS.
        end_date: End date (YYYY-MM-DD). Defaults to now.

    Returns:
        dict mapping ticker → DataFrame with columns:
        Date (index), Open, High, Low, Close, Volume
    """
    from engine.utils.market_calendar import us_market_now
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else us_market_now()
    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else end - timedelta(days=PRICE_HISTORY_DAYS)
    result: Dict[str, pd.DataFrame] = {}

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        log.info(f"Downloading prices: batch {i // BATCH_SIZE + 1} ({len(batch)} tickers)")
        rate_limiter.wait()

        try:
            data = yf.download(
                batch,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                group_by="ticker",
                threads=True,
                progress=False,
            )
        except Exception as e:
            log.error(f"Batch download failed: {e}")
            continue

        if data.empty:
            continue

        # Single ticker returns flat columns; multi-ticker returns MultiIndex
        if len(batch) == 1:
            ticker = batch[0]
            df = data.copy()
            if not df.empty:
                # Flatten MultiIndex columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                result[ticker] = df.dropna()
        else:
            for ticker in batch:
                try:
                    df = data[ticker].copy() if ticker in data.columns.get_level_values(0) else pd.DataFrame()
                    if not df.empty:
                        df = df.dropna(how="all")
                        if not df.empty:
                            result[ticker] = df
                except (KeyError, Exception) as e:
                    log.warning(f"No price data for {ticker}: {e}")

    log.info(f"Price data collected for {len(result)}/{len(tickers)} tickers")
    return result
