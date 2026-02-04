"""CLI entry point for the analysis phase.

Usage:
    python -m engine.analyze [--collected-dir collected]

Loads all collected/*.json[.gz] files produced by engine.collect,
runs the full analysis + scoring + export pipeline, then cleans up
the collected/ directory.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time

import pandas as pd

from engine.collect import (
    COLLECTED_DIR,
    read_json,
    deserialize_prices,
)
from engine.analyzers.fundamental import analyze_fundamental, compute_fundamental_subscores
from engine.analyzers.technical import analyze_technical, compute_technical_subscores
from engine.analyzers.sentiment import analyze_sentiment, annotate_headlines
from engine.analyzers.analyst import analyze_analyst, compute_analyst_subscores
from engine.analyzers.macro import detect_regime
from engine.scorer.factor_model import compute_composite
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
from engine.exporters.changes import detect_changes, format_changes_markdown
from engine.exporters.feed import generate_feed
from engine.analyzers.ic_tracker import export_ic
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


def run(collected_dir: str = COLLECTED_DIR) -> None:
    """Run the analysis pipeline from collected data."""
    start_time = time.time()
    log.info("=" * 60)
    log.info("Athene Analysis Pipeline - Start")
    log.info("=" * 60)

    # Load collected data
    log.info("Loading collected data...")

    universe_records = read_json("universe")
    universe = pd.DataFrame(universe_records)
    tickers = universe["ticker"].tolist()
    log.info(f"Universe: {len(tickers)} tickers")

    prices = deserialize_prices(read_json("prices"))
    log.info(f"Prices: {len(prices)} tickers")

    fundamentals_raw = read_json("fundamentals")
    log.info(f"Fundamentals: {len(fundamentals_raw)} tickers")

    news = read_json("news")
    log.info(f"News: {len(news)} tickers")

    analyst_raw = read_json("analyst")
    log.info(f"Analyst: {len(analyst_raw)} tickers")

    macro_raw = read_json("macro")
    log.info(f"Macro: {list(macro_raw.keys())}")

    etf_prices = deserialize_prices(read_json("sector_etfs"))
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

    # Scoring
    log.info("Scoring and ranking (absolute)...")
    sector_map = universe.set_index("ticker")["sector"] if not universe.empty else None
    fund_scored = compute_fundamental_subscores(fund_df, sectors=sector_map)
    tech_scored = compute_technical_subscores(tech_df)

    analyst_df = analyze_analyst(analyst_raw)
    analyst_scored = compute_analyst_subscores(analyst_df)

    regime_weights = regime_info.get("weights")
    composite = compute_composite(fund_scored, tech_scored, sent_df, analyst_scored,
                                  weight_overrides=regime_weights)

    composite = _apply_ema_smoothing(composite)

    if "data_completeness" in composite.columns:
        dc = composite["data_completeness"]
        log.info(f"Data completeness: mean={dc.mean():.2f}, "
                 f"min={dc.min():.2f}, <50%={int((dc < 0.50).sum())} tickers")

    ranked = assign_tiers(composite)

    # Detect changes
    run_date = time.strftime("%Y-%m-%d")
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

    log.info("Exporting JSON data...")
    export_meta(len(tickers), run_date, macro=regime_info)
    export_rankings(ranked, universe)
    export_history(ranked, run_date)

    try:
        export_ic()
    except Exception as e:
        log.warning(f"IC computation skipped: {e}")

    # Trend pipeline
    log.info("Analyzing sector trends...")
    trend_df = analyze_sector_trends(etf_prices, prices, universe, analyst_raw)

    log.info("Scoring sector trends...")
    trend_scored = score_sector_trends(trend_df)

    log.info("Computing trend history...")
    trend_hist = compute_trend_history(etf_prices)

    log.info("Exporting trend data...")
    export_trends(trend_scored, regime_info, run_date, computed_history=trend_hist)

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

    # Clean up collected directory
    if os.path.isdir(collected_dir):
        shutil.rmtree(collected_dir)
        log.info(f"Cleaned up {collected_dir}/")

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
        help=f"Directory containing collected data files (default: {COLLECTED_DIR})",
    )
    args = parser.parse_args()
    run(collected_dir=args.collected_dir)


if __name__ == "__main__":
    main()
