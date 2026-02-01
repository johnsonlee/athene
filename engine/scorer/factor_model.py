"""Multi-factor weighted composite scoring model."""

from __future__ import annotations

import pandas as pd

from engine.config import WEIGHT_FUNDAMENTAL, WEIGHT_TECHNICAL, WEIGHT_SENTIMENT
from engine.utils.logger import get_logger

log = get_logger(__name__)


def compute_composite(
    fundamental_scores: pd.DataFrame,
    technical_scores: pd.DataFrame,
    sentiment_scores: pd.DataFrame,
) -> pd.DataFrame:
    """Merge factor scores and compute weighted composite.

    Handles missing data by redistributing weights:
    - If a ticker has no fundamental score → redistribute to tech + sentiment
    - If no sentiment score → redistribute to fundamental + tech

    Returns:
        DataFrame indexed by ticker with:
        fundamental_score, technical_score, sentiment_score,
        composite_score, and weight columns
    """
    # Ensure we have score columns
    fund = fundamental_scores[["fundamental_score"]].copy() if "fundamental_score" in fundamental_scores.columns else pd.DataFrame()
    tech = technical_scores[["technical_score"]].copy() if "technical_score" in technical_scores.columns else pd.DataFrame()
    sent = sentiment_scores[["sentiment_score"]].copy() if "sentiment_score" in sentiment_scores.columns else pd.DataFrame()

    # Rename sentiment_compound to sentiment_score if needed
    if sent.empty and "sentiment_compound_z" in sentiment_scores.columns:
        sent = sentiment_scores[["sentiment_compound_z"]].rename(columns={"sentiment_compound_z": "sentiment_score"})
    elif sent.empty and "sentiment_compound" in sentiment_scores.columns:
        sent = sentiment_scores[["sentiment_compound"]].rename(columns={"sentiment_compound": "sentiment_score"})

    # Get all tickers
    all_tickers = set()
    for df in [fund, tech, sent]:
        if not df.empty:
            all_tickers.update(df.index)

    all_tickers = sorted(all_tickers)
    result = pd.DataFrame(index=all_tickers)
    result.index.name = "ticker"

    # Join scores
    if not fund.empty:
        result = result.join(fund, how="left")
    else:
        result["fundamental_score"] = float("nan")

    if not tech.empty:
        result = result.join(tech, how="left")
    else:
        result["technical_score"] = float("nan")

    if not sent.empty:
        result = result.join(sent, how="left")
    else:
        result["sentiment_score"] = float("nan")

    # Compute composite with dynamic weight redistribution
    composites = []
    w_fund_list, w_tech_list, w_sent_list = [], [], []

    for _, row in result.iterrows():
        has_fund = pd.notna(row.get("fundamental_score"))
        has_tech = pd.notna(row.get("technical_score"))
        has_sent = pd.notna(row.get("sentiment_score"))

        w_fund = WEIGHT_FUNDAMENTAL if has_fund else 0.0
        w_tech = WEIGHT_TECHNICAL if has_tech else 0.0
        w_sent = WEIGHT_SENTIMENT if has_sent else 0.0

        total_weight = w_fund + w_tech + w_sent

        if total_weight == 0:
            composites.append(0.0)
            w_fund_list.append(0.0)
            w_tech_list.append(0.0)
            w_sent_list.append(0.0)
            continue

        # Normalize weights
        w_fund /= total_weight
        w_tech /= total_weight
        w_sent /= total_weight

        score = (
            w_fund * (row.get("fundamental_score", 0) or 0)
            + w_tech * (row.get("technical_score", 0) or 0)
            + w_sent * (row.get("sentiment_score", 0) or 0)
        )
        composites.append(score)
        w_fund_list.append(w_fund)
        w_tech_list.append(w_tech)
        w_sent_list.append(w_sent)

    result["composite_score"] = composites
    result["weight_fundamental"] = w_fund_list
    result["weight_technical"] = w_tech_list
    result["weight_sentiment"] = w_sent_list

    log.info(f"Composite scores computed for {len(result)} tickers")
    return result
