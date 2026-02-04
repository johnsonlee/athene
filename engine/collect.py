"""CLI entry point for individual data collectors.

Usage:
    python -m engine.collect universe [--tickers AAPL MSFT]
    python -m engine.collect prices
    python -m engine.collect fundamentals
    python -m engine.collect news
    python -m engine.collect analyst
    python -m engine.collect macro
    python -m engine.collect sector_etfs

Each command writes output to collected/<name>.json[.gz].
Per-ticker collectors read tickers from collected/universe.json.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys

import pandas as pd

from engine.utils.logger import get_logger

log = get_logger("athene.collect")

COLLECTED_DIR = "collected"


def _ensure_dir() -> None:
    os.makedirs(COLLECTED_DIR, exist_ok=True)


def _write_json(name: str, data: object) -> str:
    """Write data as JSON to collected/<name>.json. Returns the file path."""
    _ensure_dir()
    path = os.path.join(COLLECTED_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str)
    log.info(f"Wrote {path} ({os.path.getsize(path):,} bytes)")
    return path


def _write_json_gz(name: str, data: object) -> str:
    """Write data as gzipped JSON to collected/<name>.json.gz. Returns the file path."""
    _ensure_dir()
    path = os.path.join(COLLECTED_DIR, f"{name}.json.gz")
    payload = json.dumps(data, default=str).encode("utf-8")
    with gzip.open(path, "wb") as f:
        f.write(payload)
    log.info(f"Wrote {path} ({os.path.getsize(path):,} bytes)")
    return path


def read_json(name: str) -> object:
    """Read collected/<name>.json[.gz] and return the parsed data."""
    gz_path = os.path.join(COLLECTED_DIR, f"{name}.json.gz")
    json_path = os.path.join(COLLECTED_DIR, f"{name}.json")

    if os.path.exists(gz_path):
        with gzip.open(gz_path, "rb") as f:
            return json.loads(f.read().decode("utf-8"))
    elif os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"No collected data found for '{name}' "
                                f"(checked {gz_path} and {json_path})")


def serialize_dataframe(df: pd.DataFrame) -> dict:
    """Serialize a DataFrame to a JSON-compatible dict using split orient."""
    d = df.to_dict(orient="split")
    # Convert index values to strings for JSON serialization
    d["index"] = [str(v) for v in d["index"]]
    return d


def deserialize_dataframe(data: dict) -> pd.DataFrame:
    """Reconstruct a DataFrame from split-orient dict."""
    df = pd.DataFrame(**data)
    # Attempt to restore DatetimeIndex if index looks like dates
    try:
        df.index = pd.to_datetime(df.index)
    except (ValueError, TypeError):
        pass
    return df


def serialize_prices(prices: dict[str, pd.DataFrame]) -> dict:
    """Serialize a dict of ticker -> DataFrame for price data."""
    return {ticker: serialize_dataframe(df) for ticker, df in prices.items()}


def deserialize_prices(data: dict) -> dict[str, pd.DataFrame]:
    """Reconstruct a dict of ticker -> DataFrame from serialized price data."""
    return {ticker: deserialize_dataframe(entry) for ticker, entry in data.items()}


def _load_tickers() -> list[str]:
    """Load ticker list from collected/universe.json."""
    data = read_json("universe")
    return [row["ticker"] for row in data]


def cmd_universe(args: argparse.Namespace) -> None:
    """Build stock universe and write to collected/universe.json."""
    if args.tickers:
        universe = pd.DataFrame({
            "ticker": args.tickers,
            "name": args.tickers,
            "sector": "Unknown",
            "industry": "",
        })
    else:
        from engine.universe import build_universe
        universe = build_universe()

    records = universe.to_dict(orient="records")
    _write_json("universe", records)
    log.info(f"Universe: {len(records)} tickers")


def cmd_prices(args: argparse.Namespace) -> None:
    """Collect price data for all tickers."""
    from engine.collectors.price import collect_prices

    tickers = _load_tickers()
    log.info(f"Collecting prices for {len(tickers)} tickers...")
    prices = collect_prices(tickers)
    _write_json_gz("prices", serialize_prices(prices))
    log.info(f"Price data collected for {len(prices)} tickers")


def cmd_fundamentals(args: argparse.Namespace) -> None:
    """Collect fundamental data for all tickers."""
    from engine.collectors.fundamental import collect_fundamentals

    tickers = _load_tickers()
    log.info(f"Collecting fundamentals for {len(tickers)} tickers...")
    fundamentals = collect_fundamentals(tickers)
    _write_json("fundamentals", fundamentals)
    log.info(f"Fundamentals collected for {len(fundamentals)} tickers")


def cmd_news(args: argparse.Namespace) -> None:
    """Collect news headlines for all tickers."""
    from engine.collectors.news import collect_news

    tickers = _load_tickers()
    log.info(f"Collecting news for {len(tickers)} tickers...")
    news = collect_news(tickers)
    _write_json("news", news)
    log.info(f"News collected for {len(news)} tickers")


def cmd_analyst(args: argparse.Namespace) -> None:
    """Collect analyst data for all tickers."""
    from engine.collectors.analyst import collect_analyst_data

    tickers = _load_tickers()
    log.info(f"Collecting analyst data for {len(tickers)} tickers...")
    analyst = collect_analyst_data(tickers)
    _write_json("analyst", analyst)
    log.info(f"Analyst data collected for {len(analyst)} tickers")


def cmd_macro(args: argparse.Namespace) -> None:
    """Collect macro market indicators."""
    from engine.collectors.macro import collect_macro

    log.info("Collecting macro data...")
    macro = collect_macro()
    _write_json("macro", macro)


def cmd_sector_etfs(args: argparse.Namespace) -> None:
    """Collect sector ETF price data."""
    from engine.collectors.sector_etf import collect_sector_etfs

    log.info("Collecting sector ETF data...")
    etf_prices = collect_sector_etfs()
    _write_json("sector_etfs", serialize_prices(etf_prices))
    log.info(f"Sector ETF data collected for {len(etf_prices)} tickers")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="engine.collect",
        description="Run individual data collectors for the Athene pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # universe
    p_universe = subparsers.add_parser("universe", help="Build stock universe")
    p_universe.add_argument("--tickers", nargs="+", help="Override tickers (test mode)")
    p_universe.set_defaults(func=cmd_universe)

    # prices
    p_prices = subparsers.add_parser("prices", help="Collect price data")
    p_prices.set_defaults(func=cmd_prices)

    # fundamentals
    p_fund = subparsers.add_parser("fundamentals", help="Collect fundamental data")
    p_fund.set_defaults(func=cmd_fundamentals)

    # news
    p_news = subparsers.add_parser("news", help="Collect news headlines")
    p_news.set_defaults(func=cmd_news)

    # analyst
    p_analyst = subparsers.add_parser("analyst", help="Collect analyst data")
    p_analyst.set_defaults(func=cmd_analyst)

    # macro
    p_macro = subparsers.add_parser("macro", help="Collect macro indicators")
    p_macro.set_defaults(func=cmd_macro)

    # sector_etfs
    p_etfs = subparsers.add_parser("sector_etfs", help="Collect sector ETF data")
    p_etfs.set_defaults(func=cmd_sector_etfs)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
