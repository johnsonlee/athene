"""Analyze capital flows across global asset classes.

Uses ETF shares outstanding changes (creation/redemption) to compute
direct fund flows — measuring real institutional capital allocation
rather than proxy signals.

    daily_fund_flow = Δ(shares_outstanding) × close_price

RFI (Risk Flow Index) uses tanh normalization for smooth, bounded output
without the saturation issues of the previous ratio-based formula.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from engine.config import (
    CAPITAL_FLOW_ETFS,
    CAPITAL_FLOW_LOOKBACK_WEEKS,
    CAPITAL_FLOW_WINDOW_DAYS,
    CAPITAL_FLOW_MIN_FLOW,
    CAPITAL_FLOW_MAX_ARROWS,
    RFI_TANH_SCALE,
    RFI_PANIC,
    RFI_RISK_ON,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)

# Tickers that use proxy flow estimation (no shares outstanding data)
_PROXY_TICKERS = {
    ticker for ticker, meta in CAPITAL_FLOW_ETFS.items()
    if meta.get("shares_source") is None
}


# ---------------------------------------------------------------------------
# Core flow computation
# ---------------------------------------------------------------------------

def _compute_daily_flows(etf_prices: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
    """Compute daily fund flows from shares outstanding changes.

    daily_flow = Δ(shares_outstanding) × close_price, in $B.

    Args:
        etf_prices: Dict of ticker -> DataFrame with columns including
            Close, Volume, and optionally Shares.

    Returns:
        Dict of ticker -> Series of daily flows in $B, indexed by date.
        Tickers without Shares data are omitted.
    """
    flows: Dict[str, pd.Series] = {}

    for ticker, df in etf_prices.items():
        if "Shares" not in df.columns:
            continue

        shares = df["Shares"].dropna()
        if len(shares) < 2:
            continue

        close = df["Close"].reindex(shares.index)
        delta_shares = shares.diff()
        daily_flow = (delta_shares * close) / 1e9  # Convert to $B
        daily_flow = daily_flow.dropna()

        if not daily_flow.empty:
            flows[ticker] = daily_flow

    return flows


def _compute_proxy_daily_flows(etf_prices: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
    """Proxy flow estimate for tickers without shares outstanding data.

    Uses daily_return × dollar_volume as flow proxy.
    Only applies to tickers where config has shares_source=None
    (SPY, BIL, VGK).

    Args:
        etf_prices: Dict of ticker -> DataFrame with Close, Volume columns.

    Returns:
        Dict of ticker -> Series of proxy daily flows in $B, indexed by date.
    """
    flows: Dict[str, pd.Series] = {}

    for ticker in _PROXY_TICKERS:
        if ticker not in etf_prices:
            continue

        df = etf_prices[ticker]
        if "Close" not in df.columns or "Volume" not in df.columns:
            continue
        if len(df) < 2:
            continue

        close = df["Close"].dropna()
        volume = df["Volume"].dropna()
        # Align on common index
        common = close.index.intersection(volume.index)
        if len(common) < 2:
            continue
        close = close.loc[common]
        volume = volume.loc[common]

        daily_return = close.pct_change()
        dollar_volume = close * volume
        proxy_flow = (daily_return * dollar_volume) / 1e9  # in $B
        proxy_flow = proxy_flow.dropna()

        if not proxy_flow.empty:
            flows[ticker] = proxy_flow

    return flows


def _aggregate_rolling_flows(
    daily_flows: Dict[str, pd.Series],
    window: int,
) -> Dict[str, pd.Series]:
    """Rolling sum of daily flows over a window of trading days.

    Args:
        daily_flows: Dict of ticker -> daily flow Series ($B).
        window: Number of trading days to sum over.

    Returns:
        Dict of ticker -> rolling sum Series ($B).
    """
    result: Dict[str, pd.Series] = {}
    for ticker, flow_series in daily_flows.items():
        if len(flow_series) < window:
            result[ticker] = flow_series
        else:
            result[ticker] = flow_series.rolling(window=window, min_periods=1).sum()
    return result


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _format_value(net: float) -> str:
    """Format a net flow value as a display string like '+$2.1B' or '-$0.8B'."""
    sign = "+" if net >= 0 else "-"
    return f"{sign}${abs(net):.1f}B"


def _compute_rfi(risk_net: float, safe_net: float, scale: float = RFI_TANH_SCALE) -> float:
    """Compute Risk Flow Index with tanh normalization.

    tanh((risk_net - safe_net) / scale) — smooth, bounded [-1, +1],
    no saturation at extremes unlike the ratio-based formula.

    When both risk and safe are net outflow, RFI is forced to 0.0 —
    the difference in bleed rates has no directional rotation meaning.
    """
    if risk_net < 0 and safe_net < 0:
        return 0.0
    return round(math.tanh((risk_net - safe_net) / scale), 4)


def _detect_phase(risk_net: float, safe_net: float, rfi: float) -> str:
    """Classify the market phase based on risk/safe net flows and RFI.

    Uses RFI thresholds as primary signal (stable, based on real flows).
    """
    total = abs(risk_net) + abs(safe_net)
    if total < 0.1:
        return "normal"

    # Both sides declining — broad outflow
    if risk_net < -0.5 and safe_net < -0.5:
        return "outflow"

    if rfi < RFI_PANIC:
        return "deleverage"
    if rfi < -0.3 and risk_net < 0:
        # Capital flowing from risk to safe
        if safe_net > 0:
            return "deleverage"
        return "normal"
    if rfi > RFI_RISK_ON:
        return "riskon"
    if 0 < rfi <= RFI_RISK_ON and risk_net > 0 and safe_net < 0:
        return "bottom"

    return "normal"


def _generate_flow_arrows(
    nodes: Dict[str, Dict[str, Any]],
    min_flow: float = CAPITAL_FLOW_MIN_FLOW,
    max_arrows: int = CAPITAL_FLOW_MAX_ARROWS,
) -> List[Dict[str, Any]]:
    """Generate flow arrows from sources (outflow) to sinks (inflow).

    Total arrow volume is capped at min(total_outflow, total_inflow) to
    enforce zero-sum accounting.
    """
    sources = {nid: n for nid, n in nodes.items() if n["net"] < 0}
    sinks = {nid: n for nid, n in nodes.items() if n["net"] > 0}

    if not sources or not sinks:
        return []

    total_outflow = sum(abs(n["net"]) for n in sources.values())
    total_inflow = sum(n["net"] for n in sinks.values())
    if total_inflow <= 0 or total_outflow <= 0:
        return []

    cap = min(total_outflow, total_inflow)

    arrows: List[Dict[str, Any]] = []
    for src_id, src in sources.items():
        src_share = abs(src["net"]) / total_outflow
        for sink_id, sink in sinks.items():
            sink_share = sink["net"] / total_inflow
            amount = round(cap * src_share * sink_share, 1)
            if amount >= min_flow:
                arrows.append({
                    "from": src_id,
                    "to": sink_id,
                    "amount": amount,
                    "label": f"${amount:.1f}B",
                })

    arrows.sort(key=lambda a: a["amount"], reverse=True)
    return arrows[:max_arrows]


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

def analyze_capital_flows(
    etf_prices: Dict[str, pd.DataFrame],
    lookback_weeks: int | None = None,
    window_days: int | None = None,
) -> List[Dict[str, Any]]:
    """Compute weekly capital flow snapshots from ETF shares outstanding.

    Pipeline per weekly window:
    1. Compute daily flows from Δ(shares_outstanding) × close
    2. Rolling window aggregation
    3. Build nodes with real $ flow values
    4. Compute risk_net / safe_net
    5. Compute RFI with tanh formula
    6. Detect phase
    7. Generate flow arrows (zero-sum)

    Args:
        etf_prices: Dict of ticker -> OHLCV+Shares DataFrame from collector.
        lookback_weeks: Number of weekly snapshots to produce.
        window_days: Trading days per weekly window.

    Returns:
        List of phase dicts sorted chronologically (oldest first).
    """
    weeks = lookback_weeks or CAPITAL_FLOW_LOOKBACK_WEEKS
    window = window_days or CAPITAL_FLOW_WINDOW_DAYS

    # Check for sufficient data
    min_len = min(
        (len(df) for df in etf_prices.values() if not df.empty),
        default=0,
    )
    if min_len < window + 1:
        log.warning(f"Insufficient data for capital flow analysis (min_len={min_len})")
        return []

    # Compute daily flows from shares outstanding (real data)
    daily_flows = _compute_daily_flows(etf_prices)
    tickers_with_shares = set(daily_flows.keys())

    # Compute proxy flows for tickers without shares data (SPY, BIL, VGK)
    proxy_flows = _compute_proxy_daily_flows(etf_prices)
    tickers_with_proxy = set(proxy_flows.keys())

    # Merge: proxy only fills in tickers not already in daily_flows
    for ticker, flow_series in proxy_flows.items():
        if ticker not in daily_flows:
            daily_flows[ticker] = flow_series

    if not daily_flows:
        log.warning("No flow data available — cannot compute fund flows")
        return []

    log.info(f"Computing fund flows: {len(tickers_with_shares)} real + "
             f"{len(tickers_with_proxy)} proxy tickers")

    # Aggregate rolling flows
    rolling_flows = _aggregate_rolling_flows(daily_flows, window)

    # Determine reference dates from the ticker with most data
    ref_ticker = "SPY" if "SPY" in rolling_flows else next(iter(rolling_flows))
    ref_dates = rolling_flows[ref_ticker].index

    total_needed = weeks * window
    if len(ref_dates) < total_needed:
        actual_weeks = len(ref_dates) // window
        log.info(f"Only {actual_weeks} weeks of data available (requested {weeks})")
        weeks = max(1, actual_weeks)

    phase_labels = {
        "normal":     {"zh": "正常轮动", "en": "Normal Rotation"},
        "deleverage": {"zh": "去杠杆",   "en": "Deleveraging"},
        "outflow":    {"zh": "全面流出", "en": "Broad Outflow"},
        "bottom":     {"zh": "筑底试探", "en": "Bottom Testing"},
        "riskon":     {"zh": "Risk-On",  "en": "Risk-On"},
    }

    phase_descriptions = {
        "normal":     {"zh": "资金在资产类别间正常轮动，无系统性方向",
                       "en": "Capital rotating normally across asset classes, no systemic direction"},
        "deleverage": {"zh": "风险资产被抛售，资金涌入避险资产",
                       "en": "Risk assets sold off, capital flowing into safe havens"},
        "outflow":    {"zh": "风险资产与避险资产同步流出，资金撤离至场外（货基/存款等）",
                       "en": "Both risk and safe assets declining, capital exiting to money markets / deposits"},
        "bottom":     {"zh": "恐慌缓解，资金开始试探性回流风险资产",
                       "en": "Panic subsiding, capital tentatively flowing back to risk assets"},
        "riskon":     {"zh": "风险偏好恢复，资金从避险资产大规模回流",
                       "en": "Risk appetite restored, capital flowing back from safe havens at scale"},
    }

    log.info(f"Signal method: hybrid (ETF shares outstanding + volume-price proxy)")

    phases: List[Dict[str, Any]] = []

    for w in range(weeks, 0, -1):
        end_idx = len(ref_dates) - (w - 1) * window
        start_idx = end_idx - window
        if start_idx < 0:
            continue

        window_end_date = ref_dates[min(end_idx - 1, len(ref_dates) - 1)]
        date_str = pd.Timestamp(window_end_date).strftime("%Y-%m-%d")

        nodes: Dict[str, Dict[str, Any]] = {}
        risk_net = 0.0
        safe_net = 0.0

        for ticker, meta in CAPITAL_FLOW_ETFS.items():
            node_id = meta["id"]

            if ticker not in rolling_flows:
                # No shares data for this ticker — show zero flow
                nodes[node_id] = {
                    "label_zh": meta["label_zh"],
                    "label_en": meta["label_en"],
                    "value": "$0.0B",
                    "net": 0.0,
                    "type": meta["type"],
                }
                continue

            flow_series = rolling_flows[ticker]
            # Get the flow value at or before window_end_date
            mask = flow_series.index <= window_end_date
            valid = flow_series[mask]
            if valid.empty:
                net = 0.0
            else:
                net = round(float(valid.iloc[-1]), 1)

            confidence = 0.6 if ticker in tickers_with_proxy else 1.0
            nodes[node_id] = {
                "label_zh": meta["label_zh"],
                "label_en": meta["label_en"],
                "value": _format_value(net),
                "net": net,
                "type": meta["type"],
                "confidence": confidence,
            }

            if meta["type"] == "risk":
                risk_net += net
            else:
                safe_net += net

        risk_net = round(risk_net, 1)
        safe_net = round(safe_net, 1)

        # Compute RFI with tanh normalization
        rfi = _compute_rfi(risk_net, safe_net)

        # Detect phase
        phase_type = _detect_phase(risk_net, safe_net, rfi)

        # Generate flow arrows
        flows = _generate_flow_arrows(nodes)

        # Compute untracked flow (imbalance between outflows and inflows)
        total_outflow = round(sum(abs(n["net"]) for n in nodes.values() if n["net"] < 0), 1)
        total_inflow = round(sum(n["net"] for n in nodes.values() if n["net"] > 0), 1)
        untracked = round(total_outflow - total_inflow, 1)

        phase = {
            "id": f"w{weeks - w + 1}",
            "date": date_str,
            "phase": phase_type,
            "rfi": rfi,
            "label_zh": phase_labels[phase_type]["zh"],
            "label_en": phase_labels[phase_type]["en"],
            "description_zh": phase_descriptions[phase_type]["zh"],
            "description_en": phase_descriptions[phase_type]["en"],
            "nodes": nodes,
            "flows": flows,
            "risk_net": risk_net,
            "safe_net": safe_net,
            "untracked": untracked,
        }
        phases.append(phase)

    log.info(f"Capital flow analysis: {len(phases)} weekly snapshots computed")
    if phases:
        latest = phases[-1]
        log.info(f"  Latest phase: {latest['phase']} "
                 f"(risk_net={latest['risk_net']:.1f}B, safe_net={latest['safe_net']:.1f}B, "
                 f"RFI={latest['rfi']:.4f})")

    return phases
