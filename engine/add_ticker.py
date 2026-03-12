"""Add tickers to the Athene stock universe and run analysis.

Usage:
    python -m engine.add_ticker CPNG                    # add + analyze + backfill 1yr
    python -m engine.add_ticker --since 2025-06-01 CPNG # backfill from specific date
    python -m engine.add_ticker --no-backfill CPNG      # add + analyze, no backfill
    python -m engine.add_ticker --dry-run CPNG          # preview only
    python -m engine.add_ticker --no-analyze CPNG       # add to config only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from engine.utils.logger import get_logger

log = get_logger("athene.add_ticker")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.py")


def resolve_ticker_info(symbol: str) -> dict | None:
    """Fetch ticker metadata from yfinance."""
    try:
        info = yf.Ticker(symbol).info
        if not info or info.get("regularMarketPrice") is None:
            log.warning(f"{symbol}: not found on yfinance")
            return None
        return {
            "ticker": symbol.upper(),
            "name": info.get("shortName") or info.get("longName") or symbol,
            "sector": info.get("sector") or "Unknown",
            "industry": info.get("industry") or "",
        }
    except Exception as e:
        log.error(f"{symbol}: yfinance error: {e}")
        return None


def is_in_extra_tickers(symbol: str) -> bool:
    """Check if ticker already exists in EXTRA_TICKERS in config.py."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    # Find the EXTRA_TICKERS block
    match = re.search(r"EXTRA_TICKERS\s*=\s*\[", content)
    if not match:
        return False
    start = match.start()
    # Find closing bracket
    bracket_count = 0
    end = start
    for i in range(match.end() - 1, len(content)):
        if content[i] == "[":
            bracket_count += 1
        elif content[i] == "]":
            bracket_count -= 1
            if bracket_count == 0:
                end = i
                break
    block = content[start : end + 1]
    # Look for the ticker string in the block
    pattern = rf'"ticker":\s*"{re.escape(symbol.upper())}"'
    return bool(re.search(pattern, block))


def add_to_config(entries: list[dict]) -> int:
    """Append ticker entries to EXTRA_TICKERS in config.py. Returns count added."""
    if not entries:
        return 0

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find the closing ] of EXTRA_TICKERS
    in_extra = False
    bracket_depth = 0
    insert_line = -1
    for i, line in enumerate(lines):
        if "EXTRA_TICKERS" in line and "=" in line and "[" in line:
            in_extra = True
            bracket_depth = line.count("[") - line.count("]")
            if bracket_depth == 0:
                # Single-line: EXTRA_TICKERS = []
                insert_line = i
                break
            continue
        if in_extra:
            bracket_depth += line.count("[") - line.count("]")
            if bracket_depth <= 0:
                insert_line = i
                break

    if insert_line == -1:
        log.error("Could not find EXTRA_TICKERS closing bracket in config.py")
        return 0

    # Build new lines to insert before the closing ]
    new_lines = []
    for entry in entries:
        # Escape quotes in name
        name = entry["name"].replace('"', '\\"')
        new_lines.append(
            f'    {{"ticker": "{entry["ticker"]}", "name": "{name}", '
            f'"sector": "{entry["sector"]}", "industry": "{entry["industry"]}"}},\n'
        )

    for j, new_line in enumerate(new_lines):
        lines.insert(insert_line + j, new_line)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return len(entries)


