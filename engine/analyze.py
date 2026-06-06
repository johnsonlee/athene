"""CLI entry point for the analysis phase.

Usage:
    python -m engine.analyze

Reads all collected/YYYY/MM/DD/ directories:
  - prices/ETFs: concatenate daily slices → full DataFrames (200+ days for SMA200)
  - fundamentals/news/analyst/macro: latest date only
Runs the full analysis + scoring + export pipeline.
The collected/ directory is permanently retained.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from engine.collect import (
    COLLECTED_DIR,
    iter_date_dirs,
    _read_json_from_dir,
    read_json,
    read_per_ticker,
)
from engine.analyzers.fundamental import analyze_fundamental, compute_fundamental_subscores
from engine.analyzers.technical import analyze_technical, compute_technical_subscores
from engine.analyzers.sentiment import analyze_sentiment, annotate_headlines
from engine.analyzers.analyst import analyze_analyst, compute_analyst_subscores
from engine.analyzers.macro import detect_regime
from engine.analyzers.cyclical_risk import compute_cyclical_risk
from engine.scorer.factor_model import compute_composite
from engine.scorer.alpha_model import compute_alpha_score
from engine.scorer.ranker import assign_tiers
from engine.config import (
    OUTPUT_DIR,
    SMOOTH_ALPHA,
    WEIGHT_EARNINGS_VISIBILITY,
    WEIGHT_VALUATION_MARGIN,
    WEIGHT_CATALYST_TIMELINE,
    WEIGHT_DOWNSIDE_CONTROL,
)
from engine.exporters.json_exporter import (
    export_meta,
    export_rankings,
    export_history,
    export_stock_detail,
)
from engine.analyzers.sector_trend import analyze_sector_trends, compute_trend_history
from engine.analyzers.trend_scorer import score_sector_trends
from engine.exporters.trend_exporter import export_trends
from engine.analyzers.capital_flow import analyze_capital_flows
from engine.exporters.capital_flow_exporter import export_capital_flows
from engine.config import CAPITAL_FLOW_WINDOWS
from engine.exporters.changes import detect_changes, format_changes_markdown
from engine.exporters.feed import generate_feed
from engine.analyzers.ic_tracker import export_ic
from engine.analyzers.leading_indicators import compute_leading_indicators, export_leading_indicators
from engine.analyzers.market_timing import compute_market_timing
from engine.utils.logger import get_logger

log = get_logger("athene.analyze")

_DIMENSIONS = [
    "earnings_visibility", "valuation_margin",
    "catalyst_timeline", "downside_control",
]

_DIM_WEIGHTS = {
    "earnings_visibility": WEIGHT_EARNINGS_VISIBILITY,
    "valuation_margin": WEIGHT_VALUATION_MARGIN,
    "catalyst_timeline": WEIGHT_CATALYST_TIMELINE,
    "downside_control": WEIGHT_DOWNSIDE_CONTROL,
}

SNAPSHOT_DIR = "snapshots"
SNAPSHOT_FILES = [
    "meta.json", "rankings.json", "trends.json", "capital_flows.json",
    "leading_indicators.json", "ic.json", "backtest.json",
]


def _snapshot_results(run_date: str) -> None:
    """Archive analysis output files to snapshots/YYYY/MM/DD/HHmmss/ for debugging."""
    y, m, d = run_date.split("-")
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    snap_dir = os.path.join(SNAPSHOT_DIR, y, m, d, ts)
    copied = 0
    for fname in SNAPSHOT_FILES:
        src = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(src):
            os.makedirs(snap_dir, exist_ok=True)
            shutil.copy2(src, os.path.join(snap_dir, fname))
            copied += 1
    if copied:
        log.info(f"Snapshot: {copied} files → {snap_dir}")


# ── Date-partitioned data reconstruction ──────────────────────────

def _sorted_date_dirs(collected_dir: str) -> list[tuple[str, str]]:
    """Return sorted list of (date_str, dir_path) tuples under collected_dir."""
    return iter_date_dirs(collected_dir)


def _reconstruct_prices(collected_dir: str) -> dict[str, pd.DataFrame]:
    """Reconstruct full price DataFrames from daily per-ticker files.

    Reads each collected/YYYY/MM/DD/prices/<TICKER>.json (or legacy prices.json),
    accumulates rows per ticker, and returns Dict[str, pd.DataFrame] with
    DatetimeIndex — same structure that analyzers expect.
    """
    date_dirs = _sorted_date_dirs(collected_dir)
    # ticker -> list of (date, {Open, High, Low, Close, Volume})
    ticker_rows: dict[str, list[tuple[str, dict]]] = {}

    for date_str, dir_path in date_dirs:
        daily = read_per_ticker("prices", dir_path)
        if not daily:
            continue
        for ticker, row in daily.items():
            if ticker not in ticker_rows:
                ticker_rows[ticker] = []
            ticker_rows[ticker].append((date_str, row))

    result: dict[str, pd.DataFrame] = {}
    for ticker, rows in ticker_rows.items():
        records = []
        for date_str, row in rows:
            rec = {"Date": pd.Timestamp(date_str)}
            rec.update(row)
            records.append(rec)
        df = pd.DataFrame(records).set_index("Date").sort_index()
        # Drop duplicate dates (keep last)
        df = df[~df.index.duplicated(keep="last")]
        result[ticker] = df

    return result


def _reconstruct_etf_prices(collected_dir: str) -> dict[str, pd.DataFrame]:
    """Reconstruct full ETF price DataFrames from daily per-ticker files.

    Same approach as _reconstruct_prices but reads sector_etfs/<TICKER>.json files.
    """
    date_dirs = _sorted_date_dirs(collected_dir)
    ticker_rows: dict[str, list[tuple[str, dict]]] = {}

    for date_str, dir_path in date_dirs:
        daily = read_per_ticker("sector_etfs", dir_path)
        if not daily:
            continue
        for ticker, row in daily.items():
            if ticker not in ticker_rows:
                ticker_rows[ticker] = []
            ticker_rows[ticker].append((date_str, row))

    result: dict[str, pd.DataFrame] = {}
    for ticker, rows in ticker_rows.items():
        records = []
        for date_str, row in rows:
            rec = {"Date": pd.Timestamp(date_str)}
            rec.update(row)
            records.append(rec)
        df = pd.DataFrame(records).set_index("Date").sort_index()
        df = df[~df.index.duplicated(keep="last")]
        result[ticker] = df

    return result


def _reconstruct_capital_flow_etf_prices(collected_dir: str) -> dict[str, pd.DataFrame]:
    """Reconstruct capital flow ETF price DataFrames from daily per-ticker files.

    Same approach as _reconstruct_etf_prices but reads capital_flow_etfs/<TICKER>.json files.
    """
    date_dirs = _sorted_date_dirs(collected_dir)
    ticker_rows: dict[str, list[tuple[str, dict]]] = {}

    for date_str, dir_path in date_dirs:
        daily = read_per_ticker("capital_flow_etfs", dir_path)
        if not daily:
            continue
        for ticker, row in daily.items():
            if ticker not in ticker_rows:
                ticker_rows[ticker] = []
            ticker_rows[ticker].append((date_str, row))

    result: dict[str, pd.DataFrame] = {}
    for ticker, rows in ticker_rows.items():
        records = []
        for date_str, row in rows:
            rec = {"Date": pd.Timestamp(date_str)}
            rec.update(row)
            records.append(rec)
        df = pd.DataFrame(records).set_index("Date").sort_index()
        df = df[~df.index.duplicated(keep="last")]
        result[ticker] = df

    return result


def _load_latest_snapshot(name: str, collected_dir: str) -> object:
    """Find the latest date directory containing <name>.json and load it."""
    for _, dir_path in reversed(_sorted_date_dirs(collected_dir)):
        json_path = os.path.join(dir_path, f"{name}.json")
        gz_path = os.path.join(dir_path, f"{name}.json.gz")
        if os.path.exists(json_path) or os.path.exists(gz_path):
            return _read_json_from_dir(dir_path, name)
    raise FileNotFoundError(f"No collected data for '{name}' in any date directory under {collected_dir}")


# ── Data validation ───────────────────────────────────────────────

def _validate_data_quality(
    ranked: pd.DataFrame,
    universe_size: int,
    prices: dict[str, pd.DataFrame],
) -> None:
    """Validate data quality before exporting. Aborts on critical failures."""
    errors = []

    # Ticker coverage: ranked tickers >= 80% of universe
    coverage = len(ranked) / universe_size if universe_size > 0 else 0
    if coverage < 0.80:
        errors.append(
            f"Ticker coverage too low: {len(ranked)}/{universe_size} "
            f"({coverage:.0%}) — need >=80%"
        )

    # NaN/Inf check on composite_score
    if "composite_score" in ranked.columns:
        bad = ranked["composite_score"].isna() | np.isinf(ranked["composite_score"])
        if bad.any():
            errors.append(
                f"NaN/Inf in composite_score: {int(bad.sum())} tickers"
            )

        # Score distribution: std >= 5.0
        std = ranked["composite_score"].std()
        if std < 5.0:
            errors.append(
                f"Score distribution degenerate: std={std:.2f} — need >=5.0"
            )

    # Price history depth: >= 80% of tickers have 200+ days (warn only)
    if prices:
        deep_count = sum(1 for df in prices.values() if len(df) >= 200)
        deep_pct = deep_count / len(prices)
        if deep_pct < 0.80:
            log.warning(
                f"Price history depth: only {deep_count}/{len(prices)} "
                f"({deep_pct:.0%}) tickers have 200+ days"
            )

    if errors:
        for e in errors:
            log.error(f"VALIDATION FAILED: {e}")
        log.error("Aborting — will NOT overwrite frontend/public/data/")
        sys.exit(1)

    log.info("Data validation passed")


# ── EMA smoothing ─────────────────────────────────────────────────

def _load_previous_smoothed() -> dict[str, dict[str, float]]:
    """Load previous smoothed scores from history.json."""
    history_path = os.path.join(OUTPUT_DIR, "history.json")
    if not os.path.exists(history_path):
        return {}
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
        if not history:
            return {}
        latest_date = sorted(history.keys())[-1]
        daily = history[latest_date]
        result: dict[str, dict[str, float]] = {}
        for ticker, data in daily.items():
            if "composite_score" not in data:
                continue
            entry: dict[str, float] = {
                "composite_score": data["composite_score"],
            }
            for dim in _DIMENSIONS:
                if dim in data:
                    entry[dim] = data[dim]
            result[ticker] = entry
        return result
    except Exception as e:
        log.warning(f"Failed to load previous smoothed scores: {e}")
        return {}


def _apply_ema_smoothing(composite: pd.DataFrame) -> pd.DataFrame:
    """Apply EMA smoothing to dimension scores, then recompute composite."""
    result = composite.copy()
    prev_scores = _load_previous_smoothed()

    if prev_scores:
        max_prev = max(
            entry.get("composite_score", 0) or 0
            for entry in prev_scores.values()
        )
        if max_prev < 10:
            log.info("Previous scores appear to be from old z-score system, skipping EMA smoothing")
            prev_scores = {}

    for dim in _DIMENSIONS:
        smoothed = []
        for ticker, row in result.iterrows():
            raw = row[dim]
            prev_entry = prev_scores.get(str(ticker), {})
            prev = prev_entry.get(dim)
            if prev is not None:
                s = SMOOTH_ALPHA * raw + (1 - SMOOTH_ALPHA) * prev
            else:
                s = raw
            smoothed.append(s)
        result[dim] = smoothed

    dim_weights = {}
    for dim in _DIMENSIONS:
        weight_col = f"weight_{dim}"
        if weight_col in result.columns:
            dim_weights[dim] = result[weight_col].iloc[0]
        else:
            dim_weights[dim] = _DIM_WEIGHTS[dim]

    result["composite_score"] = sum(
        dim_weights[dim] * result[dim] for dim in _DIMENSIONS
    )

    return result


# ── Main pipeline ─────────────────────────────────────────────────

def run(collected_dir: str = COLLECTED_DIR) -> None:
    """Run the analysis pipeline from date-partitioned collected data."""
    start_time = time.time()
    log.info("=" * 60)
    log.info("Athene Analysis Pipeline - Start")
    log.info("=" * 60)

    # Load collected data via date-partitioned reconstruction
    log.info("Loading collected data (date-partitioned)...")

    universe_records = _load_latest_snapshot("universe", collected_dir)
    universe = pd.DataFrame(universe_records)
    tickers = universe["ticker"].tolist()
    log.info(f"Universe: {len(tickers)} tickers")

    log.info("Reconstructing price history from daily slices...")
    prices = _reconstruct_prices(collected_dir)
    log.info(f"Prices: {len(prices)} tickers, "
             f"history depth: {min(len(df) for df in prices.values()) if prices else 0}-"
             f"{max(len(df) for df in prices.values()) if prices else 0} days")

    fundamentals_raw = _load_latest_snapshot("fundamentals", collected_dir)
    log.info(f"Fundamentals: {len(fundamentals_raw)} tickers")

    news = _load_latest_snapshot("news", collected_dir)
    log.info(f"News: {len(news)} tickers")

    analyst_raw = _load_latest_snapshot("analyst", collected_dir)
    log.info(f"Analyst: {len(analyst_raw)} tickers")

    macro_raw = _load_latest_snapshot("macro", collected_dir)
    log.info(f"Macro: {list(macro_raw.keys())}")

    log.info("Reconstructing sector ETF history from daily slices...")
    etf_prices = _reconstruct_etf_prices(collected_dir)
    log.info(f"Sector ETFs: {len(etf_prices)} tickers")

    # Backfill "Unknown" sectors from yfinance data
    unknown_mask = universe["sector"].isin(["Unknown", "", None])
    if unknown_mask.any():
        backfilled = 0
        for idx in universe.index[unknown_mask]:
            ticker = universe.at[idx, "ticker"]
            yf_sector = (fundamentals_raw.get(ticker) or {}).get("sector")
            yf_industry = (fundamentals_raw.get(ticker) or {}).get("industry")
            if yf_sector and yf_sector not in ("", "Unknown"):
                universe.at[idx, "sector"] = yf_sector
                backfilled += 1
            if yf_industry and yf_industry not in ("", "Unknown") and not universe.at[idx, "industry"]:
                universe.at[idx, "industry"] = yf_industry
        if backfilled:
            log.info(f"Backfilled {backfilled} unknown sectors from yfinance")

    # Analysis
    log.info("Running fundamental analysis...")
    fund_df = analyze_fundamental(fundamentals_raw)

    log.info("Running technical analysis...")
    tech_df = analyze_technical(prices)

    log.info("Running sentiment analysis...")
    sent_df = analyze_sentiment(news)

    log.info("Detecting market regime...")
    regime_info = detect_regime(macro_raw)

    from engine.utils.market_calendar import us_market_date
    run_date = us_market_date()

    # --- v19: Run trend / CF / leading indicators BEFORE scoring ---
    # Trend pipeline
    log.info("Analyzing sector trends...")
    trend_df = analyze_sector_trends(etf_prices, prices, universe, analyst_raw)

    log.info("Scoring sector trends...")
    trend_scored = score_sector_trends(trend_df)

    log.info("Computing trend history...")
    trend_hist = compute_trend_history(etf_prices)

    log.info("Exporting trend data...")
    export_trends(trend_scored, regime_info, run_date, computed_history=trend_hist)

    # Capital flow pipeline
    log.info("Reconstructing capital flow ETF history from daily slices...")
    cf_prices = _reconstruct_capital_flow_etf_prices(collected_dir)
    cf_window_results: dict[str, list] = {}
    if cf_prices:
        log.info(f"Capital flow ETFs: {len(cf_prices)} tickers")
        log.info("Analyzing capital flows (multi-window)...")
        for label, wdays in CAPITAL_FLOW_WINDOWS.items():
            log.info(f"  Window {label} ({wdays} trading days)...")
            phases = analyze_capital_flows(
                cf_prices,
                window_days=wdays,
            )
            cf_window_results[label] = phases
        # Export CF early so compute_leading_indicators() can read from disk
        log.info("Exporting capital flow data...")
        export_capital_flows(cf_window_results, run_date)
        total_phases = sum(len(v) for v in cf_window_results.values())
        log.info(f"  Capital flow: {total_phases} phases across "
                 f"{len(cf_window_results)} windows")
    else:
        log.warning("No capital flow ETF data in collected/ — skipping capital flow analysis")

    # Leading indicators (reads capital_flows.json + trend_history.json from disk)
    leading: dict = {}
    log.info("Computing leading indicators...")
    try:
        leading = compute_leading_indicators()
        export_leading_indicators(leading, run_date)
    except Exception as e:
        log.warning(f"Leading indicators skipped: {e}")

    # Market Timing (synthesize all timing signals)
    log.info("Computing market timing...")
    timing_result = compute_market_timing(
        regime_info,
        cf_window_results=cf_window_results if cf_window_results else None,
        leading_indicators=leading.get("indicators") if isinstance(leading, dict) and "indicators" in leading else leading,
    )

    # --- Stock Scoring ---
    log.info("Scoring and ranking (absolute)...")
    sector_map = universe.set_index("ticker")["sector"] if not universe.empty else None
    fund_scored = compute_fundamental_subscores(fund_df, sectors=sector_map)
    tech_scored = compute_technical_subscores(tech_df)

    analyst_df = analyze_analyst(analyst_raw)
    analyst_scored = compute_analyst_subscores(analyst_df)

    # v17: Cyclical risk scoring
    cyclical_risk = compute_cyclical_risk(fund_df, sectors=sector_map)

    # v19: timing supersedes regime weights when available
    composite = compute_composite(fund_scored, tech_scored, sent_df, analyst_scored,
                                  weight_overrides=regime_info.get("weights"),
                                  cyclical_risk=cyclical_risk,
                                  sectors=sector_map,
                                  timing=timing_result)

    # v20: Alpha model (three-factor multiplicative) — runs in parallel for validation
    log.info("Computing alpha model scores...")
    alpha_result = compute_alpha_score(fund_scored, tech_scored, analyst_scored)
    # Merge alpha columns into composite for export
    for col in alpha_result.columns:
        composite[col] = alpha_result[col].reindex(composite.index)

    # Forward reversal sub-scores from tech_scored for display/IC tracking
    # (factor_model.py doesn't reference these, so they need explicit forwarding)
    for _rev_col in ("reversal_score", "macd_reversal_score", "kdj_reversal_score",
                      "rsi_reversal_score", "pullback_proximity_score"):
        if _rev_col in tech_scored.columns and _rev_col not in composite.columns:
            composite[_rev_col] = tech_scored[_rev_col].reindex(composite.index).fillna(50.0)

    composite = _apply_ema_smoothing(composite)

    # Spread amplification: expand composite_score around median to increase
    # tier differentiation.  Applied after EMA smoothing (which recomputes
    # composite from smoothed dimensions) and before tier assignment.
    _SPREAD_K = 1.3
    _median = composite["composite_score"].median()
    composite["composite_score"] = (_median + _SPREAD_K * (composite["composite_score"] - _median))
    # Re-apply penalties (were applied in compute_composite but EMA smoothing
    # recomputes composite from smoothed dimensions, losing them)
    if "data_quality_penalty" in composite.columns:
        composite["composite_score"] -= composite["data_quality_penalty"]
    if "trend_gate_penalty" in composite.columns:
        composite["composite_score"] -= composite["trend_gate_penalty"]
    if "timing_penalty" in composite.columns:
        composite["composite_score"] -= composite["timing_penalty"]
    composite["composite_score"] = composite["composite_score"].clip(0, 100)

    if "data_completeness" in composite.columns:
        dc = composite["data_completeness"]
        log.info(f"Data completeness: mean={dc.mean():.2f}, "
                 f"min={dc.min():.2f}, <50%={int((dc < 0.50).sum())} tickers")

    ranked = assign_tiers(composite)

    # Validate data quality before exporting
    _validate_data_quality(ranked, len(tickers), prices)

    # Detect changes
    changes = detect_changes(ranked, universe)
    if changes:
        log.info(f"Rating changes: {len(changes)}")
    generate_feed(changes, run_date)

    summary_md = format_changes_markdown(changes)
    summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_env:
        with open(summary_env, "a") as f:
            f.write(summary_md)
        log.info("Wrote changes to GitHub Job Summary")

    # Export
    if "market_cap" in fund_scored.columns:
        ranked = ranked.join(fund_scored[["market_cap"]], how="left")
    tech_export_cols = [
        col for col in ("close", "sma_200", "ma200_ref_5d_close", "ma200_ref_5d_sma_200")
        if col in tech_scored.columns
    ]
    if tech_export_cols:
        ranked = ranked.join(tech_scored[tech_export_cols], how="left")

    log.info("Exporting JSON data...")
    export_meta(len(tickers), run_date, macro=regime_info, timing=timing_result)
    export_rankings(ranked, universe)
    export_history(ranked, run_date)

    try:
        export_ic()
    except Exception as e:
        log.warning(f"IC computation skipped: {e}")

    # Backtest
    log.info("Running backtests...")
    try:
        from engine.backtest import run as run_backtest
        run_backtest()
    except Exception as e:
        log.warning(f"Backtest skipped: {e}")

    # Export individual stock details
    log.info("Exporting individual stock details...")
    universe_info = universe.set_index("ticker")[["name", "sector", "industry"]]
    exported_count = 0
    for ticker in tickers:
        price_data = prices.get(ticker, pd.DataFrame())
        fund_data = fund_scored.loc[ticker].to_dict() if ticker in fund_scored.index else None
        tech_data = tech_scored.loc[ticker].to_dict() if ticker in tech_scored.index else None
        sent_data = sent_df.loc[ticker].to_dict() if ticker in sent_df.index else None
        anl_data = analyst_scored.loc[ticker].to_dict() if ticker in analyst_scored.index else None
        rank_data = ranked.loc[ticker].to_dict() if ticker in ranked.index else None
        if rank_data is not None and ticker in universe_info.index:
            uinfo = universe_info.loc[ticker]
            rank_data["sector"] = uinfo.get("sector", "")
            rank_data["industry"] = uinfo.get("industry", "")
        headlines = annotate_headlines(news.get(ticker, []))
        export_stock_detail(ticker, price_data, fund_data, tech_data, sent_data, rank_data, headlines, anl_data)
        exported_count += 1

    _snapshot_results(run_date)

    # No cleanup of collected/ — data is permanently retained

    elapsed = time.time() - start_time
    log.info("=" * 60)
    log.info(f"Analysis complete in {elapsed:.1f}s")
    log.info(f"  Tickers processed: {len(tickers)}")
    log.info(f"  Price data: {len(prices)}")
    log.info(f"  Fundamentals: {len(fundamentals_raw)}")
    log.info(f"  News/sentiment: {len(news)}")
    log.info(f"  Analyst data: {len(analyst_raw)}")
    log.info(f"  Market regime: {regime_info.get('regime', 'N/A')}")
    log.info(f"  Stock details exported: {exported_count}")
    log.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="engine.analyze",
        description="Run Athene analysis pipeline from collected data.",
    )
    parser.add_argument(
        "--collected-dir",
        default=COLLECTED_DIR,
        help=f"Directory containing collected date-partitioned data (default: {COLLECTED_DIR})",
    )
    args = parser.parse_args()
    run(collected_dir=args.collected_dir)


if __name__ == "__main__":
    main()
