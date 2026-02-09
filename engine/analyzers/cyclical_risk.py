"""Cyclical risk analysis for commodity and cyclical-sector stocks.

Computes a cyclical_risk_score (0-100) measuring where a stock sits in its
earnings cycle.  Higher score = safer position (trough or stable), lower
score = riskier position (near cycle peak).

Two signals are combined:

1. **Earnings direction** (60%): ``forward_pe / trailing_pe`` ratio.
   - Ratio > 1.2 means the market expects earnings to DECLINE (forward PE
     higher than trailing → cycle peak territory).
   - Ratio < 0.8 means earnings expected to IMPROVE (cycle trough).
   - Uses data already collected (trailingPE, forwardPE) — no new collection.

2. **Margin level** (40%): current operating margin vs sector reference range.
   - For cyclical sectors, unusually high margins signal peak cycle.
   - Scored relative to sector-specific reference midpoint.

Non-cyclical sectors receive a neutral score (50).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine.config import CYCLICAL_SECTORS, CYCLICAL_MARGIN_REFS
from engine.scorer.absolute import metric_score, Breakpoints
from engine.utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Breakpoints for cyclical risk scoring
# ---------------------------------------------------------------------------

# Earnings direction: forward_pe / trailing_pe ratio
# > 1 means market expects earnings decline (PE expansion) → riskier
# < 1 means market expects earnings growth (PE compression) → safer
_EARNINGS_DIRECTION_BREAKPOINTS: Breakpoints = [
    (0.5, 90),   # strong earnings improvement expected → very safe
    (0.7, 78),
    (0.85, 65),
    (1.0, 50),   # neutral — stable earnings
    (1.15, 38),
    (1.3, 25),
    (1.6, 12),   # severe earnings decline expected → peak cycle risk
]

# Margin deviation: (current_margin - sector_midpoint) / sector_midpoint
# Positive = above normal → likely at cycle peak → riskier
# Negative = below normal → likely at cycle trough → safer
_MARGIN_DEVIATION_BREAKPOINTS: Breakpoints = [
    (-0.6, 85),  # margin well below sector norm → cycle trough
    (-0.3, 72),
    (-0.1, 60),
    (0.0, 50),   # at sector norm
    (0.2, 38),
    (0.5, 25),
    (1.0, 12),   # margin far above norm → extreme peak
]


def compute_cyclical_risk(
    fund_df: pd.DataFrame,
    sectors: pd.Series | None = None,
) -> pd.Series:
    """Compute cyclical risk score for each ticker.

    Args:
        fund_df: DataFrame from ``analyze_fundamental()`` with columns
            ``pe``, ``forward_pe``, ``operating_margin``.
        sectors: Series mapping ticker → sector name.

    Returns:
        Series indexed by ticker with cyclical_risk_score (0-100).
        Higher = safer (trough / stable), lower = riskier (peak).
    """
    scores = pd.Series(50.0, index=fund_df.index, name="cyclical_risk_score")

    if sectors is None:
        log.info("No sector data — all tickers get neutral cyclical risk (50)")
        return scores

    sector_map = sectors.to_dict() if isinstance(sectors, pd.Series) else sectors
    n_scored = 0

    for ticker in fund_df.index:
        sector = sector_map.get(ticker)
        if sector is None or sector not in CYCLICAL_SECTORS:
            continue  # non-cyclical → stays at 50

        pe = fund_df.at[ticker, "pe"] if "pe" in fund_df.columns else None
        fwd_pe = fund_df.at[ticker, "forward_pe"] if "forward_pe" in fund_df.columns else None
        op_margin = fund_df.at[ticker, "operating_margin"] if "operating_margin" in fund_df.columns else None

        # Signal 1: Earnings direction (forward_pe / trailing_pe)
        earnings_dir_score = 50.0
        if (
            pe is not None
            and fwd_pe is not None
            and not np.isnan(pe)
            and not np.isnan(fwd_pe)
            and pe > 0
            and fwd_pe > 0
        ):
            ratio = fwd_pe / pe
            earnings_dir_score = metric_score(ratio, _EARNINGS_DIRECTION_BREAKPOINTS)

        # Signal 2: Margin level vs sector reference
        margin_dev_score = 50.0
        ref = CYCLICAL_MARGIN_REFS.get(sector)
        if (
            ref is not None
            and op_margin is not None
            and not np.isnan(op_margin)
            and ref > 0
        ):
            deviation = (op_margin - ref) / ref
            margin_dev_score = metric_score(deviation, _MARGIN_DEVIATION_BREAKPOINTS)

        # Weighted combination
        combined = 0.60 * earnings_dir_score + 0.40 * margin_dev_score
        scores.at[ticker] = combined
        n_scored += 1

    if n_scored:
        scored_vals = scores[scores != 50.0]
        log.info(
            f"Cyclical risk scored for {n_scored} tickers "
            f"(mean={scored_vals.mean():.1f}, "
            f"min={scored_vals.min():.1f}, max={scored_vals.max():.1f})"
        )
    else:
        log.info("No cyclical-sector tickers found — all scores neutral (50)")

    return scores
