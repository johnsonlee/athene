"""Signal backtesting framework.

Reads historical data from trend_history.json, capital_flows.json, and
collected/ ETF price archives to validate signal predictiveness.

For each signal type, computes:
  - Entry events (when the signal fires)
  - Forward returns at 5d / 10d / 22d horizons
  - Hit rate, average return, max drawdown, sample count

Usage:
    python -m engine.backtest           # Run all backtests
    python -m engine.backtest --signal sector_trend   # Specific signal
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from typing import Any

from engine.config import (
    OUTPUT_DIR,
    SECTOR_ETFS,
    TREND_STRONG_UPTREND,
    TREND_UPTREND,
    TREND_NEUTRAL,
    TREND_DOWNTREND,
)
from engine.exporters.json_exporter import NumpyEncoder
from engine.utils.logger import get_logger

log = get_logger("athene.backtest")

FORWARD_HORIZONS = [5, 10, 22]  # trading days


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_json(filename: str) -> Any:
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_etf_price_series() -> dict[str, dict[str, float]]:
    """Load SPY daily close prices from collected/ for forward return computation.

    Returns: { date_str: { etf_ticker: close_price } }
    """
    from engine.collect import iter_date_dirs, read_per_ticker

    prices: dict[str, dict[str, float]] = {}

    for date_str, dir_path in iter_date_dirs():
        try:
            data = read_per_ticker("sector_etfs", dir_path)
            if not data:
                continue
            day_prices: dict[str, float] = {}
            for ticker, etf_data in data.items():
                if isinstance(etf_data, dict):
                    close = etf_data.get("Close") or etf_data.get("close")
                    if close is not None:
                        day_prices[ticker] = float(close)
            if day_prices:
                prices[date_str] = day_prices
        except Exception:
            continue

    return prices


def _load_capital_flow_etf_prices() -> dict[str, dict[str, float]]:
    """Load capital flow ETF daily close prices from collected/.

    Returns: { date_str: { etf_ticker: close_price } }
    """
    from engine.collect import iter_date_dirs, read_per_ticker

    prices: dict[str, dict[str, float]] = {}

    for date_str, dir_path in iter_date_dirs():
        try:
            data = read_per_ticker("capital_flow_etfs", dir_path)
            if not data:
                continue
            day_prices: dict[str, float] = {}
            for ticker, etf_data in data.items():
                if isinstance(etf_data, dict):
                    close = etf_data.get("Close") or etf_data.get("close")
                    if close is not None:
                        day_prices[ticker] = float(close)
            if day_prices:
                prices[date_str] = day_prices
        except Exception:
            continue

    return prices


# ---------------------------------------------------------------------------
# Forward return computation
# ---------------------------------------------------------------------------

def _compute_forward_returns(
    entry_date: str,
    sorted_dates: list[str],
    price_series: dict[str, float],
    horizons: list[int] | None = None,
) -> dict[str, float | None]:
    """Compute forward returns from entry_date for given horizons.

    Args:
        entry_date: The signal date.
        sorted_dates: All available dates sorted ascending.
        price_series: { date: close_price } for the benchmark.
        horizons: List of forward trading day offsets.

    Returns:
        { "fwd_5d": 0.023, "fwd_10d": 0.041, ... } or None if data missing.
    """
    if horizons is None:
        horizons = FORWARD_HORIZONS

    if entry_date not in price_series:
        return {f"fwd_{h}d": None for h in horizons}

    entry_price = price_series[entry_date]
    if entry_price == 0:
        return {f"fwd_{h}d": None for h in horizons}

    try:
        idx = sorted_dates.index(entry_date)
    except ValueError:
        return {f"fwd_{h}d": None for h in horizons}

    result: dict[str, float | None] = {}
    for h in horizons:
        target_idx = idx + h
        if target_idx < len(sorted_dates):
            target_date = sorted_dates[target_idx]
            target_price = price_series.get(target_date)
            if target_price is not None and target_price > 0:
                result[f"fwd_{h}d"] = round((target_price - entry_price) / entry_price, 6)
            else:
                result[f"fwd_{h}d"] = None
        else:
            result[f"fwd_{h}d"] = None

    return result


def _compute_max_drawdown(
    entry_date: str,
    sorted_dates: list[str],
    price_series: dict[str, float],
    window: int = 22,
) -> float | None:
    """Compute max drawdown from entry_date over next N trading days."""
    if entry_date not in price_series:
        return None

    entry_price = price_series[entry_date]
    if entry_price == 0:
        return None

    try:
        idx = sorted_dates.index(entry_date)
    except ValueError:
        return None

    peak = entry_price
    max_dd = 0.0

    for i in range(1, window + 1):
        target_idx = idx + i
        if target_idx >= len(sorted_dates):
            break
        price = price_series.get(sorted_dates[target_idx])
        if price is None:
            continue
        peak = max(peak, price)
        dd = (peak - price) / peak
        max_dd = max(max_dd, dd)

    return round(max_dd, 6) if max_dd > 0 else 0.0


# ---------------------------------------------------------------------------
# Signal: Sector trend state transitions
# ---------------------------------------------------------------------------

_TREND_STATE_RANK = {
    "strong_downtrend": 0,
    "downtrend": 1,
    "neutral": 2,
    "uptrend": 3,
    "strong_uptrend": 4,
}


def _classify_trend_state(score: float | None) -> str:
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


def backtest_sector_trends(
    trend_history: dict,
    etf_prices: dict[str, dict[str, float]],
) -> list[dict]:
    """Backtest sector trend state transitions.

    Signals:
    - upgrade: sector moves to a higher trend state
    - downgrade: sector moves to a lower trend state

    Benchmark: sector ETF forward returns.
    """
    results = []

    # Map sector -> ETF ticker
    sector_to_etf = {v: k for k, v in SECTOR_ETFS.items()}

    sorted_dates = sorted(trend_history.keys())
    if len(sorted_dates) < 2:
        return results

    sectors = set()
    for daily in trend_history.values():
        sectors.update(daily.keys())

    for sector in sorted(sectors):
        etf_ticker = sector_to_etf.get(sector)
        if not etf_ticker:
            continue

        # Build price series for this ETF
        etf_price_series: dict[str, float] = {}
        for date_str, day_prices in etf_prices.items():
            if etf_ticker in day_prices:
                etf_price_series[date_str] = day_prices[etf_ticker]

        price_dates = sorted(etf_price_series.keys())
        if not price_dates:
            continue

        prev_state: str | None = None
        for date_str in sorted_dates:
            daily = trend_history.get(date_str, {})
            sector_data = daily.get(sector, {})

            # Determine trend state from the data
            if "trend_state" in sector_data:
                state = sector_data["trend_state"]
            elif "rs_score" in sector_data and "momentum_score" in sector_data:
                # Approximate trend strength from RS + momentum
                rs = sector_data.get("rs_score", 50)
                mom = sector_data.get("momentum_score", 50)
                if rs is not None and mom is not None:
                    approx_strength = 0.6 * rs + 0.4 * mom
                    state = _classify_trend_state(approx_strength)
                else:
                    state = "neutral"
            else:
                prev_state = None
                continue

            if prev_state is not None and state != prev_state:
                old_rank = _TREND_STATE_RANK.get(prev_state, 2)
                new_rank = _TREND_STATE_RANK.get(state, 2)

                if new_rank > old_rank:
                    direction = "upgrade"
                else:
                    direction = "downgrade"

                transition = f"{prev_state} -> {state}"

                fwd = _compute_forward_returns(
                    date_str, price_dates, etf_price_series,
                )
                max_dd = _compute_max_drawdown(
                    date_str, price_dates, etf_price_series,
                )

                results.append({
                    "signal": "sector_trend_transition",
                    "direction": direction,
                    "transition": transition,
                    "sector": sector,
                    "etf": etf_ticker,
                    "date": date_str,
                    **fwd,
                    "max_drawdown_22d": max_dd,
                })

            prev_state = state

    return results


# ---------------------------------------------------------------------------
# Signal: Capital flow phase transitions
# ---------------------------------------------------------------------------

_PHASE_RANK = {
    "deleverage": 0,
    "outflow": 1,
    "bottom": 2,
    "normal": 3,
    "riskon": 4,
}


def backtest_capital_flow_phases(
    capital_flows: dict,
    cf_prices: dict[str, dict[str, float]],
) -> list[dict]:
    """Backtest capital flow phase transitions.

    Uses SPY as benchmark for forward returns.
    """
    results = []

    windows = capital_flows.get("windows", {})
    # Use 1W window as primary signal
    window_data = windows.get("1W", {})
    phases = window_data.get("phases", [])

    if len(phases) < 2:
        return results

    # Build SPY price series from capital flow ETF data
    spy_prices: dict[str, float] = {}
    for date_str, day_prices in cf_prices.items():
        if "SPY" in day_prices:
            spy_prices[date_str] = day_prices["SPY"]

    price_dates = sorted(spy_prices.keys())
    if not price_dates:
        # Fallback: try sector ETF data
        return results

    prev_phase: str | None = None
    for phase_entry in phases:
        phase = phase_entry.get("phase", "normal")
        date_str = phase_entry.get("date", "")

        if prev_phase is not None and phase != prev_phase:
            transition = f"{prev_phase} -> {phase}"

            fwd = _compute_forward_returns(date_str, price_dates, spy_prices)
            max_dd = _compute_max_drawdown(date_str, price_dates, spy_prices)

            # Determine signal direction
            old_rank = _PHASE_RANK.get(prev_phase, 3)
            new_rank = _PHASE_RANK.get(phase, 3)
            if new_rank > old_rank:
                direction = "risk_on"
            elif new_rank < old_rank:
                direction = "risk_off"
            else:
                direction = "lateral"

            results.append({
                "signal": "capital_flow_phase",
                "direction": direction,
                "transition": transition,
                "date": date_str,
                **fwd,
                "max_drawdown_22d": max_dd,
                "risk_net": phase_entry.get("risk_net"),
                "safe_net": phase_entry.get("safe_net"),
            })

        prev_phase = phase

    return results


# ---------------------------------------------------------------------------
# Signal: RFI level crossings
# ---------------------------------------------------------------------------

def backtest_rfi_crossings(
    capital_flows: dict,
    cf_prices: dict[str, dict[str, float]],
) -> list[dict]:
    """Backtest RFI (Risk Flow Index) level crossings.

    RFI thresholds: -0.7 (panic), -0.3 (risk_off), 0 (neutral), 0.3 (risk_on)
    """
    results = []

    windows = capital_flows.get("windows", {})
    window_data = windows.get("1W", {})
    phases = window_data.get("phases", [])

    if len(phases) < 2:
        return results

    spy_prices: dict[str, float] = {}
    for date_str, day_prices in cf_prices.items():
        if "SPY" in day_prices:
            spy_prices[date_str] = day_prices["SPY"]

    price_dates = sorted(spy_prices.keys())

    thresholds = [-0.7, -0.3, 0.0, 0.3]

    def _rfi_zone(rfi: float) -> str:
        if rfi < -0.7:
            return "panic"
        if rfi < -0.3:
            return "risk_off"
        if rfi < 0.0:
            return "mild_risk_off"
        if rfi < 0.3:
            return "neutral"
        return "risk_on"

    prev_rfi: float | None = None
    prev_zone: str | None = None

    for phase_entry in phases:
        rfi = phase_entry.get("rfi")
        if rfi is None:
            # Compute RFI from risk_net / safe_net
            risk_net = phase_entry.get("risk_net", 0)
            safe_net = phase_entry.get("safe_net", 0)
            total = abs(risk_net) + abs(safe_net)
            if total > 0.5:
                rfi = (risk_net - safe_net) / total
            else:
                rfi = 0.0

        zone = _rfi_zone(rfi)
        date_str = phase_entry.get("date", "")

        if prev_zone is not None and zone != prev_zone:
            fwd = _compute_forward_returns(date_str, price_dates, spy_prices)
            max_dd = _compute_max_drawdown(date_str, price_dates, spy_prices)

            results.append({
                "signal": "rfi_crossing",
                "direction": f"{prev_zone} -> {zone}",
                "transition": f"{prev_zone} -> {zone}",
                "date": date_str,
                "rfi": round(rfi, 4),
                **fwd,
                "max_drawdown_22d": max_dd,
            })

        prev_rfi = rfi
        prev_zone = zone

    return results


# ---------------------------------------------------------------------------
# Signal: Macro regime transitions
# ---------------------------------------------------------------------------

def backtest_macro_regime(
    etf_prices: dict[str, dict[str, float]],
) -> list[dict]:
    """Backtest macro regime transitions using collected macro.json data.

    Uses SPY forward returns as benchmark.
    """
    results = []

    from engine.collect import iter_date_dirs

    # Load macro data for each date
    macro_by_date: dict[str, dict] = {}
    for date_str, dir_path in iter_date_dirs():
        macro_path = os.path.join(dir_path, "macro.json")
        if not os.path.exists(macro_path):
            continue
        try:
            with open(macro_path, "r", encoding="utf-8") as f:
                macro_by_date[date_str] = json.load(f)
        except (json.JSONDecodeError, Exception):
            continue

    if len(macro_by_date) < 2:
        return results

    # Build SPY price series
    spy_prices: dict[str, float] = {}
    for date_str, day_prices in etf_prices.items():
        if "SPY" in day_prices:
            spy_prices[date_str] = day_prices["SPY"]

    price_dates = sorted(spy_prices.keys())

    def _classify_regime(macro: dict) -> str | None:
        vix = macro.get("vix")
        spy_close = macro.get("sp500_close")
        spy_sma = macro.get("sp500_sma200")

        if vix is None and spy_close is None:
            return None

        signals = []
        if vix is not None:
            if vix < 15:
                signals.append(1)
            elif vix > 25:
                signals.append(-1)
            else:
                signals.append(0)

        if spy_close is not None and spy_sma is not None and spy_sma > 0:
            pct = (spy_close - spy_sma) / spy_sma
            if pct > 0.05:
                signals.append(1)
            elif pct < -0.05:
                signals.append(-1)
            else:
                signals.append(0)

        tnx = macro.get("tnx_yield")
        irx = macro.get("irx_yield")
        if tnx is not None and irx is not None:
            spread = tnx - irx
            if spread > 1.0:
                signals.append(1)
            elif spread < 0:
                signals.append(-1)
            else:
                signals.append(0)

        if not signals:
            return None
        avg = sum(signals) / len(signals)
        if avg > 0.3:
            return "risk_on"
        if avg < -0.3:
            return "risk_off"
        return "neutral"

    sorted_macro_dates = sorted(macro_by_date.keys())
    prev_regime: str | None = None

    for date_str in sorted_macro_dates:
        regime = _classify_regime(macro_by_date[date_str])
        if regime is None:
            continue

        if prev_regime is not None and regime != prev_regime:
            fwd = _compute_forward_returns(date_str, price_dates, spy_prices)
            max_dd = _compute_max_drawdown(date_str, price_dates, spy_prices)

            results.append({
                "signal": "macro_regime",
                "direction": f"{prev_regime} -> {regime}",
                "transition": f"{prev_regime} -> {regime}",
                "date": date_str,
                **fwd,
                "max_drawdown_22d": max_dd,
            })

        prev_regime = regime

    return results


# ---------------------------------------------------------------------------
# Signal: Leading indicator transitions (credit spread, breadth thrust, RFI accel)
# ---------------------------------------------------------------------------

def backtest_credit_spread(
    cf_prices: dict[str, dict[str, float]],
) -> list[dict]:
    """Backtest credit spread velocity signal transitions.

    Uses LQD/TLT ratio velocity to detect credit easing/tightening signals.
    SPY forward returns as benchmark.
    """
    from engine.analyzers.leading_indicators import compute_credit_spread_velocity

    results = []
    csv_data = compute_credit_spread_velocity(cf_prices)
    if len(csv_data) < 2:
        return results

    # Build SPY price series
    spy_prices: dict[str, float] = {}
    for date_str, day_prices in cf_prices.items():
        if "SPY" in day_prices:
            spy_prices[date_str] = day_prices["SPY"]
    price_dates = sorted(spy_prices.keys())
    if not price_dates:
        return results

    prev_signal: str | None = None
    for entry in csv_data:
        signal = entry.get("signal", "neutral")
        date_str = entry["date"]

        if prev_signal is not None and signal != prev_signal and signal != "neutral":
            fwd = _compute_forward_returns(date_str, price_dates, spy_prices)
            max_dd = _compute_max_drawdown(date_str, price_dates, spy_prices)

            results.append({
                "signal": "credit_spread",
                "direction": signal,
                "transition": f"{prev_signal} -> {signal}",
                "date": date_str,
                **fwd,
                "max_drawdown_22d": max_dd,
            })

        prev_signal = signal

    return results


def backtest_breadth_thrust(
    trend_history: dict,
    etf_prices: dict[str, dict[str, float]],
) -> list[dict]:
    """Backtest breadth thrust signal transitions.

    Uses SPY forward returns as benchmark.
    """
    if not trend_history:
        return []

    from engine.analyzers.leading_indicators import compute_breadth_thrust
    results = []
    bt_data = compute_breadth_thrust(trend_history)
    if len(bt_data) < 2:
        return results

    # Build SPY price series
    spy_prices: dict[str, float] = {}
    for date_str, day_prices in etf_prices.items():
        if "SPY" in day_prices:
            spy_prices[date_str] = day_prices["SPY"]
    price_dates = sorted(spy_prices.keys())
    if not price_dates:
        return results

    prev_signal: str | None = None
    for entry in bt_data:
        signal = entry.get("signal", "neutral")
        date_str = entry["date"]

        if prev_signal is not None and signal != prev_signal and signal != "neutral":
            fwd = _compute_forward_returns(date_str, price_dates, spy_prices)
            max_dd = _compute_max_drawdown(date_str, price_dates, spy_prices)

            results.append({
                "signal": "breadth_thrust",
                "direction": signal,
                "transition": f"{prev_signal} -> {signal}",
                "date": date_str,
                "thrust": entry.get("thrust"),
                "pct_uptrend": entry.get("pct_uptrend"),
                **fwd,
                "max_drawdown_22d": max_dd,
            })

        prev_signal = signal

    return results


def backtest_rfi_acceleration(
    capital_flows: dict,
    cf_prices: dict[str, dict[str, float]],
) -> list[dict]:
    """Backtest RFI acceleration signal transitions.

    Uses SPY forward returns as benchmark.
    """
    from engine.analyzers.leading_indicators import compute_rfi_acceleration

    results = []
    rfi_data = compute_rfi_acceleration(capital_flows)
    if len(rfi_data) < 2:
        return results

    # Build SPY price series
    spy_prices: dict[str, float] = {}
    for date_str, day_prices in cf_prices.items():
        if "SPY" in day_prices:
            spy_prices[date_str] = day_prices["SPY"]
    price_dates = sorted(spy_prices.keys())
    if not price_dates:
        return results

    prev_signal: str | None = None
    for entry in rfi_data:
        signal = entry.get("signal", "neutral")
        date_str = entry["date"]

        if prev_signal is not None and signal != prev_signal and signal != "neutral":
            fwd = _compute_forward_returns(date_str, price_dates, spy_prices)
            max_dd = _compute_max_drawdown(date_str, price_dates, spy_prices)

            results.append({
                "signal": "rfi_acceleration",
                "direction": signal,
                "transition": f"{prev_signal} -> {signal}",
                "date": date_str,
                "rfi": entry.get("rfi"),
                "rfi_acceleration": entry.get("rfi_acceleration"),
                **fwd,
                "max_drawdown_22d": max_dd,
            })

        prev_signal = signal

    return results


# ---------------------------------------------------------------------------
# Aggregation: compute stats per signal group
# ---------------------------------------------------------------------------

def _aggregate_stats(events: list[dict]) -> dict:
    """Aggregate backtest events into summary statistics.

    Groups by (signal, direction) and computes per-horizon stats.
    """
    if not events:
        return {"signals": [], "total_events": 0}

    groups: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        key = f"{ev['signal']}|{ev.get('direction', 'all')}"
        groups[key].append(ev)

    signal_stats = []
    for key, group_events in sorted(groups.items()):
        signal_name, direction = key.split("|", 1)

        stats: dict[str, Any] = {
            "signal": signal_name,
            "direction": direction,
            "count": len(group_events),
            "date_range": {
                "first": min(e["date"] for e in group_events),
                "last": max(e["date"] for e in group_events),
            },
            "horizons": {},
        }

        # Collect unique transitions
        transitions: dict[str, int] = defaultdict(int)
        for ev in group_events:
            t = ev.get("transition", "")
            if t:
                transitions[t] += 1
        stats["transitions"] = dict(sorted(transitions.items(), key=lambda x: -x[1]))

        for h in FORWARD_HORIZONS:
            col = f"fwd_{h}d"
            returns = [e[col] for e in group_events if e.get(col) is not None]

            if not returns:
                stats["horizons"][f"{h}d"] = {
                    "count": 0,
                    "hit_rate": None,
                    "avg_return": None,
                    "median_return": None,
                    "std": None,
                    "max_return": None,
                    "min_return": None,
                    "expectancy": None,
                }
                continue

            positive = sum(1 for r in returns if r > 0)
            hit_rate = positive / len(returns)
            avg_ret = statistics.mean(returns)
            med_ret = statistics.median(returns)
            std_ret = statistics.stdev(returns) if len(returns) > 1 else 0.0

            # Expectancy = avg_win * win_rate - avg_loss * loss_rate
            wins = [r for r in returns if r > 0]
            losses = [r for r in returns if r <= 0]
            avg_win = statistics.mean(wins) if wins else 0
            avg_loss = abs(statistics.mean(losses)) if losses else 0
            win_rate = len(wins) / len(returns)
            loss_rate = len(losses) / len(returns)
            expectancy = avg_win * win_rate - avg_loss * loss_rate

            stats["horizons"][f"{h}d"] = {
                "count": len(returns),
                "hit_rate": round(hit_rate, 4),
                "avg_return": round(avg_ret, 6),
                "median_return": round(med_ret, 6),
                "std": round(std_ret, 6),
                "max_return": round(max(returns), 6),
                "min_return": round(min(returns), 6),
                "expectancy": round(expectancy, 6),
            }

        # Max drawdown stats
        drawdowns = [e.get("max_drawdown_22d") for e in group_events
                     if e.get("max_drawdown_22d") is not None]
        if drawdowns:
            stats["max_drawdown"] = {
                "avg": round(statistics.mean(drawdowns), 6),
                "median": round(statistics.median(drawdowns), 6),
                "worst": round(max(drawdowns), 6),
            }
        else:
            stats["max_drawdown"] = {"avg": None, "median": None, "worst": None}

        # Per-sector breakdown for sector_trend signals
        if signal_name == "sector_trend_transition":
            sector_breakdown: dict[str, dict] = {}
            for ev in group_events:
                sector = ev.get("sector", "Unknown")
                if sector not in sector_breakdown:
                    sector_breakdown[sector] = {"count": 0, "returns_5d": [], "returns_22d": []}
                sector_breakdown[sector]["count"] += 1
                r5 = ev.get("fwd_5d")
                r22 = ev.get("fwd_22d")
                if r5 is not None:
                    sector_breakdown[sector]["returns_5d"].append(r5)
                if r22 is not None:
                    sector_breakdown[sector]["returns_22d"].append(r22)

            stats["sectors"] = {}
            for sector, sd in sorted(sector_breakdown.items()):
                r5 = sd["returns_5d"]
                r22 = sd["returns_22d"]
                stats["sectors"][sector] = {
                    "count": sd["count"],
                    "hit_rate_5d": round(sum(1 for r in r5 if r > 0) / len(r5), 4) if r5 else None,
                    "avg_return_5d": round(statistics.mean(r5), 6) if r5 else None,
                    "hit_rate_22d": round(sum(1 for r in r22 if r > 0) / len(r22), 4) if r22 else None,
                    "avg_return_22d": round(statistics.mean(r22), 6) if r22 else None,
                }

        # Recent sample events (last 10 for frontend display)
        sorted_events = sorted(group_events, key=lambda e: e["date"], reverse=True)
        sample_events = []
        for ev in sorted_events[:10]:
            sample = {
                "date": ev["date"],
                "transition": ev.get("transition", ""),
            }
            if "sector" in ev:
                sample["sector"] = ev["sector"]
            if "etf" in ev:
                sample["etf"] = ev["etf"]
            if "rfi" in ev:
                sample["rfi"] = ev["rfi"]
            for h in FORWARD_HORIZONS:
                sample[f"fwd_{h}d"] = ev.get(f"fwd_{h}d")
            sample["max_drawdown_22d"] = ev.get("max_drawdown_22d")
            sample_events.append(sample)
        stats["recent_events"] = sample_events

        signal_stats.append(stats)

    # Sort by count descending
    signal_stats.sort(key=lambda s: -s["count"])

    return {
        "signals": signal_stats,
        "total_events": len(events),
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_backtest(report: dict) -> str:
    """Export backtest results to JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "backtest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(path) / 1024
    log.info(f"Wrote {path} ({size_kb:.1f} KB)")
    return path


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def run(signal_filter: str | None = None) -> dict:
    """Run all backtests and return aggregated report."""
    log.info("=" * 60)
    log.info("Signal Backtesting Framework")
    log.info("=" * 60)

    all_events: list[dict] = []

    # Load data
    log.info("Loading trend history...")
    trend_history = _load_json("trend_history.json")

    log.info("Loading capital flows...")
    capital_flows = _load_json("capital_flows.json")

    log.info("Loading ETF price series from collected/...")
    etf_prices = _load_etf_price_series()
    cf_prices = _load_capital_flow_etf_prices()
    log.info(f"  Sector ETF prices: {len(etf_prices)} dates")
    log.info(f"  Capital flow ETF prices: {len(cf_prices)} dates")

    # 1. Sector trend transitions
    if signal_filter in (None, "sector_trend"):
        log.info("Backtesting sector trend transitions...")
        if trend_history and etf_prices:
            events = backtest_sector_trends(trend_history, etf_prices)
            log.info(f"  {len(events)} sector trend events")
            all_events.extend(events)
        else:
            log.warning("  Skipped: missing trend_history or ETF prices")

    # 2. Capital flow phase transitions
    if signal_filter in (None, "capital_flow"):
        log.info("Backtesting capital flow phase transitions...")
        if capital_flows and cf_prices:
            events = backtest_capital_flow_phases(capital_flows, cf_prices)
            log.info(f"  {len(events)} capital flow phase events")
            all_events.extend(events)
        else:
            log.warning("  Skipped: missing capital_flows or CF ETF prices")

    # 3. RFI crossings
    if signal_filter in (None, "rfi"):
        log.info("Backtesting RFI crossings...")
        if capital_flows and cf_prices:
            events = backtest_rfi_crossings(capital_flows, cf_prices)
            log.info(f"  {len(events)} RFI crossing events")
            all_events.extend(events)
        else:
            log.warning("  Skipped: missing capital_flows or CF ETF prices")

    # 4. Macro regime transitions
    if signal_filter in (None, "macro_regime"):
        log.info("Backtesting macro regime transitions...")
        # Use sector ETF prices (has SPY) or capital flow ETF prices
        combined_prices = {**etf_prices, **cf_prices}
        if combined_prices:
            events = backtest_macro_regime(combined_prices)
            log.info(f"  {len(events)} macro regime events")
            all_events.extend(events)
        else:
            log.warning("  Skipped: missing ETF prices")

    # 5. Credit spread signal transitions
    if signal_filter in (None, "credit_spread"):
        log.info("Backtesting credit spread signals...")
        if cf_prices:
            events = backtest_credit_spread(cf_prices)
            log.info(f"  {len(events)} credit spread events")
            all_events.extend(events)
        else:
            log.warning("  Skipped: missing CF ETF prices")

    # 6. Breadth thrust signal transitions
    if signal_filter in (None, "breadth_thrust"):
        log.info("Backtesting breadth thrust signals...")
        if trend_history and etf_prices:
            events = backtest_breadth_thrust(trend_history, etf_prices)
            log.info(f"  {len(events)} breadth thrust events")
            all_events.extend(events)
        else:
            log.warning("  Skipped: missing ETF prices")

    # 7. RFI acceleration signal transitions
    if signal_filter in (None, "rfi_acceleration"):
        log.info("Backtesting RFI acceleration signals...")
        if capital_flows and cf_prices:
            events = backtest_rfi_acceleration(capital_flows, cf_prices)
            log.info(f"  {len(events)} RFI acceleration events")
            all_events.extend(events)
        else:
            log.warning("  Skipped: missing capital_flows or CF ETF prices")

    log.info(f"Total events: {len(all_events)}")

    # Aggregate
    log.info("Computing aggregate statistics...")
    aggregated = _aggregate_stats(all_events)

    # Build report
    from engine.utils.market_calendar import us_market_date
    report = {
        "date": us_market_date(),
        "total_events": aggregated["total_events"],
        "forward_horizons": FORWARD_HORIZONS,
        "signals": aggregated["signals"],
    }

    # Export
    export_backtest(report)

    log.info("=" * 60)
    log.info("Backtesting complete")
    log.info(f"  Total signals: {len(aggregated['signals'])}")
    log.info(f"  Total events: {aggregated['total_events']}")
    log.info("=" * 60)

    return report


if __name__ == "__main__":
    import sys
    signal = None
    for arg in sys.argv[1:]:
        if arg.startswith("--signal"):
            if "=" in arg:
                signal = arg.split("=", 1)[1]
            elif sys.argv.index(arg) + 1 < len(sys.argv):
                signal = sys.argv[sys.argv.index(arg) + 1]
    run(signal_filter=signal)
