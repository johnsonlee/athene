"""Collect OHLCV data for global asset class ETFs.

Fetches daily OHLCV for representative ETFs across major asset classes
(US/EU/JP/EM equity, crypto, gold, treasuries, cash, corporate bonds)
used by the capital flow pipeline to compute money flow proxies.

Supports two modes:
- **Live fetch**: `collect_capital_flow_etfs()` downloads historical OHLCV from yfinance.
- **Stored daily**: `load_capital_flow_etfs_from_collected()` reconstructs DataFrames
  from stored `collected/YYYY/MM/DD/capital_flow_etfs.json` daily slices.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import yfinance as yf

from engine.config import (
    CAPITAL_FLOW_ETFS,
    CAPITAL_FLOW_LOOKBACK_WEEKS,
    CAPITAL_FLOW_WINDOW_DAYS,
)
from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)


def collect_capital_flow_etfs(
    lookback_weeks: int | None = None,
    end_date: str | None = None,
    start_date: str | None = None,
) -> Dict[str, pd.DataFrame]:
    """Fetch OHLCV for global asset class ETFs.

    Args:
        lookback_weeks: Number of weekly windows to cover. Defaults to
            CAPITAL_FLOW_LOOKBACK_WEEKS.
        end_date: End date (YYYY-MM-DD). Defaults to now.
        start_date: Start date (YYYY-MM-DD). If provided, overrides
            the lookback_weeks calculation.

    Returns:
        dict mapping ticker (e.g. "SPY", "GLD") -> DataFrame with
        columns [Open, High, Low, Close, Volume] indexed by date.
    """
    weeks = lookback_weeks or CAPITAL_FLOW_LOOKBACK_WEEKS
    tickers = list(CAPITAL_FLOW_ETFS.keys())

    from engine.utils.market_calendar import us_market_now
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else us_market_now()
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # Extra buffer for weekends/holidays
        calendar_days = weeks * 7 + 30
        start = end - timedelta(days=calendar_days)

    log.info(f"Downloading capital flow ETF prices: {len(tickers)} tickers, "
             f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    rate_limiter.wait()

    result: Dict[str, pd.DataFrame] = {}

    try:
        data = yf.download(
            tickers,
            start=start.strftime("%Y-%m-%d"),
            end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        log.error(f"Capital flow ETF batch download failed: {e}")
        return result

    if data.empty:
        log.warning("Capital flow ETF download returned empty data")
        return result

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = data.copy()
            else:
                df = (
                    data[ticker].copy()
                    if ticker in data.columns.get_level_values(0)
                    else pd.DataFrame()
                )
            if not df.empty:
                df = df.dropna(how="all")
                if not df.empty:
                    result[ticker] = df
        except (KeyError, Exception) as e:
            log.warning(f"No capital flow ETF data for {ticker}: {e}")

    log.info(f"Capital flow ETF data collected for {len(result)}/{len(tickers)} tickers")
    return result


def collect_capital_flow_etfs_daily(target_date: str) -> Dict[str, dict]:
    """Fetch OHLCV for the latest trading day up to *target_date*.

    Fetches 5 calendar days ending at target_date+1 for 9 capital flow ETFs.

    Returns:
        dict mapping ticker (e.g. "SPY", "GLD") -> {Open, High, Low, Close, Volume}
    """
    tickers = list(CAPITAL_FLOW_ETFS.keys())
    target = pd.Timestamp(target_date)
    start = (target - timedelta(days=5)).strftime("%Y-%m-%d")
    end = (target + timedelta(days=1)).strftime("%Y-%m-%d")

    log.info(f"Downloading daily capital flow ETF prices: {len(tickers)} tickers")
    rate_limiter.wait()

    result: Dict[str, dict] = {}

    try:
        data = yf.download(
            tickers,
            start=start,
            end=end,
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        log.error(f"Capital flow ETF daily download failed: {e}")
        return result

    if data.empty:
        log.warning("Capital flow ETF daily download returned empty data")
        return result

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = data.copy()
            else:
                df = (
                    data[ticker].copy()
                    if ticker in data.columns.get_level_values(0)
                    else pd.DataFrame()
                )
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
            log.warning(f"No daily capital flow ETF data for {ticker}: {e}")

    log.info(f"Daily capital flow ETF data collected for {len(result)}/{len(tickers)} tickers")
    return result


def load_capital_flow_etfs_from_collected(
    lookback_weeks: int | None = None,
    end_date: str | None = None,
) -> Dict[str, pd.DataFrame]:
    """Reconstruct OHLCV DataFrames from stored daily slices.

    Scans ``collected/YYYY/MM/DD/capital_flow_etfs.json`` files and assembles them
    into per-ticker DataFrames matching the format returned by
    ``collect_capital_flow_etfs()``.

    Args:
        lookback_weeks: Number of weekly windows to cover (determines how far
            back to load).  Defaults to CAPITAL_FLOW_LOOKBACK_WEEKS.
        end_date: Latest date to include (YYYY-MM-DD).  Defaults to today.

    Returns:
        dict mapping ticker -> DataFrame[Open, High, Low, Close, Volume]
        indexed by date, sorted chronologically.
    """
    from engine.collect import COLLECTED_DIR

    weeks = lookback_weeks or CAPITAL_FLOW_LOOKBACK_WEEKS
    from engine.utils.market_calendar import us_market_now
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else us_market_now()
    # Extra buffer for weekends/holidays (same as live fetch)
    calendar_days = weeks * 7 + 30
    start = end - timedelta(days=calendar_days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    if not os.path.isdir(COLLECTED_DIR):
        log.warning(f"No collected/ directory found — falling back to live fetch")
        return {}

    # Scan date directories in range
    from engine.collect import iter_date_dirs
    rows_by_ticker: Dict[str, list] = {}
    loaded_dates = 0

    for date_str, dir_path in iter_date_dirs():
        if date_str < start_str or date_str > end_str:
            continue
        path = os.path.join(dir_path, "capital_flow_etfs.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                daily = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log.warning(f"Failed to read {path}: {e}")
            continue

        loaded_dates += 1
        for ticker, ohlcv in daily.items():
            if ticker not in rows_by_ticker:
                rows_by_ticker[ticker] = []
            rows_by_ticker[ticker].append({
                "Date": pd.Timestamp(date_str),
                "Open": float(ohlcv["Open"]),
                "High": float(ohlcv["High"]),
                "Low": float(ohlcv["Low"]),
                "Close": float(ohlcv["Close"]),
                "Volume": int(ohlcv["Volume"]),
            })

    if not rows_by_ticker:
        log.warning(f"No capital_flow_etfs data found in collected/ "
                    f"({start_str} to {end_str}) — falling back to live fetch")
        return {}

    result: Dict[str, pd.DataFrame] = {}
    for ticker, rows in rows_by_ticker.items():
        df = pd.DataFrame(rows).set_index("Date").sort_index()
        result[ticker] = df

    log.info(f"Loaded capital flow ETF data from collected/: "
             f"{len(result)} tickers, {loaded_dates} trading days "
             f"({start_str} to {end_str})")
    return result
