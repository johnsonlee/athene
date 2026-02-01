"""Sentiment analysis using VADER on news headlines."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from engine.collectors.news import NewsItem
from engine.utils.logger import get_logger

log = get_logger(__name__)

analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(news: Dict[str, List[NewsItem]]) -> pd.DataFrame:
    """Compute sentiment scores from news headlines.

    Uses VADER compound score averaged across all headlines per ticker.

    Returns:
        DataFrame indexed by ticker with columns:
        sentiment_compound, sentiment_pos, sentiment_neg, sentiment_neu,
        news_count
    """
    records = []

    for ticker, items in news.items():
        if not items:
            continue

        compounds = []
        positives = []
        negatives = []
        neutrals = []

        for item in items:
            title = item["title"] if isinstance(item, dict) else item
            scores = analyzer.polarity_scores(title)
            compounds.append(scores["compound"])
            positives.append(scores["pos"])
            negatives.append(scores["neg"])
            neutrals.append(scores["neu"])

        records.append({
            "ticker": ticker,
            "sentiment_compound": sum(compounds) / len(compounds),
            "sentiment_pos": sum(positives) / len(positives),
            "sentiment_neg": sum(negatives) / len(negatives),
            "sentiment_neu": sum(neutrals) / len(neutrals),
            "news_count": len(items),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("ticker")

    log.info(f"Sentiment analysis complete for {len(df)} tickers")
    return df
