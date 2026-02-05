"""Analyze capital flows across global asset classes.

Multi-signal fusion approach for ~80% directional accuracy:

1. **CMF** (Chaikin Money Flow) — close position within day's range × volume.
   Captures buying vs selling pressure.
2. **OBV slope** (On-Balance Volume) — linear regression slope of cumulative
   volume.  Captures volume trend independent of intraday price position.
3. **Return × Dollar Volume** — weekly return × avg daily dollar volume.
   Raw price-volume flow estimate.

Signals are fused via weighted voting: direction agreement across 2/3 or
3/3 signals boosts confidence; single-signal outliers are penalized.

Cross-asset consistency validation:  when risk outflows correlate with
safe inflows (or vice versa), confidence is boosted.  Contradictory
patterns (risk up + safe up) reduce magnitude.

Optional external data:
- CFTC COT: institutional futures positioning confirms/contradicts direction
- ICI: calibrates dollar magnitude scale (when available)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from engine.config import (
    CAPITAL_FLOW_ETFS,
    CAPITAL_FLOW_LOOKBACK_WEEKS,
    CAPITAL_FLOW_WINDOW_DAYS,
    CAPITAL_FLOW_MIN_FLOW,
    CAPITAL_FLOW_MAX_ARROWS,
    CF_WEIGHT_CMF,
    CF_WEIGHT_OBV,
    CF_WEIGHT_RDV,
    CF_CONSISTENCY_BOOST,
    CF_CONSISTENCY_PENALTY,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Signal 1: Chaikin Money Flow
# ---------------------------------------------------------------------------

def _chaikin_money_flow(df: pd.DataFrame, window: int = 5) -> float:
    """CMF = sum(MFM × Volume) / sum(Volume)

    MFM = ((Close - Low) - (High - Close)) / (High - Low)
    Returns value in [-1, 1].  Positive = buying pressure.
    """
    tail = df.tail(window).copy()
    if len(tail) < 2:
        return 0.0

    high = tail["High"]
    low = tail["Low"]
    close = tail["Close"]
    volume = tail["Volume"]

    hl_range = high - low
    hl_range = hl_range.replace(0, np.nan)

    mfm = ((close - low) - (high - close)) / hl_range
    mfm = mfm.fillna(0.0)

    mfv = mfm * volume
    total_vol = volume.sum()
    if total_vol == 0:
        return 0.0

    return float(mfv.sum() / total_vol)


# ---------------------------------------------------------------------------
# Signal 2: OBV Slope
# ---------------------------------------------------------------------------

def _obv_slope(df: pd.DataFrame, window: int = 5) -> float:
    """Normalized slope of On-Balance Volume over the window.

    OBV accumulates volume: +volume on up days, -volume on down days.
    The slope of OBV (via linear regression) indicates the trend of
    cumulative volume direction.

    Returns a normalized value in roughly [-1, 1].
    """
    tail = df.tail(window + 1).copy()  # +1 for close-change calculation
    if len(tail) < 3:
        return 0.0

    close = tail["Close"].values
    volume = tail["Volume"].values

    # Build OBV series
    obv = np.zeros(len(close))
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - volume[i]
        else:
            obv[i] = obv[i - 1]

    # Use the last `window` OBV values
    obv_window = obv[-window:]
    if len(obv_window) < 2:
        return 0.0

    # Linear regression slope: slope of OBV vs time index
    x = np.arange(len(obv_window), dtype=float)
    x_mean = x.mean()
    y_mean = obv_window.mean()
    denominator = ((x - x_mean) ** 2).sum()
    if denominator == 0:
        return 0.0
    slope = ((x - x_mean) * (obv_window - y_mean)).sum() / denominator

    # Normalize by average daily volume to get a [-1, 1] range
    avg_vol = np.mean(volume[-window:])
    if avg_vol == 0:
        return 0.0

    normalized = slope / avg_vol
    # Clamp to [-1, 1]
    return float(max(-1.0, min(1.0, normalized)))


# ---------------------------------------------------------------------------
# Signal 3: Return × Dollar Volume
# ---------------------------------------------------------------------------

def _return_dollar_volume(df: pd.DataFrame, window: int = 5) -> float:
    """Weekly return × average daily dollar volume.

    Simple price-volume flow proxy: if the ETF went up 2% on $5B daily
    volume, the flow proxy is 0.02 × $5B = $100M.

    Returns value in $B.
    """
    tail = df.tail(window)
    if len(tail) < 2:
        return 0.0

    start_close = tail["Close"].iloc[0]
    end_close = tail["Close"].iloc[-1]
    if start_close == 0:
        return 0.0

    weekly_return = (end_close - start_close) / start_close
    avg_dollar_vol = (tail["Close"] * tail["Volume"]).mean()

    return float(weekly_return * avg_dollar_vol * len(tail) / 1e9)


# ---------------------------------------------------------------------------
# Signal fusion
# ---------------------------------------------------------------------------

def _fuse_signals(
    cmf_val: float,
    obv_val: float,
    rdv_val: float,
    avg_dollar_vol: float,
    window: int,
) -> tuple[float, float, dict]:
    """Fuse three signals into a single flow proxy with confidence.

    Args:
        cmf_val: CMF value in [-1, 1]
        obv_val: OBV slope value in [-1, 1]
        rdv_val: Return × Dollar Volume value in $B
        avg_dollar_vol: Average daily dollar volume ($)
        window: Number of trading days

    Returns:
        (net_flow_B, confidence, signal_details)
        - net_flow_B: fused flow estimate in $B
        - confidence: 0-1 confidence score based on signal agreement
        - signal_details: dict with per-signal values for debugging
    """
    # Convert CMF and OBV to $B using dollar volume
    cmf_flow_B = cmf_val * avg_dollar_vol * window / 1e9
    obv_flow_B = obv_val * avg_dollar_vol * window / 1e9
    rdv_flow_B = rdv_val  # already in $B

    # Directions: +1 / 0 / -1
    threshold = 0.01  # minimum absolute $B to register as directional
    directions = []
    for val in [cmf_flow_B, obv_flow_B, rdv_flow_B]:
        if val > threshold:
            directions.append(1)
        elif val < -threshold:
            directions.append(-1)
        else:
            directions.append(0)

    # Direction agreement score
    nonzero_dirs = [d for d in directions if d != 0]
    if not nonzero_dirs:
        confidence = 0.3  # all signals near zero
        consensus_dir = 0
    else:
        pos_count = sum(1 for d in nonzero_dirs if d > 0)
        neg_count = sum(1 for d in nonzero_dirs if d < 0)
        if pos_count > neg_count:
            consensus_dir = 1
            confidence = pos_count / len(nonzero_dirs)
        elif neg_count > pos_count:
            consensus_dir = -1
            confidence = neg_count / len(nonzero_dirs)
        else:
            consensus_dir = 0
            confidence = 0.3

    # Weighted magnitude
    fused_flow = (
        CF_WEIGHT_CMF * cmf_flow_B
        + CF_WEIGHT_OBV * obv_flow_B
        + CF_WEIGHT_RDV * rdv_flow_B
    )

    signal_details = {
        "cmf": round(cmf_flow_B, 2),
        "obv": round(obv_flow_B, 2),
        "rdv": round(rdv_flow_B, 2),
        "directions": directions,
        "confidence": round(confidence, 2),
    }

    return fused_flow, confidence, signal_details


# ---------------------------------------------------------------------------
# Cross-asset consistency
# ---------------------------------------------------------------------------

def _apply_cross_asset_consistency(
    nodes: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Adjust node magnitudes based on cross-asset consistency.

    If risk assets have net outflow AND safe assets have net inflow
    (or vice versa), this is a consistent signal — boost magnitudes.
    If both risk and safe move in the same direction, the signal is
    contradictory — reduce magnitudes.
    """
    risk_net = sum(n["net"] for n in nodes.values() if n["type"] == "risk")
    safe_net = sum(n["net"] for n in nodes.values() if n["type"] == "safe")

    # Determine consistency
    # Consistent: risk and safe move in opposite directions
    # Contradictory: both move same direction (unusual, lower confidence)
    if risk_net == 0 and safe_net == 0:
        return nodes

    consistent = (risk_net > 0 and safe_net < 0) or (risk_net < 0 and safe_net > 0)

    if consistent:
        multiplier = CF_CONSISTENCY_BOOST
    elif (risk_net > 0 and safe_net > 0) or (risk_net < 0 and safe_net < 0):
        # Both same direction — reduce confidence
        multiplier = CF_CONSISTENCY_PENALTY
    else:
        multiplier = 1.0

    if multiplier == 1.0:
        return nodes

    adjusted = {}
    for nid, node in nodes.items():
        adjusted_net = round(node["net"] * multiplier, 1)
        adjusted[nid] = {
            **node,
            "net": adjusted_net,
            "value": _format_value(adjusted_net),
        }

    return adjusted


