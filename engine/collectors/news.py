"""Collect recent news headlines for sentiment analysis."""

from __future__ import annotations

from typing import Dict, List, TypedDict

import yfinance as yf

from engine.config import NEWS_MAX_ARTICLES
from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)


class NewsItem(TypedDict):
    title: str
    url: str
    publisher: str
    date: str


def _epoch_to_date(epoch: int | float | None) -> str:
    """Convert Unix epoch to YYYY-MM-DD string."""
    if not epoch:
        return ""
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _fetch_yfinance_news(ticker: str) -> List[NewsItem]:
    """Get news items from yfinance."""
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        items: List[NewsItem] = []
        for item in news[:NEWS_MAX_ARTICLES]:
            title = item.get("title", "")
            if title:
                items.append({
                    "title": title,
                    "url": item.get("link", item.get("url", "")),
                    "publisher": item.get("publisher", ""),
                    "date": _epoch_to_date(item.get("providerPublishTime", item.get("publishedDate"))),
                })
        return items
    except Exception:
        return []


def _fetch_finviz_news(ticker: str) -> List[NewsItem]:
    """Fallback: get news items from finviz."""
    try:
        from finvizfinance.quote import finvizfinance
        stock = finvizfinance(ticker)
        news_df = stock.ticker_news()
        if news_df is not None and not news_df.empty:
            items: List[NewsItem] = []
            for _, row in news_df.head(NEWS_MAX_ARTICLES).iterrows():
                date_val = row.get("Date", "")
                date_str = str(date_val)[:10] if date_val else ""
                items.append({
                    "title": row.get("Title", ""),
                    "url": row.get("Link", ""),
                    "publisher": row.get("Source", ""),
                    "date": date_str,
                })
            return items
    except Exception:
        pass
    return []


def collect_news(tickers: list[str]) -> Dict[str, List[NewsItem]]:
    """Collect news headlines for each ticker.

    Returns:
        dict mapping ticker → list of NewsItem dicts with title, url, publisher
    """
    result: Dict[str, List[NewsItem]] = {}

    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            log.info(f"News: {i + 1}/{len(tickers)}")

        rate_limiter.wait()
        items = _fetch_yfinance_news(ticker)

        if not items:
            items = _fetch_finviz_news(ticker)

        if items:
            result[ticker] = items

    log.info(f"News collected for {len(result)}/{len(tickers)} tickers")
    return result
