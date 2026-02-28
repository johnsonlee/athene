"""Information Coefficient (IC) tracker for factor model validation.

Computes Spearman rank correlation between factor scores and forward
stock returns.  A positive IC means higher scores predict higher returns.

Usage:
    python -m engine.ic              # compute IC from accumulated history
    python -m engine.ic --horizons 5 21
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

from engine.config import OUTPUT_DIR
from engine.utils.logger import get_logger

log = get_logger(__name__)

FACTORS = [
    "composite_score",
    "earnings_visibility",
    "valuation_margin",
    "catalyst_timeline",
    "downside_control",
    # v7: sub-scores for per-metric IC validation
    "value_score",
    "quality_score",
    "growth_score",
    "safety_score",
    "trend_score",
    "momentum_score",
    "volatility_score",
    "volume_score",
    # v8: analyst revision momentum
    "analyst_score",
    # v16: per-metric scores for IC-weighted averaging
    "pe_score", "forward_pe_score", "pb_score", "ps_score",           # value
    "roe_score", "roa_score", "margin_score",                          # quality
    "rev_growth_score", "earn_growth_score",                           # growth
    "debt_equity_score", "fcf_yield_score", "current_ratio_score",     # safety
    # v17: cyclical risk
    "cyclical_risk_score",
    # v19: market timing penalty (varies per stock due to DC modulation)
    "timing_penalty",
]

DEFAULT_HORIZONS = [5, 21]  # trading days forward


def _load_history() -> dict[str, dict[str, dict[str, Any]]]:
    """Load history.json → {date: {ticker: {scores...}}}."""
    path = os.path.join(OUTPUT_DIR, "history.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_price_series(ticker: str) -> dict[str, float]:
    """Load close prices from stock detail JSON → {date_str: close}."""
    path = os.path.join(OUTPUT_DIR, "stocks", f"{ticker}.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {p["date"]: p["close"] for p in data.get("prices", [])}


def _forward_return(
    prices: dict[str, float], date_str: str, horizon: int
) -> float | None:
    """Compute forward return from date_str looking horizon trading days ahead.

    Returns fractional return (e.g. 0.05 for +5%) or None if data unavailable.
    """
    sorted_dates = sorted(prices.keys())
    try:
        idx = sorted_dates.index(date_str)
    except ValueError:
        # Exact date not in price series — find the nearest date on or after
        candidates = [d for d in sorted_dates if d >= date_str]
        if not candidates:
            return None
        idx = sorted_dates.index(candidates[0])

    target_idx = idx + horizon
    if target_idx >= len(sorted_dates):
        return None

    p0 = prices[sorted_dates[idx]]
    p1 = prices[sorted_dates[target_idx]]
    if not p0 or p0 == 0:
        return None
    return (p1 - p0) / p0


def compute_ic(
    horizons: list[int] | None = None,
) -> dict[str, Any]:
    """Compute IC time series for each factor and horizon.

    Returns:
        {
            "horizons": [5, 21],
            "factors": {
                "composite_score": {
                    "5": {"dates": [...], "ic": [...], "mean": ..., "std": ..., "ir": ..., "hit_rate": ...},
                    "21": { ... }
                },
                ...
            },
            "computed_at": "...",
            "num_dates": ...,
        }
    """
    from scipy.stats import spearmanr

    if horizons is None:
        horizons = DEFAULT_HORIZONS

    history = _load_history()
    dates = sorted(history.keys())

    if len(dates) < 2:
        log.warning(
            f"IC tracker: only {len(dates)} date(s) in history — "
            "need at least 2 for meaningful IC. Exporting skeleton."
        )

    # Collect all tickers across all dates
    all_tickers = set()
    for daily in history.values():
        all_tickers.update(daily.keys())

    # Load price series for all tickers
    log.info(f"IC tracker: loading prices for {len(all_tickers)} tickers...")
    price_cache: dict[str, dict[str, float]] = {}
    for ticker in all_tickers:
        price_cache[ticker] = _load_price_series(ticker)

    result: dict[str, Any] = {
        "horizons": horizons,
        "factors": {},
        "computed_at": datetime.now().isoformat(),
        "num_dates": len(dates),
    }

    for factor in FACTORS:
        factor_result: dict[str, Any] = {}

        for horizon in horizons:
            ic_dates: list[str] = []
            ic_values: list[float] = []

            for date_str in dates:
                daily = history[date_str]
                scores: list[float] = []
                returns: list[float] = []

                for ticker, data in daily.items():
                    score = data.get(factor)
                    if score is None:
                        continue

                    prices = price_cache.get(ticker, {})
                    fwd = _forward_return(prices, date_str, horizon)
                    if fwd is None:
                        continue

                    scores.append(score)
                    returns.append(fwd)

                # Need at least 10 pairs for a meaningful correlation
                if len(scores) < 10:
                    continue

                corr, _pval = spearmanr(scores, returns)
                if corr is not None and not (corr != corr):  # not NaN
                    ic_dates.append(date_str)
                    ic_values.append(round(corr, 4))

            # Summary statistics
            summary: dict[str, Any] = {
                "dates": ic_dates,
                "ic": ic_values,
                "count": len(ic_values),
            }

            if ic_values:
                import statistics

                mean_ic = statistics.mean(ic_values)
                summary["mean"] = round(mean_ic, 4)

                if len(ic_values) >= 2:
                    std_ic = statistics.stdev(ic_values)
                    summary["std"] = round(std_ic, 4)
                    summary["ir"] = (
                        round(mean_ic / std_ic, 4) if std_ic > 0 else None
                    )
                else:
                    summary["std"] = None
                    summary["ir"] = None

                positive = sum(1 for v in ic_values if v > 0)
                summary["hit_rate"] = round(positive / len(ic_values), 4)
            else:
                summary["mean"] = None
                summary["std"] = None
                summary["ir"] = None
                summary["hit_rate"] = None

            factor_result[str(horizon)] = summary

        result["factors"][factor] = factor_result

    return result


def export_ic(ic_data: dict[str, Any] | None = None) -> str:
    """Compute IC and write to ic.json."""
    if ic_data is None:
        ic_data = compute_ic()

    path = os.path.join(OUTPUT_DIR, "ic.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ic_data, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(path) / 1024
    log.info(f"IC tracker: wrote {path} ({size_kb:.1f} KB)")

    # Log summary
    for factor, horizons in ic_data.get("factors", {}).items():
        for h, stats in horizons.items():
            count = stats.get("count", 0)
            mean = stats.get("mean")
            ir = stats.get("ir")
            hit = stats.get("hit_rate")
            log.info(
                f"  {factor} [{h}d]: IC={mean} IR={ir} hit={hit} ({count} obs)"
            )

    return path
