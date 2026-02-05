"""Collect fundamental / financial data via yfinance Ticker.info."""

from __future__ import annotations

from typing import Any, Dict

import yfinance as yf

from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)

# Keys we extract from yf.Ticker.info
INFO_KEYS = [
    "sector",
    "industry",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "priceToSalesTrailing12Months",
    "returnOnEquity",
    "returnOnAssets",
    "revenueGrowth",
    "earningsGrowth",
    "earningsQuarterlyGrowth",
    "debtToEquity",
    "freeCashflow",
    "totalRevenue",
    "totalDebt",
    "totalCash",
    "ebitda",
    "currentRatio",
    "marketCap",
    "dividendYield",
    "beta",
    "currentPrice",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "profitMargins",
    "operatingMargins",
    "grossMargins",
    # Company profile
    "longBusinessSummary",
    "fullTimeEmployees",
    "website",
    "city",
    "country",
]


def collect_fundamentals(tickers: list[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch fundamental data for each ticker.

    Returns:
        dict mapping ticker → dict of fundamental metrics
    """
    result: Dict[str, Dict[str, Any]] = {}

    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            log.info(f"Fundamentals: {i + 1}/{len(tickers)}")

        rate_limiter.wait()
        try:
            info = yf.Ticker(ticker).info
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                log.warning(f"No fundamental data for {ticker}")
                continue
            data = {key: info.get(key) for key in INFO_KEYS}
            result[ticker] = data
        except Exception as e:
            log.warning(f"Failed to fetch fundamentals for {ticker}: {e}")

    log.info(f"Fundamental data collected for {len(result)}/{len(tickers)} tickers")
    return result
