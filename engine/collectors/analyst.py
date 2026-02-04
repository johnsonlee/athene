"""Collect analyst recommendation and price-target data via yfinance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, TypedDict

import yfinance as yf

from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)

REVISION_LOOKBACK_DAYS = 90


class AnalystRevision(TypedDict):
    date: str
    firm: str
    to_grade: str
    from_grade: str
    action: str


class AnalystData(TypedDict, total=False):
    recommendation_mean: float | None
    recommendation_key: str | None
    target_mean_price: float | None
    target_median_price: float | None
    target_high_price: float | None
    target_low_price: float | None
    number_of_analysts: int | None
    current_price: float | None
    revisions: List[AnalystRevision]


# Actions that represent upgrades vs downgrades
_UPGRADE_ACTIONS = {"up", "upgrade", "reiterated", "initiated"}
_DOWNGRADE_ACTIONS = {"down", "downgrade"}

# Grade ordinal for computing direction when action is ambiguous
_GRADE_RANK: Dict[str, int] = {
    "strong buy": 5,
    "buy": 4,
    "outperform": 4,
    "overweight": 4,
    "accumulate": 4,
    "market outperform": 4,
    "sector outperform": 4,
    "positive": 4,
    "hold": 3,
    "neutral": 3,
    "equal-weight": 3,
    "market perform": 3,
    "sector perform": 3,
    "in-line": 3,
    "peer perform": 3,
    "mixed": 3,
    "sell": 2,
    "underperform": 2,
    "underweight": 2,
    "reduce": 2,
    "market underperform": 2,
    "sector underperform": 2,
    "negative": 2,
    "strong sell": 1,
}


def _classify_revision(action: str, from_grade: str, to_grade: str) -> str:
    """Classify a revision as 'upgrade', 'downgrade', or 'maintain'."""
    action_lower = action.lower().strip()

    if action_lower in _UPGRADE_ACTIONS:
        return "upgrade"
    if action_lower in _DOWNGRADE_ACTIONS:
        return "downgrade"

    # Fall back to grade comparison
    from_rank = _GRADE_RANK.get(from_grade.lower().strip(), 3)
    to_rank = _GRADE_RANK.get(to_grade.lower().strip(), 3)

    if to_rank > from_rank:
        return "upgrade"
    if to_rank < from_rank:
        return "downgrade"
    return "maintain"


def collect_analyst_data(tickers: list[str]) -> Dict[str, AnalystData]:
    """Fetch analyst recommendation data for each ticker.

    Returns:
        dict mapping ticker -> AnalystData with consensus info and recent revisions.
    """
    result: Dict[str, AnalystData] = {}
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=REVISION_LOOKBACK_DAYS)

    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            log.info(f"Analyst data: {i + 1}/{len(tickers)}")

        rate_limiter.wait()
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            data: AnalystData = {
                "recommendation_mean": info.get("recommendationMean"),
                "recommendation_key": info.get("recommendationKey"),
                "target_mean_price": info.get("targetMeanPrice"),
                "target_median_price": info.get("targetMedianPrice"),
                "target_high_price": info.get("targetHighPrice"),
                "target_low_price": info.get("targetLowPrice"),
                "number_of_analysts": info.get("numberOfAnalystOpinions"),
                "current_price": info.get("currentPrice"),
                "revisions": [],
            }

            # Fetch upgrades/downgrades history
            try:
                ud = t.upgrades_downgrades
                if ud is not None and not ud.empty:
                    revisions: List[AnalystRevision] = []
                    for idx, row in ud.iterrows():
                        # idx is typically a Timestamp
                        if hasattr(idx, "tz_localize"):
                            rev_date = idx if idx.tzinfo else idx.tz_localize("UTC")
                        elif hasattr(idx, "to_pydatetime"):
                            rev_date = idx.to_pydatetime()
                            if rev_date.tzinfo is None:
                                rev_date = rev_date.replace(tzinfo=timezone.utc)
                        else:
                            continue

                        if rev_date < cutoff:
                            continue

                        date_str = rev_date.strftime("%Y-%m-%d") if hasattr(rev_date, "strftime") else str(rev_date)[:10]
                        revisions.append({
                            "date": date_str,
                            "firm": str(row.get("Firm", "")),
                            "to_grade": str(row.get("ToGrade", "")),
                            "from_grade": str(row.get("FromGrade", "")),
                            "action": str(row.get("Action", "")),
                        })
                    data["revisions"] = revisions
            except Exception:
                pass  # upgrades_downgrades not always available

            # Only include if we have at least some analyst data
            has_consensus = data.get("recommendation_mean") is not None
            has_targets = data.get("target_median_price") is not None
            has_revisions = len(data.get("revisions", [])) > 0
            if has_consensus or has_targets or has_revisions:
                result[ticker] = data

        except Exception as e:
            log.warning(f"Failed to fetch analyst data for {ticker}: {e}")

    log.info(f"Analyst data collected for {len(result)}/{len(tickers)} tickers")
    return result
