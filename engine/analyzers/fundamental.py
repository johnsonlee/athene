"""Fundamental analysis: value, quality, growth, and safety sub-factors."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from engine.config import (
    FUND_WEIGHT_VALUE,
    FUND_WEIGHT_QUALITY,
    FUND_WEIGHT_GROWTH,
    FUND_WEIGHT_SAFETY,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)


def _safe(val: Any) -> float | None:
    """Convert to float or return None."""
    if val is None:
        return None
    try:
        v = float(val)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def analyze_fundamental(fundamentals: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    """Compute fundamental sub-scores for each ticker.

    Returns:
        DataFrame indexed by ticker with columns:
        value_score, quality_score, growth_score, safety_score,
        fundamental_score, plus raw metric columns
    """
    records = []

    for ticker, data in fundamentals.items():
        pe = _safe(data.get("trailingPE"))
        fwd_pe = _safe(data.get("forwardPE"))
        pb = _safe(data.get("priceToBook"))
        ps = _safe(data.get("priceToSalesTrailing12Months"))
        roe = _safe(data.get("returnOnEquity"))
        roa = _safe(data.get("returnOnAssets"))
        rev_growth = _safe(data.get("revenueGrowth"))
        earn_growth = _safe(data.get("earningsGrowth"))
        debt_equity = _safe(data.get("debtToEquity"))
        fcf = _safe(data.get("freeCashflow"))
        market_cap = _safe(data.get("marketCap"))
        profit_margin = _safe(data.get("profitMargins"))
        op_margin = _safe(data.get("operatingMargins"))
        gross_margin = _safe(data.get("grossMargins"))
        dividend_yield = _safe(data.get("dividendYield"))
        beta = _safe(data.get("beta"))
        current_price = _safe(data.get("currentPrice"))
        high_52w = _safe(data.get("fiftyTwoWeekHigh"))
        low_52w = _safe(data.get("fiftyTwoWeekLow"))

        # Value: inverse PE/PB/PS (lower is better)
        inv_pe = 1.0 / pe if pe and pe > 0 else None
        inv_pb = 1.0 / pb if pb and pb > 0 else None
        inv_ps = 1.0 / ps if ps and ps > 0 else None

        records.append({
            "ticker": ticker,
            "pe": pe,
            "forward_pe": fwd_pe,
            "pb": pb,
            "ps": ps,
            "roe": roe,
            "roa": roa,
            "revenue_growth": rev_growth,
            "earnings_growth": earn_growth,
            "debt_to_equity": debt_equity,
            "fcf": fcf,
            "market_cap": market_cap,
            "profit_margin": profit_margin,
            "operating_margin": op_margin,
            "gross_margin": gross_margin,
            "dividend_yield": dividend_yield,
            "beta": beta,
            "current_price": current_price,
            "high_52w": high_52w,
            "low_52w": low_52w,
            # Derived metrics for scoring
            "inv_pe": inv_pe,
            "inv_pb": inv_pb,
            "inv_ps": inv_ps,
            # FCF yield (FCF / market cap)
            "fcf_yield": fcf / market_cap if fcf and market_cap and market_cap > 0 else None,
        })

    df = pd.DataFrame(records).set_index("ticker")

    # We'll z-score normalize in the normalizer; here just return raw metrics
    log.info(f"Fundamental analysis complete for {len(df)} tickers")
    return df


def compute_fundamental_subscores(df: pd.DataFrame) -> pd.DataFrame:
    """Compute sub-factor scores using absolute metric scoring (0-100).

    Uses piecewise linear breakpoints per metric instead of z-scores.

    Returns:
        DataFrame with value_score, quality_score, growth_score, safety_score,
        fundamental_score columns added (all 0-100).
    """
    from engine.scorer.absolute import (
        score_pe, score_pb, score_ps,
        score_roe, score_roa, score_profit_margin,
        score_revenue_growth, score_earnings_growth,
        score_debt_equity,
    )

    result = df.copy()

    # Value sub-score: avg(pe_score, pb_score, ps_score)
    result["pe_score"] = result["pe"].apply(score_pe) if "pe" in result.columns else 50.0
    result["pb_score"] = result["pb"].apply(score_pb) if "pb" in result.columns else 50.0
    result["ps_score"] = result["ps"].apply(score_ps) if "ps" in result.columns else 50.0
    result["value_score"] = result[["pe_score", "pb_score", "ps_score"]].mean(axis=1)

    # Quality sub-score: avg(roe_score, roa_score, margin_score)
    result["roe_score"] = result["roe"].apply(score_roe) if "roe" in result.columns else 50.0
    result["roa_score"] = result["roa"].apply(score_roa) if "roa" in result.columns else 50.0
    result["margin_score"] = result["profit_margin"].apply(score_profit_margin) if "profit_margin" in result.columns else 50.0
    result["quality_score"] = result[["roe_score", "roa_score", "margin_score"]].mean(axis=1)

    # Growth sub-score: avg(rev_growth_score, earn_growth_score)
    result["rev_growth_score"] = result["revenue_growth"].apply(score_revenue_growth) if "revenue_growth" in result.columns else 50.0
    result["earn_growth_score"] = result["earnings_growth"].apply(score_earnings_growth) if "earnings_growth" in result.columns else 50.0
    result["growth_score"] = result[["rev_growth_score", "earn_growth_score"]].mean(axis=1)

    # Safety sub-score: debt_equity_score
    result["safety_score"] = result["debt_to_equity"].apply(score_debt_equity) if "debt_to_equity" in result.columns else 50.0

    # Composite fundamental score (weighted, already 0-100)
    result["fundamental_score"] = (
        FUND_WEIGHT_VALUE * result["value_score"].fillna(50)
        + FUND_WEIGHT_QUALITY * result["quality_score"].fillna(50)
        + FUND_WEIGHT_GROWTH * result["growth_score"].fillna(50)
        + FUND_WEIGHT_SAFETY * result["safety_score"].fillna(50)
    )

    return result
