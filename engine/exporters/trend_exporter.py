"""Export sector trend data to JSON files for the frontend."""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np
import pandas as pd

from engine.config import OUTPUT_DIR
from engine.exporters.json_exporter import NumpyEncoder
from engine.utils.logger import get_logger

log = get_logger(__name__)


def _write_json(data: Any, filename: str) -> str:
    """Write data to a JSON file under OUTPUT_DIR."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(path) / 1024
    log.info(f"Wrote {path} ({size_kb:.1f} KB)")
    return path


def _safe_float(val: Any) -> Any:
    """Convert to float, replacing NaN/Inf with None."""
    if val is None:
        return None
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 2)
    except (TypeError, ValueError):
        return val


def export_trends(
    trend_scored: pd.DataFrame,
    regime_info: dict,
    run_date: str,
    computed_history: dict | None = None,
) -> None:
    """Export trends.json and trend_history.json.

    Args:
        trend_scored: DataFrame indexed by sector name with trend signals + scores.
        regime_info: Market regime dict from detect_regime().
        run_date: Date string (YYYY-MM-DD).
        computed_history: Historical RS/momentum from compute_trend_history().
            If provided, used as the base for trend_history.json (current day merged on top).
    """
    sectors = []
    for sector_name, row in trend_scored.iterrows():
        entry = {
            "sector": str(sector_name),
            "etf": str(row.get("etf_ticker", "")),
            "trend_strength": _safe_float(row.get("trend_strength")),
            "trend_state": str(row.get("trend_state", "neutral")),
            "primary_signal": str(row.get("primary_signal", "")),
            "signals": {
                "relative_strength": {
                    "score": _safe_float(row.get("relative_strength_score")),
                    "rs_1m": _safe_float(row.get("rs_1m")),
                    "rs_3m": _safe_float(row.get("rs_3m")),
                    "rs_6m": _safe_float(row.get("rs_6m")),
                },
                "breadth": {
                    "score": _safe_float(row.get("breadth_score")),
                    "pct_above_sma50": _safe_float(row.get("breadth_sma50")),
                    "pct_above_sma200": _safe_float(row.get("breadth_sma200")),
                },
                "analyst_revisions": {
                    "score": _safe_float(row.get("analyst_revision_score")),
                    "upgrades": int(row.get("analyst_upgrades", 0)),
                    "downgrades": int(row.get("analyst_downgrades", 0)),
                },
                "momentum": {
                    "score": _safe_float(row.get("momentum_score")),
                    "rsi": _safe_float(row.get("etf_rsi")),
                },
                "volume": {
                    "score": _safe_float(row.get("volume_score")),
                    "volume_ratio": _safe_float(row.get("volume_ratio")),
                },
            },
            "etf_close": _safe_float(row.get("etf_close")),
            "stock_count": int(row.get("stock_count", 0)),
        }
        sectors.append(entry)

    # Sort by trend_strength descending
    sectors.sort(key=lambda s: s.get("trend_strength") or 0, reverse=True)

    trends_data = {
        "date": run_date,
        "regime": regime_info,
        "sectors": sectors,
    }
    _write_json(trends_data, "trends.json")

    # --- Build trend_history.json ---
    # Start from computed historical data if available, otherwise load existing
    if computed_history:
        history: dict = dict(computed_history)
    else:
        history_path = os.path.join(OUTPUT_DIR, "trend_history.json")
        history = {}
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, Exception):
                history = {}

    # Merge current day with full signal data (overwrites computed entry for today)
    daily: dict = {}
    for sector_name, row in trend_scored.iterrows():
        daily[str(sector_name)] = {
            "trend_strength": _safe_float(row.get("trend_strength")),
            "trend_state": str(row.get("trend_state", "neutral")),
            "rs_score": _safe_float(row.get("relative_strength_score")),
            "momentum_score": _safe_float(row.get("momentum_score")),
        }

    history[run_date] = daily
    log.info(f"Trend history: {len(history)} total dates, {len(daily)} sectors for {run_date}")
    _write_json(history, "trend_history.json")
