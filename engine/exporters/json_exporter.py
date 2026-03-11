"""Export analysis results to JSON files for the frontend."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd

from engine.config import OUTPUT_DIR
from engine.utils.logger import get_logger

log = get_logger(__name__)


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)


def _clean_record(record: dict) -> dict:
    """Replace NaN/Inf with None for JSON serialization."""
    cleaned = {}
    for k, v in record.items():
        if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def _write_json(data: Any, filename: str) -> str:
    """Write data to a JSON file under OUTPUT_DIR."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(path) / 1024
    log.info(f"Wrote {path} ({size_kb:.1f} KB)")
    return path


def export_meta(ticker_count: int, run_date: str | None = None, macro: dict | None = None, timing: "Any | None" = None) -> str:
    """Export meta.json with run metadata.

    Args:
        macro: Optional macro regime info dict from detect_regime().
        timing: Optional TimingResult from compute_market_timing().
    """
    from engine.utils.market_calendar import us_market_date, us_market_now
    data: Dict[str, Any] = {
        "date": run_date or us_market_date(),
        "timestamp": us_market_now().isoformat(),
        "version": "1.0.0",
        "ticker_count": ticker_count,
    }
    if macro:
        data["macro"] = macro
    if timing is not None:
        data["timing"] = {
            "market_timing_score": timing.market_timing_score,
            "timing_zone": timing.timing_zone,
            "composite_penalty": timing.composite_penalty,
            "signal_contributions": timing.signal_contributions,
            "raw_signals": timing.raw_signals,
            "weight_adjustments": timing.weight_adjustments,
        }
    return _write_json(data, "meta.json")


def export_rankings(ranked: pd.DataFrame, universe: pd.DataFrame) -> str:
    """Export rankings.json - the main screener data file."""
    # Merge universe info (name, sector) with rankings
    if "name" not in ranked.columns and not universe.empty:
        info = universe.set_index("ticker")[["name", "sector", "industry"]]
        merged = ranked.join(info, how="left")
    else:
        merged = ranked

    records = []
    for ticker, row in merged.iterrows():
        rec = _clean_record(row.to_dict())
        rec["ticker"] = ticker
        records.append(rec)

    return _write_json(records, "rankings.json")


def export_history(ranked: pd.DataFrame, run_date: str | None = None) -> str:
    """Append today's snapshot to history.json.

    Each day's entry is keyed by date, containing per-ticker
    composite_score, tier, rank, and percentile.
    """
    from engine.utils.market_calendar import us_market_date
    run_date = run_date or us_market_date()

    history_path = os.path.join(OUTPUT_DIR, "history.json")
    history: dict = {}
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = {}

    daily: dict = {}
    for ticker, row in ranked.iterrows():
        entry: dict = {
            "composite_score": float(row.get("composite_score", 0)),
            "tier": str(row.get("tier", "")),
            "rank": int(row.get("rank", 0)),
            "percentile": float(row.get("percentile", 0)),
        }
        # Store dimension scores for change attribution (v3 4-dimension model)
        # v7: also store sub-scores for per-metric IC validation
        # v8: added analyst_score
        for key in ("earnings_visibility", "valuation_margin",
                     "catalyst_timeline", "downside_control",
                     "fundamental_score", "technical_score", "sentiment_score",
                     # v7: sub-scores for IC tracking
                     "value_score", "quality_score", "growth_score", "safety_score",
                     "trend_score", "momentum_score", "volatility_score", "volume_score",
                     # v8: analyst revision momentum
                     "analyst_score",
                     "data_completeness",
                     # v16: per-metric scores for IC tracking
                     "pe_score", "forward_pe_score", "pb_score", "ps_score",
                     "roe_score", "roa_score", "margin_score",
                     "rev_growth_score", "earn_growth_score",
                     "debt_equity_score", "fcf_yield_score", "current_ratio_score",
                     # v19: market timing
                     "market_timing_score", "timing_penalty",
                     # v20: alpha model scores
                     "alpha_score",
                     "alpha_vm", "alpha_ev", "alpha_timing",
                     "alpha_visibility", "alpha_multiplier"):
            val = row.get(key)
            if val is not None and pd.notna(val):
                entry[key] = round(float(val), 2)
        daily[str(ticker)] = entry

    history[run_date] = daily
    log.info(f"History: added {len(daily)} tickers for {run_date} ({len(history)} total days)")
    return _write_json(history, "history.json")


_PROFILE_KEYS = [
    "longBusinessSummary",
    "fullTimeEmployees",
    "website",
    "city",
    "country",
]


def _extract_profile(fundamental: dict | None) -> dict | None:
    """Extract company profile fields from fundamental data."""
    if not fundamental:
        return None
    profile = {k: fundamental.get(k) for k in _PROFILE_KEYS if fundamental.get(k) is not None}
    return profile if profile else None


def export_stock_detail(
    ticker: str,
    prices: pd.DataFrame,
    fundamental: dict | None,
    technical: dict | None,
    sentiment: dict | None,
    ranking: dict | None,
    headlines: list | None = None,
    analyst: dict | None = None,
) -> str:
    """Export individual stock JSON to stocks/{ticker}.json."""
    stocks_dir = os.path.join(OUTPUT_DIR, "stocks")
    os.makedirs(stocks_dir, exist_ok=True)

    # Convert price history to list of records
    price_records = []
    if prices is not None and not prices.empty:
        for date, row in prices.iterrows():
            rec = {
                "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
                "open": float(row.get("Open", 0)),
                "high": float(row.get("High", 0)),
                "low": float(row.get("Low", 0)),
                "close": float(row.get("Close", 0)),
                "volume": int(row.get("Volume", 0)),
            }
            price_records.append(rec)

    data = {
        "ticker": ticker,
        "profile": _extract_profile(fundamental),
        "prices": price_records,
        "fundamental": _clean_record(fundamental) if fundamental else None,
        "technical": _clean_record(technical) if technical else None,
        "sentiment": _clean_record(sentiment) if sentiment else None,
        "analyst": _clean_record(analyst) if analyst else None,
        "ranking": _clean_record(ranking) if ranking else None,
        "headlines": headlines or [],
    }

    path = os.path.join(stocks_dir, f"{ticker}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
    return path
