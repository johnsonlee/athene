"""Sentiment analysis on news headlines.

v9 enhancements:
- Time decay: exponential decay (half-life 7 days) weights recent headlines higher
- Source credibility: major financial news sources weighted 1.5x
- Headline count normalization: sentiment_confidence (0-1) measures coverage depth;
  low-coverage scores are pulled toward neutral
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from engine.collectors.news import NewsItem
from engine.config import SENTIMENT_HALF_LIFE_DAYS, SENTIMENT_CONFIDENCE_N
from engine.utils.logger import get_logger

log = get_logger(__name__)

analyzer = SentimentIntensityAnalyzer()

_DECAY_LAMBDA = math.log(2) / SENTIMENT_HALF_LIFE_DAYS

# ---------------------------------------------------------------------------
# Source credibility tiers
# ---------------------------------------------------------------------------
# Tier 1: major wire services and institutional financial outlets
_TIER1_KEYWORDS = {
    "reuters", "bloomberg", "wsj", "wall street journal",
    "financial times", "ft.com", "cnbc", "ap news", "associated press",
    "barron", "marketwatch", "investor's business daily",
}
_TIER1_WEIGHT = 1.5

# Tier 3: aggregator / opinion-oriented sources
_TIER3_KEYWORDS = {
    "benzinga", "seekingalpha", "seeking alpha", "motley fool",
    "investorplace", "investor place", "24/7 wall st", "247wallst",
}
_TIER3_WEIGHT = 0.7

_DEFAULT_WEIGHT = 1.0


def _source_weight(publisher: str) -> float:
    """Return credibility weight for a publisher."""
    name = publisher.lower().strip()
    if any(kw in name for kw in _TIER1_KEYWORDS):
        return _TIER1_WEIGHT
    if any(kw in name for kw in _TIER3_KEYWORDS):
        return _TIER3_WEIGHT
    return _DEFAULT_WEIGHT


def _days_old(date_str: str, now: datetime) -> float:
    """Compute age in days from a YYYY-MM-DD date string."""
    if not date_str:
        return 7.0  # unknown date -> assume moderately old
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        delta = (now - dt).total_seconds() / 86400
        return max(0.0, delta)
    except (ValueError, TypeError):
        return 7.0


def _time_weight(days: float) -> float:
    """Exponential decay weight: w = exp(-lambda * days)."""
    return math.exp(-_DECAY_LAMBDA * days)


def annotate_headlines(headlines: List[NewsItem]) -> List[dict]:
    """Add per-headline sentiment signal using VADER.

    Returns a new list of headline dicts, each with an added ``sentiment``
    field: ``"positive"``, ``"negative"``, or ``"neutral"``.
    """
    annotated = []
    for item in headlines:
        rec = dict(item) if isinstance(item, dict) else {"title": item}
        title = rec.get("title", "")
        compound = analyzer.polarity_scores(title)["compound"]
        if compound >= 0.05:
            rec["sentiment"] = "positive"
        elif compound <= -0.05:
            rec["sentiment"] = "negative"
        else:
            rec["sentiment"] = "neutral"
        annotated.append(rec)
    return annotated


def analyze_sentiment(news: Dict[str, List[NewsItem]]) -> pd.DataFrame:
    """Compute sentiment scores from news headlines.

    v9: Uses time-decayed, source-weighted average of VADER compound scores.
    Applies confidence normalization to pull low-coverage scores toward neutral.

    Returns:
        DataFrame indexed by ticker with columns:
        sentiment_compound, sentiment_pos, sentiment_neg, sentiment_neu,
        news_count, sentiment_score, sentiment_confidence
    """
    records = []
    now = datetime.now(tz=timezone.utc)

    for ticker, items in news.items():
        if not items:
            continue

        weighted_compounds = []
        weights = []
        positives = []
        negatives = []
        neutrals = []

        for item in items:
            title = item["title"] if isinstance(item, dict) else item
            publisher = item.get("publisher", "") if isinstance(item, dict) else ""
            date_str = item.get("date", "") if isinstance(item, dict) else ""

            scores = analyzer.polarity_scores(title)
            compound = scores["compound"]

            # Combined weight = time_decay * source_credibility
            days = _days_old(date_str, now)
            tw = _time_weight(days)
            sw = _source_weight(publisher)
            w = tw * sw

            weighted_compounds.append(compound * w)
            weights.append(w)
            positives.append(scores["pos"])
            negatives.append(scores["neg"])
            neutrals.append(scores["neu"])

        total_weight = sum(weights)
        if total_weight > 0:
            compound_avg = sum(weighted_compounds) / total_weight
        else:
            compound_avg = 0.0

        # Raw sentiment score (0-100)
        raw_score = max(0.0, min(100.0, (compound_avg + 1.0) * 50.0))

        # Confidence normalization: pull toward neutral when coverage is thin
        news_count = len(items)
        confidence = min(1.0, news_count / SENTIMENT_CONFIDENCE_N)
        sentiment_score = 50.0 + confidence * (raw_score - 50.0)

        records.append({
            "ticker": ticker,
            "sentiment_compound": compound_avg,
            "sentiment_pos": sum(positives) / len(positives),
            "sentiment_neg": sum(negatives) / len(negatives),
            "sentiment_neu": sum(neutrals) / len(neutrals),
            "news_count": news_count,
            "sentiment_confidence": round(confidence, 3),
            "sentiment_score": round(sentiment_score, 2),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("ticker")

    log.info(f"Sentiment analysis complete for {len(df)} tickers "
             f"(time-decayed, source-weighted, confidence-normalized)")
    return df
