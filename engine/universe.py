"""Build the stock universe from S&P 500 + NASDAQ 100 via Wikipedia."""

from __future__ import annotations

import pandas as pd
import requests
from io import StringIO

from engine.config import EXTRA_TICKERS
from engine.utils.logger import get_logger

log = get_logger(__name__)

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

_HEADERS = {
    "User-Agent": "Athene/1.0 (stock screener; https://github.com/johnsonlee/athene)"
}


def _fetch_html(url: str) -> str:
    """Fetch HTML content with a proper User-Agent."""
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def _fetch_sp500() -> pd.DataFrame:
    """Scrape S&P 500 constituents from Wikipedia."""
    html = _fetch_html(SP500_URL)
    tables = pd.read_html(StringIO(html))
    df = tables[0][["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]].copy()
    df.columns = ["ticker", "name", "sector", "industry"]
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)  # BRK.B → BRK-B
    return df


def _fetch_nasdaq100() -> pd.DataFrame:
    """Scrape NASDAQ 100 constituents from Wikipedia."""
    html = _fetch_html(NASDAQ100_URL)
    tables = pd.read_html(StringIO(html))
    # The constituents table has a "Ticker" column
    for table in tables:
        cols = [str(c).lower() for c in table.columns]
        if "ticker" in cols or "symbol" in cols:
            ticker_col = table.columns[cols.index("ticker") if "ticker" in cols else cols.index("symbol")]
            name_col = table.columns[cols.index("company") if "company" in cols else 1]
            sector_col = None
            if "gics sector" in cols:
                sector_col = table.columns[cols.index("gics sector")]
            elif "sector" in cols:
                sector_col = table.columns[cols.index("sector")]

            df = pd.DataFrame({
                "ticker": table[ticker_col].str.replace(".", "-", regex=False),
                "name": table[name_col],
                "sector": table[sector_col] if sector_col else "Unknown",
                "industry": "",
            })
            return df
    raise ValueError("Could not find NASDAQ 100 constituents table")


def build_universe() -> pd.DataFrame:
    """Return deduplicated universe of S&P 500 + NASDAQ 100 stocks.

    Returns:
        DataFrame with columns: ticker, name, sector, industry
    """
    log.info("Fetching S&P 500 constituents...")
    sp500 = _fetch_sp500()
    log.info(f"  S&P 500: {len(sp500)} tickers")

    log.info("Fetching NASDAQ 100 constituents...")
    nasdaq = _fetch_nasdaq100()
    log.info(f"  NASDAQ 100: {len(nasdaq)} tickers")

    universe = pd.concat([sp500, nasdaq], ignore_index=True)

    # Append extra tickers from config
    if EXTRA_TICKERS:
        extra = pd.DataFrame(EXTRA_TICKERS)
        universe = pd.concat([universe, extra], ignore_index=True)
        log.info(f"  Extra tickers added: {[t['ticker'] for t in EXTRA_TICKERS]}")

    universe = universe.drop_duplicates(subset="ticker").reset_index(drop=True)
    universe = universe.sort_values("ticker").reset_index(drop=True)

    log.info(f"Universe built: {len(universe)} unique tickers")
    return universe
