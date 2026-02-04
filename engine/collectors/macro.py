"""Collect market-level macro indicators for regime detection.

Fetches VIX, S&P 500 (with SMA200), 10-Year Treasury yield,
and 13-Week T-Bill yield from Yahoo Finance.
"""

from __future__ import annotations

from typing import Any, Dict

import yfinance as yf

from engine.utils.logger import get_logger

log = get_logger(__name__)

_VIX_TICKER = "^VIX"
_SP500_TICKER = "^GSPC"
_TNX_TICKER = "^TNX"     # 10-Year Treasury yield
_IRX_TICKER = "^IRX"     # 13-Week Treasury Bill yield


def collect_macro() -> Dict[str, Any]:
    """Fetch macro market indicators.

    Returns:
        dict with keys: vix, sp500_close, sp500_sma200,
        sp500_vs_sma200_pct, tnx_yield, irx_yield, yield_curve_spread
    """
    result: Dict[str, Any] = {}

    # VIX
    try:
        vix = yf.Ticker(_VIX_TICKER)
        vix_hist = vix.history(period="5d")
        if not vix_hist.empty:
            result["vix"] = float(vix_hist["Close"].iloc[-1])
    except Exception as e:
        log.warning(f"Failed to fetch VIX: {e}")

    # S&P 500 + SMA200
    try:
        sp = yf.Ticker(_SP500_TICKER)
        sp_hist = sp.history(period="1y")
        if not sp_hist.empty:
            sp_close = float(sp_hist["Close"].iloc[-1])
            result["sp500_close"] = sp_close
            if len(sp_hist) >= 200:
                sma200 = float(sp_hist["Close"].tail(200).mean())
                result["sp500_sma200"] = round(sma200, 2)
                result["sp500_vs_sma200_pct"] = round(
                    (sp_close - sma200) / sma200, 4
                )
    except Exception as e:
        log.warning(f"Failed to fetch S&P 500: {e}")

    # 10-Year Treasury yield
    try:
        tnx = yf.Ticker(_TNX_TICKER)
        tnx_hist = tnx.history(period="5d")
        if not tnx_hist.empty:
            result["tnx_yield"] = float(tnx_hist["Close"].iloc[-1])
    except Exception as e:
        log.warning(f"Failed to fetch 10Y Treasury: {e}")

    # 13-Week T-Bill yield
    try:
        irx = yf.Ticker(_IRX_TICKER)
        irx_hist = irx.history(period="5d")
        if not irx_hist.empty:
            result["irx_yield"] = float(irx_hist["Close"].iloc[-1])
    except Exception as e:
        log.warning(f"Failed to fetch 13W T-Bill: {e}")

    # Yield curve spread (10Y - 3M) in percentage points
    if "tnx_yield" in result and "irx_yield" in result:
        result["yield_curve_spread"] = round(
            result["tnx_yield"] - result["irx_yield"], 3
        )

    log.info(f"Macro data collected: VIX={result.get('vix')}, "
             f"SP500%SMA200={result.get('sp500_vs_sma200_pct')}, "
             f"YC spread={result.get('yield_curve_spread')}")
    return result
