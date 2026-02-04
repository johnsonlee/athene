"""Main pipeline orchestrator for the Athene stock screening engine."""

from __future__ import annotations

import json
import os
import sys
import time

import pandas as pd

from engine.universe import build_universe
from engine.collectors.price import collect_prices
from engine.collectors.fundamental import collect_fundamentals
from engine.collectors.news import collect_news
from engine.collectors.analyst import collect_analyst_data
from engine.analyzers.fundamental import analyze_fundamental, compute_fundamental_subscores
from engine.analyzers.technical import analyze_technical, compute_technical_subscores
from engine.analyzers.sentiment import analyze_sentiment, annotate_headlines
from engine.analyzers.analyst import analyze_analyst, compute_analyst_subscores
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
from engine.exporters.changes import detect_changes, format_changes_markdown
from engine.exporters.feed import generate_feed
from engine.analyzers.ic_tracker import export_ic
from engine.utils.logger import get_logger
from engine.utils.market_calendar import is_us_trading_day

log = get_logger("athene.pipeline")


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
    """Load previous smoothed scores from history.json.

    Returns dict of ticker → {dimension: score, composite_score: score}.
    """
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
    """Apply EMA smoothing to dimension scores, then recompute composite.

    v6: Smooth each dimension individually so that
        composite = weighted sum of smoothed dimensions (math stays consistent).

    smoothed_dim = SMOOTH_ALPHA * raw_dim + (1 - SMOOTH_ALPHA) * prev_smoothed_dim
    composite = sum(weight_i * smoothed_dim_i)
    """
    result = composite.copy()
    prev_scores = _load_previous_smoothed()

    # Detect stale history from old z-score system (scores << 10).
    if prev_scores:
        max_prev = max(
            entry.get("composite_score", 0) or 0
            for entry in prev_scores.values()
        )
        if max_prev < 10:
            log.info("Previous scores appear to be from old z-score system, skipping EMA smoothing")
            prev_scores = {}

    # Smooth each dimension individually
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

    # Recompute composite from smoothed dimensions (math-consistent)
    result["composite_score"] = sum(
        _DIM_WEIGHTS[dim] * result[dim] for dim in _DIMENSIONS
    )

    return result