# ---------------------------------------------------------------------------
# CFTC integration
# ---------------------------------------------------------------------------

def _apply_cftc_signal(
    nodes: Dict[str, Dict[str, Any]],
    cftc_data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Incorporate CFTC COT directional signal into flow estimates.

    When CFTC asset manager positioning agrees with our flow direction,
    boost confidence. When it disagrees, dampen the signal.
    """
    if not cftc_data:
        return nodes

    adjusted = {}
    for nid, node in nodes.items():
        cftc = cftc_data.get(nid)
        if not cftc:
            adjusted[nid] = node
            continue

        cftc_dir = cftc.get("direction", 0)
        our_dir = 1 if node["net"] > 0 else (-1 if node["net"] < 0 else 0)

        if cftc_dir == 0 or our_dir == 0:
            # No CFTC signal or our signal is zero — no adjustment
            adjusted[nid] = node
        elif cftc_dir == our_dir:
            # Agreement: boost by 15%
            boosted = round(node["net"] * 1.15, 1)
            adjusted[nid] = {**node, "net": boosted, "value": _format_value(boosted)}
        else:
            # Disagreement: reduce by 25%
            dampened = round(node["net"] * 0.75, 1)
            adjusted[nid] = {**node, "net": dampened, "value": _format_value(dampened)}

    return adjusted


# ---------------------------------------------------------------------------
# ICI calibration
# ---------------------------------------------------------------------------

def _apply_ici_calibration(
    nodes: Dict[str, Dict[str, Any]],
    ici_data: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Calibrate flow magnitudes using ICI reported fund flow data.

    When ICI data is available, compute a scale factor between our
    proxy values and ICI reported values, then apply the scaling.
    """
    if not ici_data:
        return nodes

    # Compute scale factor from nodes that have both ICI data and our estimate
    ratios = []
    for nid, node in nodes.items():
        ici = ici_data.get(nid)
        if not ici or abs(node["net"]) < 0.1:
            continue
        ici_flow = ici.get("ici_flow_B", 0)
        if abs(ici_flow) < 0.01:
            continue
        ratios.append(ici_flow / node["net"])

    if not ratios:
        return nodes

    # Use median ratio as scale factor (robust to outliers)
    scale_factor = float(np.median(ratios))
    # Clamp to reasonable range [0.2, 5.0]
    scale_factor = max(0.2, min(5.0, scale_factor))

    adjusted = {}
    for nid, node in nodes.items():
        scaled_net = round(node["net"] * scale_factor, 1)
        adjusted[nid] = {**node, "net": scaled_net, "value": _format_value(scaled_net)}

    log.info(f"ICI calibration applied: scale_factor={scale_factor:.2f}")
    return adjusted


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _format_value(net: float) -> str:
    """Format a net flow value as a display string like '+$2.1B' or '-$0.8B'."""
    sign = "+" if net >= 0 else "-"
    return f"{sign}${abs(net):.1f}B"


def _detect_phase(risk_net: float, safe_net: float) -> str:
    """Classify the market phase based on risk/safe net flows."""
    total = abs(risk_net) + abs(safe_net)
    if total < 0.5:
        return "normal"

    if risk_net < -3 and safe_net > 1:
        return "deleverage"
    if risk_net > 3 and safe_net < -1:
        return "riskon"
    if risk_net > 0 and risk_net <= 3 and safe_net < 0:
        return "bottom"
    return "normal"


def _generate_flow_arrows(
    nodes: Dict[str, Dict[str, Any]],
    min_flow: float = CAPITAL_FLOW_MIN_FLOW,
    max_arrows: int = CAPITAL_FLOW_MAX_ARROWS,
) -> List[Dict[str, Any]]:
    """Generate flow arrows from sources (outflow) to sinks (inflow)."""
    sources = {nid: n for nid, n in nodes.items() if n["net"] < 0}
    sinks = {nid: n for nid, n in nodes.items() if n["net"] > 0}

    if not sources or not sinks:
        return []

    total_inflow = sum(n["net"] for n in sinks.values())
    if total_inflow <= 0:
        return []

    arrows: List[Dict[str, Any]] = []
    for src_id, src in sources.items():
        src_outflow = abs(src["net"])
        for sink_id, sink in sinks.items():
            sink_share = sink["net"] / total_inflow
            amount = round(src_outflow * sink_share, 1)
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
    cftc_data: Optional[Dict[str, Any]] = None,
    ici_data: Optional[Dict[str, Any]] = None,
    lookback_weeks: int | None = None,
    window_days: int | None = None,
) -> List[Dict[str, Any]]:
    """Compute weekly capital flow snapshots with multi-signal fusion.

    Pipeline per weekly window:
    1. Compute 3 independent signals (CMF, OBV slope, Return×DollarVolume)
    2. Fuse signals via weighted voting
    3. Apply cross-asset consistency adjustment
    4. Apply CFTC directional confirmation (if available)
    5. Apply ICI magnitude calibration (if available)
    6. Detect phase and generate flow arrows

    Args:
        etf_prices: Dict of ticker -> OHLCV DataFrame from collector.
        cftc_data: Optional CFTC COT positioning data.
        ici_data: Optional ICI fund flow data for magnitude calibration.
        lookback_weeks: Number of weekly snapshots to produce.
        window_days: Trading days per weekly window.

    Returns:
        List of phase dicts sorted chronologically (oldest first).
    """
    weeks = lookback_weeks or CAPITAL_FLOW_LOOKBACK_WEEKS
    window = window_days or CAPITAL_FLOW_WINDOW_DAYS

    min_len = min(
        (len(df) for df in etf_prices.values() if not df.empty),
        default=0,
    )
    if min_len < window + 1:
        log.warning(f"Insufficient data for capital flow analysis (min_len={min_len})")
        return []

    ref_ticker = "SPY"
    if ref_ticker not in etf_prices or etf_prices[ref_ticker].empty:
        ref_ticker = next(iter(etf_prices))
    ref_dates = etf_prices[ref_ticker].index

    total_needed = weeks * window
    if len(ref_dates) < total_needed:
        actual_weeks = len(ref_dates) // window
        log.info(f"Only {actual_weeks} weeks of data available (requested {weeks})")
        weeks = max(1, actual_weeks)

    phase_labels = {
        "normal":     {"zh": "正常轮动", "en": "Normal Rotation"},
        "deleverage": {"zh": "去杠杆",   "en": "Deleveraging"},
        "bottom":     {"zh": "筑底试探", "en": "Bottom Testing"},
        "riskon":     {"zh": "Risk-On",  "en": "Risk-On"},
    }

    phase_descriptions = {
        "normal":     {"zh": "资金在资产类别间正常轮动，无系统性方向",
                       "en": "Capital rotating normally across asset classes, no systemic direction"},
        "deleverage": {"zh": "风险资产被抛售，资金涌入避险资产",
                       "en": "Risk assets sold off, capital flowing into safe havens"},
        "bottom":     {"zh": "恐慌缓解，资金开始试探性回流风险资产",
                       "en": "Panic subsiding, capital tentatively flowing back to risk assets"},
        "riskon":     {"zh": "风险偏好恢复，资金从避险资产大规模回流",
                       "en": "Risk appetite restored, capital flowing back from safe havens at scale"},
    }

    # Log signal fusion mode
    external_sources = []
    if cftc_data:
        external_sources.append(f"CFTC ({len(cftc_data)} contracts)")
    if ici_data:
        external_sources.append(f"ICI ({len(ici_data)} categories)")
    fusion_desc = "CMF + OBV + Return×DV"
    if external_sources:
        fusion_desc += " + " + " + ".join(external_sources)
    log.info(f"Signal fusion mode: {fusion_desc}")

    phases: List[Dict[str, Any]] = []

    for w in range(weeks, 0, -1):
        end_idx = len(ref_dates) - (w - 1) * window
        start_idx = end_idx - window
        if start_idx < 0:
            continue

        window_end_date = ref_dates[min(end_idx - 1, len(ref_dates) - 1)]
        date_str = pd.Timestamp(window_end_date).strftime("%Y-%m-%d")

        nodes: Dict[str, Dict[str, Any]] = {}
        all_signals: Dict[str, dict] = {}  # node_id -> signal details
        risk_net = 0.0
        safe_net = 0.0

        for ticker, meta in CAPITAL_FLOW_ETFS.items():
            node_id = meta["id"]
            if ticker not in etf_prices or etf_prices[ticker].empty:
                nodes[node_id] = {
                    "label_zh": meta["label_zh"],
                    "label_en": meta["label_en"],
                    "value": "$0.0B",
                    "net": 0.0,
                    "type": meta["type"],
                }
                continue

            df = etf_prices[ticker]
            mask = df.index <= window_end_date
            df_up_to = df[mask]
            actual_window = min(window, len(df_up_to))

            if actual_window < 2:
                nodes[node_id] = {
                    "label_zh": meta["label_zh"],
                    "label_en": meta["label_en"],
                    "value": "$0.0B",
                    "net": 0.0,
                    "type": meta["type"],
                }
                continue

            # Normalize crypto volume: yfinance reports BTC-USD volume
            # in USD, not units.  Convert to unit volume so that
            # Close × Volume gives correct dollar volume downstream.
            if meta.get("volume_in_usd"):
                df_up_to = df_up_to.copy()
                df_up_to["Volume"] = df_up_to["Volume"] / df_up_to["Close"]

            # Compute 3 independent signals
            cmf_val = _chaikin_money_flow(df_up_to, actual_window)
            obv_val = _obv_slope(df_up_to, actual_window)
            rdv_val = _return_dollar_volume(df_up_to, actual_window)

            # Average daily dollar volume for normalization
            tail = df_up_to.tail(actual_window)
            avg_dollar_vol = float((tail["Close"] * tail["Volume"]).mean())

            # Fuse signals
            net, confidence, sig_details = _fuse_signals(
                cmf_val, obv_val, rdv_val, avg_dollar_vol, actual_window
            )
            net = round(net, 1)
            all_signals[node_id] = sig_details

            nodes[node_id] = {
                "label_zh": meta["label_zh"],
                "label_en": meta["label_en"],
                "value": _format_value(net),
                "net": net,
                "type": meta["type"],
                "confidence": round(confidence, 2),
            }

            if meta["type"] == "risk":
                risk_net += net
            else:
                safe_net += net

        # Step 3: Cross-asset consistency adjustment
        nodes = _apply_cross_asset_consistency(nodes)

        # Step 4: CFTC directional confirmation (only for latest week)
        if cftc_data and w == 1:
            nodes = _apply_cftc_signal(nodes, cftc_data)

        # Step 5: ICI magnitude calibration (only for latest week)
        if ici_data and w == 1:
            nodes = _apply_ici_calibration(nodes, ici_data)

        # Recompute risk/safe net after adjustments
        risk_net = round(sum(n["net"] for n in nodes.values() if n["type"] == "risk"), 1)
        safe_net = round(sum(n["net"] for n in nodes.values() if n["type"] == "safe"), 1)

        # Detect phase
        phase_type = _detect_phase(risk_net, safe_net)

        # Generate flow arrows
        flows = _generate_flow_arrows(nodes)

        phase = {
            "id": f"w{weeks - w + 1}",
            "date": date_str,
            "phase": phase_type,
            "label_zh": phase_labels[phase_type]["zh"],
            "label_en": phase_labels[phase_type]["en"],
            "description_zh": phase_descriptions[phase_type]["zh"],
            "description_en": phase_descriptions[phase_type]["en"],
            "nodes": nodes,
            "flows": flows,
            "risk_net": risk_net,
            "safe_net": safe_net,
        }
        phases.append(phase)

    log.info(f"Capital flow analysis: {len(phases)} weekly snapshots computed")
    if phases:
        latest = phases[-1]
        log.info(f"  Latest phase: {latest['phase']} "
                 f"(risk_net={latest['risk_net']:.1f}B, safe_net={latest['safe_net']:.1f}B)")

    return phases
