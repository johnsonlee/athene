"""Standalone capital flow pipeline.

Run independently of the main stock scoring pipeline:
    python -m engine.capital_flow_pipeline
    python -m engine.capital_flow_pipeline --window 5 --lookback 52

Data collection runs daily (OHLCV from yfinance).
Analysis window is configurable:
  --window   Trading days per snapshot (default 5 = weekly)
  --lookback Number of snapshots in timeline (default 52 = ~1 year)
"""

from __future__ import annotations

import argparse
import sys
import time

from engine.collectors.capital_flow import (
    collect_capital_flow_etfs,
    load_capital_flow_etfs_from_collected,
)
from engine.collectors.cftc import collect_cftc_cot
from engine.collectors.ici import collect_ici_flows
from engine.analyzers.capital_flow import analyze_capital_flows
from engine.exporters.capital_flow_exporter import export_capital_flows
from engine.utils.logger import get_logger

log = get_logger("athene.capital_flow")


def run(window_days: int | None = None, lookback_weeks: int | None = None) -> None:
    """Run the standalone capital flow pipeline.

    Args:
        window_days: Trading days per analysis window (None = use config default).
        lookback_weeks: Number of snapshots in timeline (None = use config default).
    """
    start_time = time.time()
    log.info("=" * 50)
    log.info("Athene Capital Flow Pipeline - Start")
    log.info("=" * 50)
    if window_days:
        log.info(f"  Analysis window: {window_days} trading days")
    if lookback_weeks:
        log.info(f"  Lookback: {lookback_weeks} snapshots")

    run_date = time.strftime("%Y-%m-%d")

    # Step 1: Load ETF price data (prefer stored daily slices, fallback to live)
    log.info("Step 1/5: Loading global asset class ETF data...")
    cf_prices = load_capital_flow_etfs_from_collected(
        lookback_weeks=lookback_weeks,
        end_date=run_date,
    )
    if not cf_prices:
        log.info("  No stored data found — fetching live from yfinance...")
        cf_prices = collect_capital_flow_etfs(
            lookback_weeks=lookback_weeks,
        )
    if not cf_prices:
        log.error("No ETF data available — aborting")
        return

    # Step 2: Collect CFTC COT data (optional)
    log.info("Step 2/5: Collecting CFTC COT data (optional)...")
    cftc_data = None
    try:
        cftc_data = collect_cftc_cot()
    except Exception as e:
        log.warning(f"CFTC data unavailable: {e}")

    # Step 3: Collect ICI fund flow data (optional)
    log.info("Step 3/5: Collecting ICI fund flow data (optional)...")
    ici_data = None
    try:
        ici_data = collect_ici_flows()
    except Exception as e:
        log.warning(f"ICI data unavailable: {e}")

    # Step 4: Analyze with multi-signal fusion at multiple windows
    log.info("Step 4/5: Analyzing capital flows (multi-signal fusion)...")
    from engine.config import CAPITAL_FLOW_WINDOWS
    windows_to_run = (
        {f"{window_days}d": window_days} if window_days
        else CAPITAL_FLOW_WINDOWS
    )
    all_window_results: dict[str, list] = {}
    for label, wdays in windows_to_run.items():
        log.info(f"  Window {label} ({wdays} trading days)...")
        phases = analyze_capital_flows(
            cf_prices,
            cftc_data=cftc_data,
            ici_data=ici_data,
            lookback_weeks=lookback_weeks,
            window_days=wdays,
        )
        all_window_results[label] = phases

    # Step 5: Export
    log.info("Step 5/5: Exporting capital flow data...")
    export_capital_flows(all_window_results, run_date)

    elapsed = time.time() - start_time
    total_phases = sum(len(v) for v in all_window_results.values())
    log.info("=" * 50)
    log.info(f"Capital Flow Pipeline complete in {elapsed:.1f}s")
    log.info(f"  ETFs collected: {len(cf_prices)}")
    log.info(f"  CFTC contracts: {len(cftc_data) if cftc_data else 0}")
    log.info(f"  ICI categories: {len(ici_data) if ici_data else 0}")
    log.info(f"  Windows: {list(all_window_results.keys())}")
    log.info(f"  Total phases exported: {total_phases}")
    log.info("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(description="Athene Capital Flow Pipeline")
    parser.add_argument(
        "--window", type=int, default=None,
        help="Trading days per analysis window (default: config value)",
    )
    parser.add_argument(
        "--lookback", type=int, default=None,
        help="Number of snapshots in timeline (default: config value)",
    )
    args = parser.parse_args()
    run(window_days=args.window, lookback_weeks=args.lookback)


if __name__ == "__main__":
    main()
