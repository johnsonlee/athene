"""Collect CFTC Commitments of Traders (COT) data.

Fetches the Traders in Financial Futures (TFF) report from CFTC and
extracts Asset Manager net positioning for key futures contracts
(S&P 500, Gold, Treasuries, Euro FX, Yen).

This is an *optional* data source — the capital flow pipeline
degrades gracefully if CFTC data is unavailable.
"""

from __future__ import annotations

import io
from typing import Any, Dict

import pandas as pd

from engine.config import CFTC_CONTRACT_MAP, CFTC_REPORT_URL
from engine.utils.logger import get_logger

log = get_logger(__name__)


def collect_cftc_cot() -> Dict[str, Any]:
    """Fetch CFTC TFF report and extract asset manager net positioning.

    Returns:
        dict mapping node_id (e.g. "usEquity") -> {
            "net_position": int,         # Asset manager net (long - short)
            "net_change": int,           # Week-over-week change
            "pct_long": float,           # % of OI held long
            "pct_short": float,          # % of OI held short
            "direction": int,            # +1 (net long) / -1 (net short) / 0
        }
        Empty dict if data is unavailable.
    """
    try:
        import requests
    except ImportError:
        log.warning("requests not installed — CFTC data unavailable")
        return {}

    try:
        resp = requests.get(CFTC_REPORT_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        log.warning(f"CFTC data fetch failed: {e}")
        return {}

    try:
        return _parse_tff_report(resp.text)
    except Exception as e:
        log.warning(f"CFTC data parse failed: {e}")
        return {}


def _parse_tff_report(text: str) -> Dict[str, Any]:
    """Parse the Traders in Financial Futures pipe-delimited report.

    The TFF report has columns including:
    - Market_and_Exchange_Names
    - Report_Date_as_YYYY-MM-DD
    - Asset_Mgr_Positions_Long_All
    - Asset_Mgr_Positions_Short_All
    - Change_in_Asset_Mgr_Long_All
    - Change_in_Asset_Mgr_Short_All
    - Pct_of_OI_Asset_Mgr_Long_All
    - Pct_of_OI_Asset_Mgr_Short_All
    """
    # Try to parse as CSV (comma-delimited) — TFF format varies
    try:
        df = pd.read_csv(io.StringIO(text), low_memory=False)
    except Exception:
        log.warning("CFTC: Failed to parse as CSV")
        return {}

    if df.empty:
        return {}

    # Normalize column names (strip whitespace)
    df.columns = df.columns.str.strip()

    # Identify the market name column
    name_col = None
    for candidate in ["Market_and_Exchange_Names", "Market and Exchange Names"]:
        if candidate in df.columns:
            name_col = candidate
            break
    if name_col is None:
        log.warning(f"CFTC: market name column not found. Columns: {list(df.columns)[:10]}")
        return {}

    result: Dict[str, Any] = {}

    for contract_keyword, node_id in CFTC_CONTRACT_MAP.items():
        # Find rows matching this contract
        mask = df[name_col].str.contains(contract_keyword, case=False, na=False)
        matched = df[mask]
        if matched.empty:
            continue

        # Use the most recent report date
        date_col = None
        for c in ["Report_Date_as_YYYY-MM-DD", "As_of_Date_In_Form_YYMMDD"]:
            if c in matched.columns:
                date_col = c
                break

        if date_col:
            matched = matched.sort_values(date_col, ascending=False)

        row = matched.iloc[0]

        # Extract asset manager positioning
        long_pos = _safe_int(row, "Asset_Mgr_Positions_Long_All",
                             "Dealer_Positions_Long_All")
        short_pos = _safe_int(row, "Asset_Mgr_Positions_Short_All",
                              "Dealer_Positions_Short_All")
        long_chg = _safe_int(row, "Change_in_Asset_Mgr_Long_All",
                             "Change_in_Dealer_Long_All")
        short_chg = _safe_int(row, "Change_in_Asset_Mgr_Short_All",
                              "Change_in_Dealer_Short_All")
        pct_long = _safe_float(row, "Pct_of_OI_Asset_Mgr_Long_All",
                               "Pct_of_OI_Dealer_Long_All")
        pct_short = _safe_float(row, "Pct_of_OI_Asset_Mgr_Short_All",
                                "Pct_of_OI_Dealer_Short_All")

        net_position = long_pos - short_pos
        net_change = long_chg - short_chg
        direction = 1 if net_position > 0 else (-1 if net_position < 0 else 0)

        result[node_id] = {
            "net_position": net_position,
            "net_change": net_change,
            "pct_long": pct_long,
            "pct_short": pct_short,
            "direction": direction,
        }

    log.info(f"CFTC COT data: {len(result)}/{len(CFTC_CONTRACT_MAP)} contracts parsed")
    return result


def _safe_int(row: pd.Series, *col_names: str) -> int:
    """Extract an integer from the first matching column name."""
    for col in col_names:
        if col in row.index:
            try:
                return int(row[col])
            except (ValueError, TypeError):
                pass
    return 0


def _safe_float(row: pd.Series, *col_names: str) -> float:
    """Extract a float from the first matching column name."""
    for col in col_names:
        if col in row.index:
            try:
                return float(row[col])
            except (ValueError, TypeError):
                pass
    return 0.0
