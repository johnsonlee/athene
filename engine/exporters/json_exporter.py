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
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False, indent=None, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    log.info(f"Wrote {path} ({size_kb:.1f} KB)")
    return path


def export_meta(ticker_count: int, run_date: str | None = None) -> str:
    """Export meta.json with run metadata."""
    data = {
        "date": run_date or datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "ticker_count": ticker_count,
    }
    return _write_json(data, "meta.json")


def export_universe(universe: pd.DataFrame) -> str:
    """Export universe.json with ticker list."""
    records = universe.to_dict(orient="records")
    return _write_json(records, "universe.json")


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


def export_fundamentals(fundamental_df: pd.DataFrame) -> str:
    """Export fundamentals.json with detailed fundamental metrics."""
    records = []
    for ticker, row in fundamental_df.iterrows():
        rec = _clean_record(row.to_dict())
        rec["ticker"] = ticker
        records.append(rec)
    return _write_json(records, "fundamentals.json")


def export_technicals(technical_df: pd.DataFrame) -> str:
    """Export technicals.json with detailed technical indicators."""
    records = []
    for ticker, row in technical_df.iterrows():
        rec = _clean_record(row.to_dict())
        rec["ticker"] = ticker
        records.append(rec)
    return _write_json(records, "technicals.json")


def export_sentiment(sentiment_df: pd.DataFrame) -> str:
    """Export sentiment.json with sentiment data."""
    records = []
    for ticker, row in sentiment_df.iterrows():
        rec = _clean_record(row.to_dict())
        rec["ticker"] = ticker
        records.append(rec)
    return _write_json(records, "sentiment.json")


def export_history(ranked: pd.DataFrame, run_date: str | None = None) -> str:
    """Append today's snapshot to history.json.

    Each day's entry is keyed by date, containing per-ticker
    composite_score, tier, rank, and percentile.
    """
    run_date = run_date or datetime.now().strftime("%Y-%m-%d")

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
        daily[str(ticker)] = {
            "composite_score": float(row.get("composite_score", 0)),
            "tier": str(row.get("tier", "")),
            "rank": int(row.get("rank", 0)),
            "percentile": float(row.get("percentile", 0)),
        }

    history[run_date] = daily
    log.info(f"History: added {len(daily)} tickers for {run_date} ({len(history)} total days)")
    return _write_json(history, "history.json")


def export_stock_detail(
    ticker: str,
    prices: pd.DataFrame,
    fundamental: dict | None,
    technical: dict | None,
    sentiment: dict | None,
    ranking: dict | None,
    headlines: list | None = None,
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
        "prices": price_records,
        "fundamental": _clean_record(fundamental) if fundamental else None,
        "technical": _clean_record(technical) if technical else None,
        "sentiment": _clean_record(sentiment) if sentiment else None,
        "ranking": _clean_record(ranking) if ranking else None,
        "headlines": headlines or [],
    }

    path = os.path.join(stocks_dir, f"{ticker}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False, indent=None, separators=(",", ":"))
    return path
