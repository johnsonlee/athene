"""Analyst revision momentum analysis.

Computes a composite analyst_score from three sub-metrics:

    revision_momentum  (40%)  — net upgrade/downgrade ratio over last 90 days
    target_upside      (35%)  — median target price vs current price
    consensus_rating   (25%)  — sell-side consensus recommendation (1-5 scale)

This captures institutional-quality signals that VADER news sentiment misses:
analyst rating changes, price target revisions, and consensus shifts.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from engine.collectors.analyst import AnalystData, _classify_revision
from engine.utils.logger import get_logger

log = get_logger(__name__)


def analyze_analyst(analyst_data: Dict[str, AnalystData]) -> pd.DataFrame:
    """Compute analyst revision momentum scores.

    Returns:
        DataFrame indexed by ticker with columns:
        revision_momentum, target_upside, consensus_rating,
        analyst_score, analyst_revision_count, analyst_count
    """
    records = []

    for ticker, data in analyst_data.items():
        revisions = data.get("revisions", [])
        rec_mean = data.get("recommendation_mean")
        target_median = data.get("target_median_price")
        target_mean = data.get("target_mean_price")
        current_price = data.get("current_price")
        num_analysts = data.get("number_of_analysts")

        # --- Revision momentum: (upgrades - downgrades) / total ---
        upgrades = 0
        downgrades = 0
        maintains = 0
        for rev in revisions:
            classification = _classify_revision(
                rev.get("action", ""),
                rev.get("from_grade", ""),
                rev.get("to_grade", ""),
            )
            if classification == "upgrade":
                upgrades += 1
            elif classification == "downgrade":
                downgrades += 1
            else:
                maintains += 1

        total_revisions = upgrades + downgrades + maintains
        if total_revisions > 0:
            # Range: -1 (all downgrades) to +1 (all upgrades)
            revision_momentum = (upgrades - downgrades) / total_revisions
        else:
            revision_momentum = None

        # --- Target price upside: (target - current) / current ---
        target_price = target_median or target_mean
        if target_price and current_price and current_price > 0:
            target_upside = (target_price - current_price) / current_price
        else:
            target_upside = None

        # --- Consensus rating: 1 (Strong Buy) to 5 (Strong Sell) ---
        # We'll pass the raw value; scoring inverts in absolute.py
        consensus_rating = rec_mean

        records.append({
            "ticker": ticker,
            "revision_momentum": revision_momentum,
            "target_upside": target_upside,
            "consensus_rating": consensus_rating,
            "analyst_revision_count": total_revisions,
            "analyst_count": num_analysts,
            "analyst_upgrades": upgrades,
            "analyst_downgrades": downgrades,
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("ticker")

    log.info(f"Analyst analysis complete for {len(df)} tickers")
    return df


def compute_analyst_subscores(df: pd.DataFrame) -> pd.DataFrame:
    """Score analyst metrics using absolute breakpoints.

    Returns:
        DataFrame with revision_momentum_score, target_upside_score,
        consensus_score, analyst_score columns added.
    """
    from engine.scorer.absolute import (
        score_revision_momentum,
        score_target_upside,
        score_consensus_rating,
    )

    result = df.copy()

    result["revision_momentum_score"] = (
        result["revision_momentum"].apply(score_revision_momentum)
        if "revision_momentum" in result.columns
        else 50.0
    )
    result["target_upside_score"] = (
        result["target_upside"].apply(score_target_upside)
        if "target_upside" in result.columns
        else 50.0
    )
    result["consensus_score"] = (
        result["consensus_rating"].apply(score_consensus_rating)
        if "consensus_rating" in result.columns
        else 50.0
    )

    # Composite analyst score: weighted average
    # Revision momentum 40% + Target upside 35% + Consensus 25%
    result["analyst_score"] = (
        0.40 * result["revision_momentum_score"]
        + 0.35 * result["target_upside_score"]
        + 0.25 * result["consensus_score"]
    )

    log.info(f"Analyst sub-scores computed for {len(result)} tickers")
    return result
