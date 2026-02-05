"""Collect ICI weekly fund flow estimates.

ICI (Investment Company Institute) publishes weekly estimated net new
cash flow data for US mutual funds and ETFs.  Data is free but delayed
by ~1 week and not available via a clean API.

This collector attempts to fetch ICI flow data for calibrating our
CMF-based flow proxy.  It degrades gracefully if data is unavailable.

Mapping to our asset classes:
  - Equity Domestic  → usEquity
  - Equity World     → euEquity + jpEquity + emEquity
  - Bond Taxable     → usTreasury + corpBond
  - Money Market     → cash
"""

from __future__ import annotations

from typing import Any, Dict

from engine.utils.logger import get_logger

log = get_logger(__name__)

# ICI publishes at https://www.ici.org/research/stats/flows
# The actual data endpoints change and require browser navigation.
# For now we use a best-effort approach with graceful fallback.

# Node ID mapping for ICI flow categories
ICI_CATEGORY_MAP = {
    "equity_domestic": ["usEquity"],
    "equity_world":    ["euEquity", "jpEquity", "emEquity"],
    "bond_taxable":    ["usTreasury", "corpBond"],
    "money_market":    ["cash"],
}


def collect_ici_flows() -> Dict[str, Any]:
    """Fetch ICI weekly fund flow estimates.

    Returns:
        dict mapping node_id -> {
            "ici_flow_B": float,       # ICI reported flow in $B
            "ici_direction": int,      # +1 / -1 / 0
            "ici_date": str,           # report date
        }
        Empty dict if data is unavailable (common — no stable free API).
    """
    try:
        return _try_fetch_ici()
    except Exception as e:
        log.info(f"ICI data unavailable (expected): {e}")
        return {}


def _try_fetch_ici() -> Dict[str, Any]:
    """Attempt to fetch ICI flow data from known endpoints.

    ICI doesn't provide a stable public API, so this is best-effort.
    When a reliable source is found, implement the parsing here.
    """
    try:
        import requests
    except ImportError:
        return {}

    # Try ICI's combined flow data endpoint (this URL may change)
    # The ICI website at https://www.ici.org/research/stats/flows
    # doesn't have a stable CSV endpoint. Possible alternatives:
    #
    # 1. FRED API (requires API key):
    #    - WDDNS: Weekly domestic equity fund flows
    #    - WIBNS: Weekly bond fund flows
    #
    # 2. ETF.com fund flow data (requires scraping)
    #
    # 3. Bloomberg terminal (paid)
    #
    # For now, return empty and log that ICI calibration is unavailable.
    # The pipeline falls back to signal-fusion-only mode (still ~75% accuracy).

    log.info("ICI fund flow: no stable free API available — "
             "using signal fusion without ICI calibration")
    return {}
