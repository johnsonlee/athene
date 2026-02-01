"""Collect recent news headlines for sentiment analysis."""

from __future__ import annotations

from typing import Dict, List

import yfinance as yf

from engine.config import NEWS_MAX_ARTICLES
from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)


def _fetch_yfinance_news(ticker: str) -> List[str]:
    """Get news titles from yfinance."""
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        titles = []
        for item in news[:NEWS_MAX_ARTICLES]:
            title = item.get("title", "")
            if title:
                titles.append(title)
        return titles
    except Exception:
        return []


def _fetch_finviz_news(ticker: str) -> List[str]:
    """Fallback: get news titles from finviz."""
    try:
        from finvizfinance.quote import finvizfinance
        stock = finvizfinance(ticker)
        news_df = stock.ticker_news()
        if news_df is not None and not news_df.empty:
            return news_df["Title"].head(NEWS_MAX_ARTICLES).tolist()
    except Exception:
        pass
    return []


def collect_news(tickers: list[str]) -> Dict[str, List[str]]:
    """Collect news headlines for each ticker.

    Returns:
        dict mapping ticker → list of headline strings
    """
    result: Dict[str, List[str]] = {}

    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            log.info(f"News: {i + 1}/{len(tickers)}")

        rate_limiter.wait()
        titles = _fetch_yfinance_news(ticker)

        if not titles:
            titles = _fetch_finviz_news(ticker)

        if titles:
            result[ticker] = titles

    log.info(f"News collected for {len(result)}/{len(tickers)} tickers")
    return result
