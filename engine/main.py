"""Main pipeline orchestrator for the Athene stock screening engine."""

from __future__ import annotations

import sys
import time

import pandas as pd

from engine.universe import build_universe
from engine.collectors.price import collect_prices
from engine.collectors.fundamental import collect_fundamentals
from engine.collectors.news import collect_news
from engine.analyzers.fundamental import analyze_fundamental, compute_fundamental_subscores
from engine.analyzers.technical import analyze_technical, compute_technical_subscores
from engine.analyzers.sentiment import analyze_sentiment
from engine.scorer.normalizer import normalize_columns
from engine.scorer.factor_model import compute_composite
from engine.scorer.ranker import assign_tiers
from engine.exporters.json_exporter import (
    export_meta,
    export_universe,
    export_rankings,
    export_fundamentals,
    export_technicals,
    export_sentiment,
    export_stock_detail,
)
from engine.utils.logger import get_logger

log = get_logger("athene.pipeline")


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

    # Step 1: Build universe
    log.info("Step 1/8: Building stock universe...")
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

    # Step 2: Collect data
    log.info("Step 2/8: Collecting price data...")
    prices = collect_prices(tickers)

    log.info("Step 3/8: Collecting fundamental data...")
    fundamentals_raw = collect_fundamentals(tickers)

    log.info("Step 4/8: Collecting news headlines...")
    news = collect_news(tickers)

    # Step 3: Analyze
    log.info("Step 5/8: Running fundamental analysis...")
    fund_df = analyze_fundamental(fundamentals_raw)

    log.info("Step 6/8: Running technical analysis...")
    tech_df = analyze_technical(prices)

    log.info("Step 7/8: Running sentiment analysis...")
    sent_df = analyze_sentiment(news)

    # Step 4: Normalize
    log.info("Step 8/8: Scoring and ranking...")

    # Normalize fundamental metrics
    fund_z_cols = ["inv_pe", "inv_pb", "inv_ps", "roe", "roa",
                   "revenue_growth", "earnings_growth", "fcf_yield"]
    fund_norm = normalize_columns(fund_df, fund_z_cols)

    # Invert debt_to_equity (lower is better)
    if "debt_to_equity" in fund_norm.columns:
        fund_norm["debt_to_equity_inv"] = -fund_norm["debt_to_equity"]
        fund_norm = normalize_columns(fund_norm, ["debt_to_equity_inv"])

    fund_scored = compute_fundamental_subscores(fund_norm)

    # Normalize technical metrics
    tech_z_cols = ["trend_alignment", "rsi_score", "macd_histogram",
                   "bb_position", "volume_ratio"]
    tech_norm = normalize_columns(tech_df, tech_z_cols)
    tech_scored = compute_technical_subscores(tech_norm)

    # Normalize sentiment
    sent_norm = normalize_columns(sent_df, ["sentiment_compound"])
    if "sentiment_compound_z" in sent_norm.columns:
        sent_norm["sentiment_score"] = sent_norm["sentiment_compound_z"]
    elif "sentiment_compound" in sent_norm.columns:
        sent_norm["sentiment_score"] = sent_norm["sentiment_compound"]
    else:
        sent_norm["sentiment_score"] = 0.0

    # Step 5: Composite scoring
    composite = compute_composite(fund_scored, tech_scored, sent_norm)

    # Step 6: Rank and tier
    ranked = assign_tiers(composite)

    # Step 7: Export
    log.info("Exporting JSON data...")
    export_meta(len(tickers))
    export_universe(universe)
    export_rankings(ranked, universe)
    export_fundamentals(fund_df)
    export_technicals(tech_df)
    export_sentiment(sent_df)

    # Export individual stock details
    log.info("Exporting individual stock details...")
    exported_count = 0
    for ticker in tickers:
        price_data = prices.get(ticker, pd.DataFrame())
        fund_data = fund_df.loc[ticker].to_dict() if ticker in fund_df.index else None
        tech_data = tech_df.loc[ticker].to_dict() if ticker in tech_df.index else None
        sent_data = sent_df.loc[ticker].to_dict() if ticker in sent_df.index else None
        rank_data = ranked.loc[ticker].to_dict() if ticker in ranked.index else None
        export_stock_detail(ticker, price_data, fund_data, tech_data, sent_data, rank_data)
        exported_count += 1

    elapsed = time.time() - start_time
    log.info("=" * 60)
    log.info(f"Pipeline complete in {elapsed:.1f}s")
    log.info(f"  Tickers processed: {len(tickers)}")
    log.info(f"  Price data: {len(prices)}")
    log.info(f"  Fundamentals: {len(fundamentals_raw)}")
    log.info(f"  News/sentiment: {len(news)}")
    log.info(f"  Stock details exported: {exported_count}")
    log.info("=" * 60)


if __name__ == "__main__":
    # Allow passing tickers as CLI args for testing
    if len(sys.argv) > 1:
        test_tickers = sys.argv[1:]
        log.info(f"Test mode: {test_tickers}")
        run(tickers_override=test_tickers)
    else:
        run()