def run_analysis(tickers: list[str]) -> None:
    """Run the engine pipeline for the given tickers."""
    cmd = [sys.executable, "-m", "engine.main"] + tickers
    log.info(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def backfill_history(tickers: list[str], since: str) -> None:
    """Backfill history.json with daily scores for new tickers.

    Uses existing dates in history.json as the date grid.
    Fundamentals and analyst data are treated as static snapshots.
    Only technical indicators (and thus alpha_score) vary by date.
    """
    from engine.collectors.price import collect_prices
    from engine.collectors.fundamental import collect_fundamentals
    from engine.collectors.analyst import collect_analyst_data
    from engine.analyzers.fundamental import analyze_fundamental, compute_fundamental_subscores
    from engine.analyzers.technical import analyze_technical, compute_technical_subscores
    from engine.analyzers.analyst import analyze_analyst, compute_analyst_subscores
    from engine.scorer.alpha_model import compute_alpha_score
    from engine.scorer.factor_model import compute_composite
    from engine.scorer.ranker import assign_tiers
    from engine.config import OUTPUT_DIR
    from engine.exporters.json_exporter import NumpyEncoder

    t_start = time.time()

    # -- Load existing history.json to get the date grid --
    history_path = os.path.join(OUTPUT_DIR, "history.json")
    if not os.path.exists(history_path):
        log.error(f"history.json not found at {history_path}; cannot backfill")
        return

    with open(history_path, "r", encoding="utf-8") as f:
        history: dict = json.load(f)

    # Filter to dates >= since
    all_dates = sorted(d for d in history.keys() if d >= since)
    if not all_dates:
        log.warning(f"No existing dates in history.json on or after {since}")
        return

    log.info(f"Backfill: {len(tickers)} ticker(s), {len(all_dates)} dates ({all_dates[0]} to {all_dates[-1]})")

    # -- Collect data --
    # Prices: fetch from well before `since` to ensure enough lookback for indicators
    lookback_start = (datetime.strptime(since, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")
    log.info(f"Collecting prices from {lookback_start} (with 90d lookback buffer)...")
    prices_all = collect_prices(tickers, start_date=lookback_start)
    if not prices_all:
        log.error("No price data collected; aborting backfill")
        return

    log.info("Collecting fundamentals (static snapshot)...")
    fundamentals = collect_fundamentals(tickers)

    log.info("Collecting analyst data (static snapshot)...")
    analyst_data = collect_analyst_data(tickers)

    # -- Pre-compute static scored DataFrames (fundamentals + analyst) --
    fund_raw = analyze_fundamental(fundamentals)
    fund_scored = compute_fundamental_subscores(fund_raw)

    analyst_raw = analyze_analyst(analyst_data)
    analyst_scored = compute_analyst_subscores(analyst_raw) if not analyst_raw.empty else None

    # -- History key list (matches export_history in json_exporter.py) --
    history_keys = (
        "earnings_visibility", "valuation_margin",
        "catalyst_timeline", "downside_control",
        "fundamental_score", "technical_score", "sentiment_score",
        "value_score", "quality_score", "growth_score", "safety_score",
        "trend_score", "momentum_score", "volatility_score", "volume_score",
        "analyst_score",
        "data_completeness",
        "pe_score", "forward_pe_score", "pb_score", "ps_score",
        "roe_score", "roa_score", "margin_score",
        "rev_growth_score", "earn_growth_score",
        "debt_equity_score", "fcf_yield_score", "current_ratio_score",
        "market_timing_score", "timing_penalty",
        "alpha_score",
        "alpha_vm", "alpha_ev", "alpha_timing",
        "alpha_visibility", "alpha_multiplier",
    )

    # Create an empty sentiment DataFrame (no news backfill)
    sent_df = pd.DataFrame(
        {"sentiment_score": 50.0},
        index=pd.Index(tickers, name="ticker"),
    )

    dates_processed = 0
    dates_skipped = 0

    for i, date_str in enumerate(all_dates):
        # Skip dates where all tickers already have entries
        existing_day = history.get(date_str, {})
        tickers_to_fill = [t for t in tickers if t not in existing_day]
        if not tickers_to_fill:
            dates_skipped += 1
            continue

        # Slice prices up to this date for each ticker
        date_ts = pd.Timestamp(date_str)
        prices_sliced: dict[str, pd.DataFrame] = {}
        for ticker in tickers_to_fill:
            if ticker not in prices_all:
                continue
            df = prices_all[ticker]
            sliced = df[df.index <= date_ts]
            if len(sliced) < 20:
                continue  # Not enough data for technical indicators
            prices_sliced[ticker] = sliced

        if not prices_sliced:
            dates_skipped += 1
            continue

        # Compute technical indicators on sliced prices
        tech_raw = analyze_technical(prices_sliced)
        if tech_raw.empty:
            dates_skipped += 1
            continue
        tech_scored = compute_technical_subscores(tech_raw)

        # Filter fund/analyst to only tickers present in this slice
        slice_tickers = list(prices_sliced.keys())
        fund_slice = fund_scored.reindex([t for t in slice_tickers if t in fund_scored.index])
        analyst_slice = (
            analyst_scored.reindex([t for t in slice_tickers if t in analyst_scored.index])
            if analyst_scored is not None
            else None
        )
        sent_slice = sent_df.reindex([t for t in slice_tickers if t in sent_df.index])

        # Compute alpha score
        alpha_df = compute_alpha_score(fund_slice, tech_scored, analyst_slice)

        # Compute composite (legacy)
        composite_df = compute_composite(fund_slice, tech_scored, sent_slice, analyst_slice)

        # Merge alpha into composite for assign_tiers
        for col in alpha_df.columns:
            composite_df[col] = alpha_df[col].reindex(composite_df.index)

        # Assign tiers (rank/percentile within backfill set only)
        ranked = assign_tiers(composite_df)

        # Merge into history
        if date_str not in history:
            history[date_str] = {}

        for ticker, row in ranked.iterrows():
            if ticker in history[date_str]:
                continue  # Don't overwrite existing entries

            entry: dict = {
                "composite_score": float(row.get("composite_score", 0)),
                "tier": str(row.get("tier", "")),
                "rank": int(row.get("rank", 0)),
                "percentile": float(row.get("percentile", 0)),
            }
            for key in history_keys:
                val = row.get(key)
                if val is not None and pd.notna(val):
                    entry[key] = round(float(val), 2)
            history[date_str][str(ticker)] = entry

        dates_processed += 1

        if (i + 1) % 10 == 0:
            log.info(f"  Backfill progress: {i + 1}/{len(all_dates)} dates processed")

    # -- Write updated history.json --
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)

    elapsed = time.time() - t_start
    log.info(
        f"Backfill complete: {dates_processed} dates filled, "
        f"{dates_skipped} skipped, {elapsed:.1f}s elapsed"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add tickers to Athene and run analysis",
    )
    parser.add_argument("tickers", nargs="+", help="Ticker symbols to add")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't modify config or analyze",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Add to config but skip analysis",
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        default=None,
        help="Backfill history from this date (default: 1 year ago)",
    )
    parser.add_argument(
        "--no-backfill",
        action="store_true",
        help="Skip history backfill",
    )
    args = parser.parse_args()

    symbols = [t.upper() for t in args.tickers]
    resolved = []
    skipped = []

    for symbol in symbols:
        if is_in_extra_tickers(symbol):
            log.info(f"{symbol}: already in EXTRA_TICKERS, skipping")
            skipped.append(symbol)
            continue

        log.info(f"{symbol}: resolving from yfinance...")
        info = resolve_ticker_info(symbol)
        if info is None:
            continue

        log.info(
            f"  {info['ticker']}: {info['name']} | {info['sector']} | {info['industry']}"
        )
        resolved.append(info)

    if not resolved:
        log.info("No new tickers to add")
        # Still run analysis for skipped tickers if they were already in config
        if skipped and not args.dry_run and not args.no_analyze:
            run_analysis(skipped)
        return

    if args.dry_run:
        log.info(f"[Dry run] Would add {len(resolved)} ticker(s) to EXTRA_TICKERS:")
        for entry in resolved:
            log.info(f"  {entry['ticker']}: {entry['name']} ({entry['sector']})")
        return

    added = add_to_config(resolved)
    log.info(f"Added {added} ticker(s) to EXTRA_TICKERS in config.py")

    if not args.no_analyze:
        all_tickers = [e["ticker"] for e in resolved] + skipped
        run_analysis(all_tickers)

        # Backfill history unless opted out
        if not args.no_backfill:
            since = args.since or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            log.info(f"Starting history backfill from {since}...")
            backfill_history(all_tickers, since)

    # Summary
    log.info("")
    log.info("Summary:")
    for entry in resolved:
        log.info(f"  + {entry['ticker']}: {entry['name']} ({entry['sector']})")
    for s in skipped:
        log.info(f"  = {s}: already existed")


if __name__ == "__main__":
    main()
