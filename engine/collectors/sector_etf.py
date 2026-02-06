"""Collect OHLCV data for sector ETFs and SPY benchmark.

Fetches 1 year of daily OHLCV for 11 SPDR Select Sector ETFs plus SPY,
used by the trend pipeline to compute sector-level signals.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import yfinance as yf

from engine.config import SECTOR_ETFS, SPY_TICKER, PRICE_HISTORY_DAYS
from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)


def collect_sector_etfs_daily(target_date: str) -> Dict[str, dict]:
    """Fetch OHLCV for the latest trading day up to *target_date*.

    Fetches 5 calendar days ending at target_date+1 for 11 sector ETFs + SPY.

    Returns:
        dict mapping ticker (e.g. "XLK", "SPY") -> {Open, High, Low, Close, Volume}
    """
    tickers = list(SECTOR_ETFS.keys()) + [SPY_TICKER]
    target = pd.Timestamp(target_date)
    start = (target - timedelta(days=5)).strftime("%Y-%m-%d")
    end = (target + timedelta(days=1)).strftime("%Y-%m-%d")

    log.info(f"Downloading daily sector ETF prices: {len(tickers)} tickers")
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
        log.error(f"Sector ETF daily download failed: {e}")
        return result

    if data.empty:
        log.warning("Sector ETF daily download returned empty data")
        return result

    for ticker in tickers:
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
            log.warning(f"No daily ETF data for {ticker}: {e}")

    log.info(f"Daily sector ETF data collected for {len(result)}/{len(tickers)} tickers")
    return result


def collect_sector_etfs(start_date: str | None = None, end_date: str | None = None) -> Dict[str, pd.DataFrame]:
    """Fetch OHLCV for 11 sector ETFs + SPY benchmark.

    Args:
        start_date: Start date (YYYY-MM-DD). Defaults to now - PRICE_HISTORY_DAYS.
        end_date: End date (YYYY-MM-DD). Defaults to now.

    Returns:
        dict mapping ticker (e.g. "XLK", "SPY") -> DataFrame[Date, Open, High, Low, Close, Volume]
    """
    tickers = list(SECTOR_ETFS.keys()) + [SPY_TICKER]
    from engine.utils.market_calendar import us_market_now
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else us_market_now()
    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else end - timedelta(days=PRICE_HISTORY_DAYS)

    log.info(f"Downloading sector ETF prices: {len(tickers)} tickers")
    rate_limiter.wait()

    result: Dict[str, pd.DataFrame] = {}

    try:
        data = yf.download(
            tickers,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        log.error(f"Sector ETF batch download failed: {e}")
        return result

    if data.empty:
        log.warning("Sector ETF download returned empty data")
        return result

    for ticker in tickers:
        try:
            df = data[ticker].copy() if ticker in data.columns.get_level_values(0) else pd.DataFrame()
            if not df.empty:
                df = df.dropna(how="all")
                if not df.empty:
                    result[ticker] = df
        except (KeyError, Exception) as e:
            log.warning(f"No ETF price data for {ticker}: {e}")

    log.info(f"Sector ETF data collected for {len(result)}/{len(tickers)} tickers")
    return result