def run(tickers_override: list[str] | None = None) -> None:
    """Run the full analysis pipeline.

    Args:
        tickers_override: If provided, use these tickers instead of fetching
                         the full universe (useful for testing).
    """
    start_time = time.time()
    log.info("=" * 60)
    log.info("Athene Stock Screening Engine - Pipeline Start")
    log.info("=" * 60)

    test_mode = tickers_override is not None

    # Step 1: Build universe
    log.info("Step 1/9: Building stock universe...")
    if tickers_override:
        universe = pd.DataFrame({
            "ticker": tickers_override,
            "name": tickers_override,
            "sector": "Unknown",
            "industry": "",
        })
    else:
        universe = build_universe()

    tickers = universe["ticker"].tolist()
    log.info(f"Universe: {len(tickers)} tickers")

    # When US market is closed, only fetch data for new tickers (no existing
    # stock detail JSON).  Existing tickers' data hasn't changed — skip them.
    # Test mode and ATHENE_FORCE_RUN always run the full list regardless.
    force_run = os.environ.get("ATHENE_FORCE_RUN", "").lower() in ("true", "1", "yes")
    incremental = False
    if not test_mode and not force_run and not is_us_trading_day():
        stocks_dir = os.path.join(OUTPUT_DIR, "stocks")
        new_tickers = [t for t in tickers if not os.path.exists(os.path.join(stocks_dir, f"{t}.json"))]
        if new_tickers:
            log.info(f"US market is closed — only fetching {len(new_tickers)} new ticker(s)")
            log.info(f"  New: {', '.join(new_tickers[:20])}")
            tickers = new_tickers
            incremental = True
        else:
            log.info("US market is closed today — skipping pipeline")
            return

    # Step 2: Collect data
    log.info("Step 2/9: Collecting price data...")
    prices = collect_prices(tickers)

    log.info("Step 3/9: Collecting fundamental data...")
    fundamentals_raw = collect_fundamentals(tickers)

    # Backfill "Unknown" sectors from yfinance data (covers NASDAQ-only stocks
    # where Wikipedia may lack a sector column, and test-mode tickers).
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

    log.info("Step 4/9: Collecting news headlines...")
    news = collect_news(tickers)

    log.info("Step 5/9: Collecting analyst data...")
    analyst_raw = collect_analyst_data(tickers)

    # Step 3: Analyze
    log.info("Step 6/9: Running fundamental analysis...")
    fund_df = analyze_fundamental(fundamentals_raw)

    log.info("Step 7/9: Running technical analysis...")
    tech_df = analyze_technical(prices)

    log.info("Step 8/9: Running sentiment analysis...")
    sent_df = analyze_sentiment(news)

    # Step 4: Absolute scoring (no z-score normalization)
    log.info("Step 9/9: Scoring and ranking (absolute)...")

    # Pass sector info so financial-sector stocks use adjusted breakpoints
    sector_map = universe.set_index("ticker")["sector"] if not universe.empty else None
    fund_scored = compute_fundamental_subscores(fund_df, sectors=sector_map)
    tech_scored = compute_technical_subscores(tech_df)
    # sentiment_score already computed in analyze_sentiment (0-100)

    # v8: Analyst revision momentum scoring
    analyst_df = analyze_analyst(analyst_raw)
    analyst_scored = compute_analyst_subscores(analyst_df)

    # Step 5: Composite scoring (4-dimension qualitative model)
    composite = compute_composite(fund_scored, tech_scored, sent_df, analyst_scored)

    # Step 5.5: EMA smoothing on composite_score
    composite = _apply_ema_smoothing(composite)

    # Log data quality stats (v7)
    if "data_completeness" in composite.columns:
        dc = composite["data_completeness"]
        log.info(f"Data completeness: mean={dc.mean():.2f}, "
                 f"min={dc.min():.2f}, <50%={int((dc < 0.50).sum())} tickers")

    # Step 6: Rank and tier (absolute rating + relative ranking)
    ranked = assign_tiers(composite)

    # Step 7: Detect changes (before overwriting rankings.json)
    run_date = time.strftime("%Y-%m-%d")
    full_run = not test_mode and not incremental
    if full_run:
        changes = detect_changes(ranked, universe)
        if changes:
            log.info(f"Rating changes: {len(changes)}")
        feed_path = generate_feed(changes, run_date)

        # Write changes summary for GitHub Actions Job Summary
        summary_md = format_changes_markdown(changes)
        summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_env:
            with open(summary_env, "a") as f:
                f.write(summary_md)
            log.info("Wrote changes to GitHub Job Summary")

    # Step 8: Export
    # In test mode or incremental mode (market closed, new tickers only),
    # skip global aggregation files to avoid overwriting full-universe data.
    # Carry market_cap from fundamentals into ranked for export
    if "market_cap" in fund_scored.columns:
        ranked = ranked.join(fund_scored[["market_cap"]], how="left")

    if full_run:
        log.info("Exporting JSON data...")
        export_meta(len(tickers), run_date)
        export_rankings(ranked, universe)
        export_history(ranked, run_date)

        # Compute IC after history is updated (needs >=2 days for meaningful results)
        try:
            export_ic()
        except Exception as e:
            log.warning(f"IC computation skipped: {e}")
    else:
        log.info("Partial run — skipping global aggregation exports")

    # Export individual stock details (use scored DataFrames for sub-scores)
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
        # Attach universe info (sector/industry) to ranking data for detail pages
        if rank_data is not None and ticker in universe_info.index:
            uinfo = universe_info.loc[ticker]
            rank_data["sector"] = uinfo.get("sector", "")
            rank_data["industry"] = uinfo.get("industry", "")
        headlines = annotate_headlines(news.get(ticker, []))
        export_stock_detail(ticker, price_data, fund_data, tech_data, sent_data, rank_data, headlines, anl_data)
        exported_count += 1

    elapsed = time.time() - start_time
    log.info("=" * 60)
    log.info(f"Pipeline complete in {elapsed:.1f}s")
    log.info(f"  Tickers processed: {len(tickers)}")
    log.info(f"  Price data: {len(prices)}")
    log.info(f"  Fundamentals: {len(fundamentals_raw)}")
    log.info(f"  News/sentiment: {len(news)}")
    log.info(f"  Analyst data: {len(analyst_raw)}")
    log.info(f"  Stock details exported: {exported_count}")
    log.info("=" * 60)

    # In test mode, print a results summary to console
    if test_mode:
        log.info("")
        log.info("Test Results:")
        log.info(f"{'Ticker':<8} {'Score':>6} {'Rating':<12} {'Rank':>5}")
        log.info("-" * 35)
        for ticker in tickers:
            if ticker in ranked.index:
                row = ranked.loc[ticker]
                log.info(
                    f"{ticker:<8} {row['composite_score']:>6.1f} "
                    f"{row['tier']:<12} {int(row.get('rank', 0)):>5}"
                )
        log.info("")


if __name__ == "__main__":
    # Allow passing tickers as CLI args for testing
    if len(sys.argv) > 1:
        test_tickers = sys.argv[1:]
        log.info(f"Test mode: {test_tickers}")
        run(tickers_override=test_tickers)
    else:
        run()
