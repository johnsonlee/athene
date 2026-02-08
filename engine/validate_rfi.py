"""RFI (Risk Flow Index) validation harness.

Validates the synthetic RFI indicator through 4 indirect checks:
1. Event sanity: known market events produce expected RFI readings
2. VIX correlation: RFI vs VIX negative correlation in expected range
3. Phase transition sequence: no impossible/noisy phase jumps
4. RFI-phase consistency: RFI sign matches phase semantics

Usage:
    python -m engine.validate_rfi
    python -m engine.validate_rfi --window 10        # custom rolling window
    python -m engine.validate_rfi --no-fetch-vix     # skip yfinance VIX fetch
    python -m engine.validate_rfi --no-export        # console only
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from engine.analyzers.capital_flow import (
    _aggregate_rolling_flows,
    _compute_daily_flows,
    _compute_proxy_daily_flows,
    _compute_rfi,
    _detect_phase,
)
from engine.collectors.capital_flow import load_capital_flow_etfs_from_collected
from engine.config import (
    CAPITAL_FLOW_ETFS,
    RFI_MILD_RISK_OFF,
    RFI_RISK_ON,
)
from engine.exporters.json_exporter import NumpyEncoder
from engine.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Known events for sanity check
# ---------------------------------------------------------------------------

KNOWN_EVENTS = [
    {
        "name": "2023-03 SVB banking crisis",
        "start": "2023-03-08",
        "end": "2023-03-24",
        "expected_sign": "negative",
        "expected_phases": {"deleverage", "outflow"},
        "min_window": 5,
    },
    {
        "name": "2023-10 yield spike to 5%",
        "start": "2023-10-01",
        "end": "2023-10-31",
        "expected_sign": "negative",
        "expected_phases": {"deleverage", "outflow"},
        "lenient": True,  # gradual move — only require negative seen, not avg
        "min_window": 5,
    },
    {
        "name": "2024-08 yen carry trade unwind",
        "start": "2024-08-01",
        "end": "2024-08-12",
        "expected_sign": "negative",
        "expected_phases": {"deleverage", "outflow"},
        "min_window": 5,
    },
    {
        "name": "2024-11 post-election risk-on",
        "start": "2024-11-06",
        "end": "2024-11-30",
        "expected_sign": "positive",
        "expected_phases": {"riskon", "normal"},
        "min_window": 5,
    },
    {
        "name": "2025-04 Trump tariff war (Liberation Day)",
        "start": "2025-04-02",
        "end": "2025-04-30",
        "expected_sign": "negative",
        "expected_phases": {"deleverage", "outflow", "bottom"},
        "min_window": 5,
    },
]

# Valid phase transitions
VALID_TRANSITIONS: Dict[str, set] = {
    "normal":     {"deleverage", "outflow", "riskon", "bottom"},
    "deleverage": {"outflow", "normal", "bottom"},
    "outflow":    {"deleverage", "bottom", "normal"},
    "bottom":     {"riskon", "normal", "outflow"},
    "riskon":     {"normal", "bottom", "deleverage"},
}


# ---------------------------------------------------------------------------
# Data loading & RFI reconstruction
# ---------------------------------------------------------------------------

def _compute_daily_rfi_series(
    etf_prices: Dict[str, pd.DataFrame],
    window: int,
) -> List[Dict[str, Any]]:
    """Reconstruct daily RFI time series from raw ETF data.

    Returns list of {date, risk_net, safe_net, rfi, phase} sorted chronologically.
    """
    # Compute daily flows
    real_flows = _compute_daily_flows(etf_prices)
    proxy_flows = _compute_proxy_daily_flows(etf_prices)
    all_flows = dict(real_flows)
    for ticker, series in proxy_flows.items():
        if ticker not in all_flows:
            all_flows[ticker] = series

    if not all_flows:
        log.warning("No flow data available")
        return []

    # Rolling aggregation
    rolling = _aggregate_rolling_flows(all_flows, window)

    # Reference date index from the ticker with most data
    ref_ticker = max(rolling, key=lambda t: len(rolling[t]))
    ref_index = rolling[ref_ticker].index

    # Build type lookup: ticker -> "risk" | "safe"
    ticker_type = {t: meta["type"] for t, meta in CAPITAL_FLOW_ETFS.items()}

    series: List[Dict[str, Any]] = []
    for date in ref_index:
        risk_net = 0.0
        safe_net = 0.0
        for ticker, flow_series in rolling.items():
            if date not in flow_series.index:
                continue
            val = float(flow_series.loc[date])
            if np.isnan(val):
                continue
            t = ticker_type.get(ticker, "risk")
            if t == "risk":
                risk_net += val
            else:
                safe_net += val

        risk_net = round(risk_net, 2)
        safe_net = round(safe_net, 2)
        rfi = _compute_rfi(risk_net, safe_net)
        phase = _detect_phase(risk_net, safe_net, rfi)
        date_str = pd.Timestamp(date).strftime("%Y-%m-%d")

        series.append({
            "date": date_str,
            "risk_net": risk_net,
            "safe_net": safe_net,
            "rfi": rfi,
            "phase": phase,
        })

    log.info(f"Reconstructed daily RFI: {len(series)} data points "
             f"({series[0]['date']} to {series[-1]['date']})")
    return series


def _fetch_vix_history(start: str, end: str) -> Dict[str, float]:
    """Fetch VIX daily close from yfinance."""
    import yfinance as yf

    log.info(f"Fetching VIX history {start} to {end}...")
    vix = yf.Ticker("^VIX")
    hist = vix.history(start=start, end=end)
    if hist.empty:
        log.warning("VIX fetch returned empty")
        return {}

    result = {}
    for date, row in hist.iterrows():
        date_str = pd.Timestamp(date).strftime("%Y-%m-%d")
        result[date_str] = float(row["Close"])

    log.info(f"VIX history: {len(result)} data points")
    return result


# ---------------------------------------------------------------------------
# Check 1: Event sanity
# ---------------------------------------------------------------------------

def check_event_sanity(
    rfi_series: List[Dict[str, Any]],
    window: int,
) -> Dict[str, Any]:
    """Validate known market events produce expected RFI readings."""
    rfi_by_date = {d["date"]: d for d in rfi_series}
    events_result = []
    verdicts = []

    for event in KNOWN_EVENTS:
        name = event["name"]
        start, end = event["start"], event["end"]
        expected_sign = event["expected_sign"]
        expected_phases = event["expected_phases"]
        lenient = event.get("lenient", False)
        min_window = event.get("min_window", 5)

        # Skip if rolling window exceeds event duration
        event_days = sum(1 for d in rfi_by_date if start <= d <= end)
        if window > event_days and event_days > 0:
            events_result.append({
                "name": name,
                "verdict": "SKIP",
                "reason": f"window={window} > event_days={event_days}",
            })
            continue

        # Filter RFI to event window
        points = [d for d in rfi_series if start <= d["date"] <= end]
        if not points:
            events_result.append({
                "name": name,
                "verdict": "SKIP",
                "reason": "no data in date range",
            })
            continue

        rfis = [p["rfi"] for p in points]
        phases = {p["phase"] for p in points}
        avg_rfi = sum(rfis) / len(rfis)
        min_rfi = min(rfis)
        max_rfi = max(rfis)

        # Check sign
        if expected_sign == "negative":
            if lenient:
                sign_ok = min_rfi < 0
            else:
                sign_ok = avg_rfi < 0
            extreme = min_rfi
        else:
            if lenient:
                sign_ok = max_rfi > 0
            else:
                sign_ok = avg_rfi > 0
            extreme = max_rfi

        # Check phases
        phase_ok = bool(phases & expected_phases)
        signal_strength = abs(extreme) > 0.1

        if sign_ok and phase_ok:
            verdict = "PASS"
        elif sign_ok or phase_ok:
            verdict = "WARN"
        else:
            verdict = "FAIL"

        if not signal_strength and verdict == "PASS":
            verdict = "WARN"

        verdicts.append(verdict)
        events_result.append({
            "name": name,
            "verdict": verdict,
            "avg_rfi": round(avg_rfi, 4),
            "min_rfi": round(min_rfi, 4),
            "max_rfi": round(max_rfi, 4),
            "extreme_rfi": round(extreme, 4),
            "phases_seen": sorted(phases),
            "n_points": len(points),
        })

    # Overall: FAIL if any FAIL, WARN if any WARN, else PASS
    active = [v for v in verdicts]
    if "FAIL" in active:
        overall = "FAIL"
    elif "WARN" in active:
        overall = "WARN"
    elif active:
        overall = "PASS"
    else:
        overall = "SKIP"

    return {"verdict": overall, "events": events_result}


# ---------------------------------------------------------------------------
# Check 2: VIX correlation
# ---------------------------------------------------------------------------

def check_vix_correlation(
    rfi_series: List[Dict[str, Any]],
    vix_history: Dict[str, float],
) -> Dict[str, Any]:
    """Compute Spearman correlation between daily RFI and VIX."""
    from scipy.stats import spearmanr

    # Align on common dates
    rfi_by_date = {d["date"]: d["rfi"] for d in rfi_series}
    common_dates = sorted(set(rfi_by_date.keys()) & set(vix_history.keys()))

    if len(common_dates) < 30:
        return {
            "verdict": "SKIP",
            "reason": f"insufficient aligned data ({len(common_dates)} points, need 30+)",
        }

    rfi_vals = [rfi_by_date[d] for d in common_dates]
    vix_vals = [vix_history[d] for d in common_dates]

    r, p = spearmanr(rfi_vals, vix_vals)
    r = float(r)
    p = float(p)

    # Rolling 60-day correlation
    rfi_s = pd.Series(rfi_vals, index=common_dates)
    vix_s = pd.Series(vix_vals, index=common_dates)
    rolling_corr = rfi_s.rolling(60).corr(vix_s).dropna()
    rolling_stats = {
        "mean": round(float(rolling_corr.mean()), 4),
        "std": round(float(rolling_corr.std()), 4),
        "min": round(float(rolling_corr.min()), 4),
        "max": round(float(rolling_corr.max()), 4),
    } if len(rolling_corr) > 0 else None

    # Verdict
    if p >= 0.05:
        verdict = "FAIL"
        interpretation = "correlation not statistically significant"
    elif r > 0:
        verdict = "FAIL"
        interpretation = "wrong sign — RFI and VIX positively correlated"
    elif r > -0.2:
        verdict = "WARN"
        interpretation = "too weak — RFI may not capture risk sentiment"
    elif r < -0.7:
        verdict = "WARN"
        interpretation = "too strong — RFI may be redundant with VIX"
    else:
        verdict = "PASS"
        interpretation = "moderate negative correlation — captures risk sentiment, not redundant"

    return {
        "verdict": verdict,
        "spearman_r": round(r, 4),
        "p_value": round(p, 6),
        "n_points": len(common_dates),
        "interpretation": interpretation,
        "rolling_60d": rolling_stats,
    }


# ---------------------------------------------------------------------------
# Check 3: Phase transition sequence
# ---------------------------------------------------------------------------

def check_phase_transitions(
    rfi_series: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate phase transition sequences."""
    transitions: List[Dict[str, str]] = []
    invalid: List[Dict[str, str]] = []
    matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    phase_durations: List[int] = []

    prev_phase: Optional[str] = None
    streak = 0

    for point in rfi_series:
        phase = point["phase"]
        if prev_phase is None:
            prev_phase = phase
            streak = 1
            continue

        if phase != prev_phase:
            phase_durations.append(streak)
            trans = {"date": point["date"], "from": prev_phase, "to": phase}
            transitions.append(trans)
            matrix[prev_phase][phase] += 1

            valid_targets = VALID_TRANSITIONS.get(prev_phase, set())
            if phase not in valid_targets:
                invalid.append(trans)

            prev_phase = phase
            streak = 1
        else:
            streak += 1

    if streak > 0:
        phase_durations.append(streak)

    total = len(transitions)
    n_invalid = len(invalid)
    invalid_rate = n_invalid / total if total > 0 else 0.0
    n_days = len(rfi_series)
    monthly_rate = (total / n_days * 22) if n_days > 0 else 0.0
    avg_duration = sum(phase_durations) / len(phase_durations) if phase_durations else 0.0

    # Verdict
    if invalid_rate > 0.15 or monthly_rate > 8:
        verdict = "FAIL"
    elif invalid_rate > 0.05 or monthly_rate > 4:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "verdict": verdict,
        "total_transitions": total,
        "invalid_transitions": n_invalid,
        "invalid_rate": round(invalid_rate, 4),
        "monthly_rate": round(monthly_rate, 2),
        "avg_phase_duration_days": round(avg_duration, 1),
        "transition_matrix": {k: dict(v) for k, v in matrix.items()},
        "invalid_examples": invalid[:10],
    }


