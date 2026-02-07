"""Leading indicators for market turn detection.

Computes 4 forward-looking signals from existing collected data:

1. VIX Term Structure   — ^VIX / ^VIX3M ratio (contango/backwardation)
2. Credit Spread Velocity — d/dt(LQD/TLT) rate-of-change
3. RFI Acceleration     — second derivative of Risk Flow Index
4. Breadth Thrust       — % of sectors flipping from downtrend to uptrend
"""

from __future__ import annotations

import json
import os
from typing import Any

from engine.config import (
    OUTPUT_DIR,
    TREND_STRONG_UPTREND,
    TREND_UPTREND,
    TREND_NEUTRAL,
    TREND_DOWNTREND,
)
from engine.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_json(filename: str) -> Any:
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_cf_etf_prices() -> dict[str, dict[str, float]]:
    """Load capital flow ETF daily close prices from collected/."""
    from engine.collect import iter_date_dirs
    prices: dict[str, dict[str, float]] = {}
    for date_str, dir_path in iter_date_dirs():
        cf_path = os.path.join(dir_path, "capital_flow_etfs.json")
        if not os.path.exists(cf_path):
            continue
        try:
            with open(cf_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            day: dict[str, float] = {}
            for ticker, etf_data in data.items():
                if isinstance(etf_data, dict):
                    close = etf_data.get("Close") or etf_data.get("close")
                    if close is not None:
                        day[ticker] = float(close)
            if day:
                prices[date_str] = day
        except Exception:
            continue
    return prices


def _load_macro_history() -> dict[str, dict]:
    """Load macro.json from collected/ for VIX history."""
    from engine.collect import iter_date_dirs
    result: dict[str, dict] = {}
    for date_str, dir_path in iter_date_dirs():
        p = os.path.join(dir_path, "macro.json")
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                result[date_str] = json.load(f)
        except Exception:
            continue
    return result


# ---------------------------------------------------------------------------
# 1. VIX Term Structure
# ---------------------------------------------------------------------------

def compute_vix_term_structure(macro_history: dict[str, dict]) -> list[dict]:
    """Compute VIX term structure ratio from collected macro data.

    Requires both 'vix' and 'vix3m' fields. If only 'vix' is available,
    returns empty (insufficient data).

    Returns list of {date, vix, vix3m, ratio, signal}.
    """
    results = []
    for date_str in sorted(macro_history.keys()):
        m = macro_history[date_str]
        vix = m.get("vix")
        vix3m = m.get("vix3m")
        if vix is None or vix3m is None or vix3m == 0:
            continue
        ratio = round(vix / vix3m, 4)
        # ratio > 1.0 = backwardation (fear), < 1.0 = contango (complacency)
        if ratio > 1.05:
            signal = "backwardation"  # peak fear — often precedes rebounds
        elif ratio < 0.85:
            signal = "deep_contango"  # extreme complacency — risk of correction
        elif ratio < 0.95:
            signal = "contango"
        else:
            signal = "neutral"
        results.append({
            "date": date_str,
            "vix": round(vix, 2),
            "vix3m": round(vix3m, 2),
            "ratio": ratio,
            "signal": signal,
        })
    return results


# ---------------------------------------------------------------------------
# 2. Credit Spread Velocity
# ---------------------------------------------------------------------------

def compute_credit_spread_velocity(
    cf_prices: dict[str, dict[str, float]],
    windows: list[int] | None = None,
) -> list[dict]:
    """Compute LQD/TLT ratio and its rate-of-change.

    LQD = investment-grade corporate bonds, TLT = long-term Treasuries.
    Rising LQD/TLT = credit tightening (risk-off).
    Falling LQD/TLT = credit easing (risk-on).
    Velocity = d/dt of the ratio — leads equity turns by days.

    Args:
        cf_prices: {date: {ticker: close}}
        windows: ROC windows in trading days (default [5, 10])

    Returns list of {date, lqd_tlt_ratio, velocity_5d, velocity_10d, signal}.
    """
    if windows is None:
        windows = [5, 10]

    sorted_dates = sorted(cf_prices.keys())
    ratios: list[tuple[str, float]] = []

    for d in sorted_dates:
        lqd = cf_prices[d].get("LQD")
        tlt = cf_prices[d].get("TLT")
        if lqd is not None and tlt is not None and tlt > 0:
            ratios.append((d, lqd / tlt))

    if len(ratios) < max(windows) + 1:
        return []

    results = []
    for i in range(max(windows), len(ratios)):
        d, r = ratios[i]
        entry: dict[str, Any] = {
            "date": d,
            "lqd_tlt_ratio": round(r, 6),
        }
        for w in windows:
            prev_r = ratios[i - w][1]
            if prev_r > 0:
                velocity = (r - prev_r) / prev_r
                entry[f"velocity_{w}d"] = round(velocity, 6)
            else:
                entry[f"velocity_{w}d"] = None

        # Signal: fast velocity direction
        v5 = entry.get("velocity_5d")
        v10 = entry.get("velocity_10d")
        if v5 is not None and v10 is not None:
            if v5 < -0.01 and v10 < -0.01:
                entry["signal"] = "credit_easing"   # bullish for equities
            elif v5 > 0.01 and v10 > 0.01:
                entry["signal"] = "credit_tightening"  # bearish for equities
            elif v5 > 0.005 and v10 < 0:
                entry["signal"] = "tightening_reversal"  # was easing, now tightening
            elif v5 < -0.005 and v10 > 0:
                entry["signal"] = "easing_reversal"  # was tightening, now easing
            else:
                entry["signal"] = "neutral"
        else:
            entry["signal"] = "neutral"

        results.append(entry)

    return results


# ---------------------------------------------------------------------------
# 3. RFI Acceleration
# ---------------------------------------------------------------------------

def compute_rfi_acceleration(capital_flows: dict) -> list[dict]:
    """Compute RFI velocity (1st derivative) and acceleration (2nd derivative).

    Reads phase timeline from capital_flows.json.
    RFI = (risk_net - safe_net) / (|risk_net| + |safe_net|).

    Returns list of {date, rfi, rfi_velocity, rfi_acceleration, signal}.
    """
    windows = capital_flows.get("windows", {})
    window_data = windows.get("1W", {})
    phases = window_data.get("phases", [])

    if len(phases) < 3:
        return []

    # Extract RFI series
    rfi_series: list[tuple[str, float]] = []
    for p in phases:
        rfi = p.get("rfi")
        if rfi is None:
            risk_net = p.get("risk_net", 0)
            safe_net = p.get("safe_net", 0)
            total = abs(risk_net) + abs(safe_net)
            rfi = (risk_net - safe_net) / total if total > 0.5 else 0.0
        rfi_series.append((p.get("date", ""), float(rfi)))

    results = []
    for i in range(2, len(rfi_series)):
        d, rfi = rfi_series[i]
        _, rfi_prev = rfi_series[i - 1]
        _, rfi_prev2 = rfi_series[i - 2]

        velocity = rfi - rfi_prev
        acceleration = velocity - (rfi_prev - rfi_prev2)

        # Signal classification
        if acceleration > 0.15 and velocity > 0:
            signal = "strong_improving"  # capital rushing into risk
        elif acceleration > 0.05 and velocity > 0:
            signal = "improving"
        elif acceleration < -0.15 and velocity < 0:
            signal = "strong_deteriorating"  # capital fleeing risk fast
        elif acceleration < -0.05 and velocity < 0:
            signal = "deteriorating"
        elif acceleration > 0.05 and velocity < 0:
            signal = "bottoming"  # deceleration of outflow — possible turn
        elif acceleration < -0.05 and velocity > 0:
            signal = "topping"   # deceleration of inflow — possible turn
        else:
            signal = "neutral"

        results.append({
            "date": d,
            "rfi": round(rfi, 4),
            "rfi_velocity": round(velocity, 4),
            "rfi_acceleration": round(acceleration, 4),
            "signal": signal,
        })

    return results


# ---------------------------------------------------------------------------
# 4. Breadth Thrust
# ---------------------------------------------------------------------------

def _classify_trend(score: float | None) -> str:
    """Classify trend state matching the canonical 5-bucket classifier in trend_scorer."""
    if score is None:
        return "neutral"
    if score >= TREND_STRONG_UPTREND:
        return "strong_uptrend"
    if score >= TREND_UPTREND:
        return "uptrend"
    if score >= TREND_NEUTRAL:
        return "neutral"
    if score >= TREND_DOWNTREND:
        return "downtrend"
    return "strong_downtrend"


def compute_breadth_thrust(
    trend_history: dict,
    window: int = 22,
) -> list[dict]:
    """Compute breadth thrust: rate of sectors flipping into uptrend.

    Breadth thrust = (# sectors in uptrend today - # sectors in uptrend N days ago)
    normalized by total sector count.

    A rapid increase in the percentage of sectors trending up signals a
    broad-based reversal — historically the strongest momentum signal.

    Args:
        trend_history: {date: {sector: {trend_strength, trend_state, ...}}}
        window: lookback in trading days for thrust computation.

    Returns list of {date, pct_uptrend, pct_downtrend, thrust, signal}.
    """
    sorted_dates = sorted(trend_history.keys())
    if len(sorted_dates) < window + 1:
        return []

    # Pre-compute daily breadth
    daily_breadth: list[tuple[str, int, int, int]] = []
    for d in sorted_dates:
        sectors = trend_history[d]
        total = 0
        up = 0
        down = 0
        for sec_data in sectors.values():
            ts = sec_data.get("trend_state")
            if ts is None:
                strength = sec_data.get("trend_strength")
                rs = sec_data.get("rs_score")
                mom = sec_data.get("momentum_score")
                if strength is not None:
                    ts = _classify_trend(strength)
                elif rs is not None and mom is not None:
                    approx = 0.6 * rs + 0.4 * mom
                    ts = _classify_trend(approx)
                else:
                    ts = "neutral"
            total += 1
            if ts in ("uptrend", "strong_uptrend"):
                up += 1
            elif ts in ("downtrend", "strong_downtrend"):
                down += 1
        daily_breadth.append((d, up, down, total))

    results = []
    for i in range(window, len(daily_breadth)):
        d, up, down, total = daily_breadth[i]
        _, up_prev, down_prev, total_prev = daily_breadth[i - window]

        if total == 0:
            continue

        pct_up = up / total
        pct_down = down / total

        # Thrust = change in % uptrend over window
        pct_up_prev = up_prev / total_prev if total_prev > 0 else 0
        thrust = pct_up - pct_up_prev

        # Signal classification
        if thrust >= 0.36:  # 4+ sectors flipped to uptrend (out of 11)
            signal = "strong_thrust"
        elif thrust >= 0.18:  # 2+ sectors flipped
            signal = "thrust"
        elif thrust <= -0.36:
            signal = "strong_collapse"
        elif thrust <= -0.18:
            signal = "collapse"
        else:
            signal = "neutral"

        results.append({
            "date": d,
            "pct_uptrend": round(pct_up, 4),
            "pct_downtrend": round(pct_down, 4),
            "sectors_uptrend": up,
            "sectors_downtrend": down,
            "sectors_total": total,
            "thrust": round(thrust, 4),
            "signal": signal,
        })

    return results


# ---------------------------------------------------------------------------
# Composite: compute all indicators + export
# ---------------------------------------------------------------------------

def compute_leading_indicators() -> dict:
    """Compute all available leading indicators from existing data.

    Returns dict with indicator results for export.
    """
    log.info("Computing leading indicators...")

    # Load data
    cf_prices = _load_cf_etf_prices()
    capital_flows = _load_json("capital_flows.json")
    trend_history = _load_json("trend_history.json")
    macro_history = _load_macro_history()

    result: dict[str, Any] = {}

    # 1. VIX Term Structure
    vix_ts = compute_vix_term_structure(macro_history)
    result["vix_term_structure"] = {
        "data": vix_ts[-60:] if vix_ts else [],  # last 60 entries
        "count": len(vix_ts),
        "available": len(vix_ts) > 0,
    }
    log.info(f"  VIX term structure: {len(vix_ts)} data points")

    # 2. Credit Spread Velocity
    csv_data = compute_credit_spread_velocity(cf_prices) if cf_prices else []
    result["credit_spread"] = {
        "data": csv_data[-120:] if csv_data else [],  # last ~6 months
        "count": len(csv_data),
        "available": len(csv_data) > 0,
    }
    if csv_data:
        latest = csv_data[-1]
        log.info(f"  Credit spread: {len(csv_data)} data points, "
                 f"latest signal={latest['signal']}, "
                 f"LQD/TLT={latest['lqd_tlt_ratio']:.4f}")
    else:
        log.info("  Credit spread: no data")

    # 3. RFI Acceleration
    rfi_acc = compute_rfi_acceleration(capital_flows) if capital_flows else []
    result["rfi_acceleration"] = {
        "data": rfi_acc,
        "count": len(rfi_acc),
        "available": len(rfi_acc) > 0,
    }
    if rfi_acc:
        latest = rfi_acc[-1]
        log.info(f"  RFI acceleration: {len(rfi_acc)} data points, "
                 f"latest signal={latest['signal']}, "
                 f"accel={latest['rfi_acceleration']:.4f}")
    else:
        log.info("  RFI acceleration: no data")

    # 4. Breadth Thrust
    bt = compute_breadth_thrust(trend_history) if trend_history else []
    result["breadth_thrust"] = {
        "data": bt[-120:] if bt else [],  # last ~6 months
        "count": len(bt),
        "available": len(bt) > 0,
    }
    if bt:
        latest = bt[-1]
        log.info(f"  Breadth thrust: {len(bt)} data points, "
                 f"latest signal={latest['signal']}, "
                 f"thrust={latest['thrust']:+.4f}, "
                 f"{latest['sectors_uptrend']}/{latest['sectors_total']} sectors up")
    else:
        log.info("  Breadth thrust: no data")

    return result


def export_leading_indicators(indicators: dict, run_date: str) -> str:
    """Export leading_indicators.json for the frontend."""
    from engine.exporters.json_exporter import NumpyEncoder

    data = {
        "date": run_date,
        "indicators": indicators,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "leading_indicators.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NumpyEncoder, ensure_ascii=False,
                  indent=None, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    log.info(f"Wrote {path} ({size_kb:.1f} KB)")
    return path