# ---------------------------------------------------------------------------
# Check 4: RFI-phase consistency
# ---------------------------------------------------------------------------

def check_rfi_phase_consistency(
    rfi_series: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Check RFI value matches phase semantics per snapshot."""
    # Read thresholds from config
    rfi_risk_on = RFI_RISK_ON         # 0.3
    rfi_mild_off = RFI_MILD_RISK_OFF  # -0.3

    consistency_rules = {
        "outflow":    lambda rfi: rfi == 0.0,
        "riskon":     lambda rfi: rfi > rfi_risk_on,
        "deleverage": lambda rfi: rfi < rfi_mild_off,
        "bottom":     lambda rfi: 0 < rfi <= rfi_risk_on,
        "normal":     lambda rfi: abs(rfi) <= rfi_risk_on,
    }

    per_phase: Dict[str, Dict[str, int]] = defaultdict(lambda: {"ok": 0, "bad": 0})
    rfi_by_phase: Dict[str, List[float]] = defaultdict(list)
    inconsistent: List[Dict[str, Any]] = []

    for point in rfi_series:
        phase = point["phase"]
        rfi = point["rfi"]
        rfi_by_phase[phase].append(rfi)

        rule = consistency_rules.get(phase)
        if rule is None:
            per_phase[phase]["ok"] += 1
            continue

        if rule(rfi):
            per_phase[phase]["ok"] += 1
        else:
            per_phase[phase]["bad"] += 1
            if len(inconsistent) < 10:
                inconsistent.append({
                    "date": point["date"],
                    "phase": phase,
                    "rfi": rfi,
                    "risk_net": point["risk_net"],
                    "safe_net": point["safe_net"],
                })

    total_ok = sum(v["ok"] for v in per_phase.values())
    total_bad = sum(v["bad"] for v in per_phase.values())
    total = total_ok + total_bad
    overall_rate = total_ok / total if total > 0 else 0.0

    # Per-phase stats
    phase_stats = {}
    for phase in sorted(rfi_by_phase.keys()):
        vals = rfi_by_phase[phase]
        counts = per_phase[phase]
        phase_total = counts["ok"] + counts["bad"]
        phase_stats[phase] = {
            "consistency": round(counts["ok"] / phase_total, 4) if phase_total > 0 else 1.0,
            "count": phase_total,
            "rfi_mean": round(float(np.mean(vals)), 4),
            "rfi_std": round(float(np.std(vals)), 4),
            "rfi_min": round(float(np.min(vals)), 4),
            "rfi_max": round(float(np.max(vals)), 4),
        }

    if overall_rate >= 0.90:
        verdict = "PASS"
    elif overall_rate >= 0.75:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    return {
        "verdict": verdict,
        "overall_consistency": round(overall_rate, 4),
        "per_phase": phase_stats,
        "inconsistent_examples": inconsistent,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _overall_verdict(checks: Dict[str, Dict[str, Any]]) -> str:
    verdicts = [c.get("verdict", "SKIP") for c in checks.values()]
    if "FAIL" in verdicts:
        return "FAIL"
    if "WARN" in verdicts:
        return "WARN"
    if all(v == "SKIP" for v in verdicts):
        return "SKIP"
    return "PASS"


def _print_summary(report: Dict[str, Any]) -> None:
    """Print formatted console summary."""
    W = 60
    print("=" * W)
    print("RFI Validation Report")
    print("=" * W)
    s = report["rfi_series_summary"]
    print(f"Data range: {s['start']} to {s['end']} ({s['count']} trading days)")
    print(f"RFI window: {report['rfi_window']} trading days")
    print()

    checks = report["checks"]
    labels = [
        ("event_sanity", "Event Sanity Check"),
        ("vix_correlation", "VIX Correlation Check"),
        ("phase_transitions", "Phase Transition Sequence Check"),
        ("rfi_phase_consistency", "RFI-Phase Consistency Check"),
    ]

    for i, (key, label) in enumerate(labels, 1):
        check = checks[key]
        v = check["verdict"]
        dots = "." * (W - len(f"[{i}/4] {label}  {v}"))
        print(f"[{i}/4] {label} {dots} {v}")

        if key == "event_sanity":
            for ev in check.get("events", []):
                name = ev["name"]
                v2 = ev["verdict"]
                if v2 == "SKIP":
                    print(f"  {name:38s} SKIP ({ev.get('reason', '')})")
                else:
                    avg = ev.get("avg_rfi", 0)
                    phases = ", ".join(ev.get("phases_seen", []))
                    print(f"  {name:38s} {v2} (avg RFI {avg:+.2f}, phases: {phases})")
        elif key == "vix_correlation":
            if check["verdict"] != "SKIP":
                r = check["spearman_r"]
                p = check["p_value"]
                n = check["n_points"]
                print(f"  Spearman r = {r:.4f} (p = {p:.4f}, n={n})")
                print(f"  {check.get('interpretation', '')}")
                rs = check.get("rolling_60d")
                if rs:
                    print(f"  Rolling 60d: mean={rs['mean']:.2f}, range=[{rs['min']:.2f}, {rs['max']:.2f}]")
            else:
                print(f"  {check.get('reason', '')}")
        elif key == "phase_transitions":
            print(f"  {check['total_transitions']} transitions over {s['count']} days "
                  f"({check['monthly_rate']:.1f}/month)")
            print(f"  Invalid: {check['invalid_transitions']} ({check['invalid_rate']:.1%})")
            print(f"  Avg phase duration: {check['avg_phase_duration_days']:.1f} days")
        elif key == "rfi_phase_consistency":
            print(f"  Overall consistency: {check['overall_consistency']:.1%}")
            for phase, ps in check.get("per_phase", {}).items():
                print(f"  {phase:12s} {ps['consistency']:.0%} "
                      f"(n={ps['count']}, RFI mean={ps['rfi_mean']:+.2f})")
        print()

    print("=" * W)
    print(f"Overall Verdict: {report['overall_verdict']}")
    n_pass = sum(1 for k, _ in labels if checks[k]["verdict"] == "PASS")
    n_total = len(labels)
    print(f"  ({n_pass}/{n_total} checks passed)")
    print("=" * W)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    window: int = 5,
    fetch_vix: bool = True,
    export: bool = True,
) -> Dict[str, Any]:
    """Run all RFI validation checks."""
    log.info("Loading capital flow ETF data from collected/...")
    etf_prices = load_capital_flow_etfs_from_collected(lookback_weeks=200)
    log.info(f"Loaded {len(etf_prices)} tickers")

    # Reconstruct daily RFI
    rfi_series = _compute_daily_rfi_series(etf_prices, window)
    if not rfi_series:
        log.error("No RFI data reconstructed — aborting")
        return {"overall_verdict": "FAIL", "error": "no data"}

    # RFI summary
    rfis = [d["rfi"] for d in rfi_series]
    phase_dist = dict(Counter(d["phase"] for d in rfi_series))
    rfi_summary = {
        "start": rfi_series[0]["date"],
        "end": rfi_series[-1]["date"],
        "count": len(rfi_series),
        "mean": round(float(np.mean(rfis)), 4),
        "std": round(float(np.std(rfis)), 4),
        "min": round(float(np.min(rfis)), 4),
        "max": round(float(np.max(rfis)), 4),
        "phase_distribution": phase_dist,
    }

    # Check 1: Event sanity
    log.info("Running Check 1: Event Sanity...")
    c1 = check_event_sanity(rfi_series, window)

    # Check 2: VIX correlation
    if fetch_vix:
        log.info("Running Check 2: VIX Correlation...")
        vix = _fetch_vix_history(rfi_series[0]["date"], rfi_series[-1]["date"])
        c2 = check_vix_correlation(rfi_series, vix)
    else:
        c2 = {"verdict": "SKIP", "reason": "VIX fetch disabled (--no-fetch-vix)"}

    # Check 3: Phase transitions
    log.info("Running Check 3: Phase Transitions...")
    c3 = check_phase_transitions(rfi_series)

    # Check 4: RFI-phase consistency
    log.info("Running Check 4: RFI-Phase Consistency...")
    c4 = check_rfi_phase_consistency(rfi_series)

    checks = {
        "event_sanity": c1,
        "vix_correlation": c2,
        "phase_transitions": c3,
        "rfi_phase_consistency": c4,
    }

    report = {
        "date": rfi_series[-1]["date"],
        "rfi_window": window,
        "overall_verdict": _overall_verdict(checks),
        "rfi_series_summary": rfi_summary,
        "checks": checks,
    }

    _print_summary(report)

    if export:
        out_path = os.path.join("output", "rfi_validation.json")
        os.makedirs("output", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
        log.info(f"Report exported to {out_path}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RFI Validation Harness")
    parser.add_argument("--window", type=int, default=5,
                        help="RFI rolling window in trading days (default: 5)")
    parser.add_argument("--no-fetch-vix", action="store_true",
                        help="Skip yfinance VIX fetch")
    parser.add_argument("--no-export", action="store_true",
                        help="Console only, no JSON export")
    args = parser.parse_args()
    run(window=args.window, fetch_vix=not args.no_fetch_vix, export=not args.no_export)
