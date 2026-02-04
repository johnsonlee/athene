"""CLI entry point for individual data collectors.

Usage:
    python -m engine.collect universe [--tickers AAPL MSFT] [--date 2026-02-05] [--force]
    python -m engine.collect prices [--date 2026-02-05] [--force]
    python -m engine.collect prices --bootstrap
    python -m engine.collect fundamentals [--date 2026-02-05] [--force]
    python -m engine.collect news [--date 2026-02-05] [--force]
    python -m engine.collect analyst [--date 2026-02-05] [--force]
    python -m engine.collect macro [--date 2026-02-05] [--force]
    python -m engine.collect sector_etfs [--date 2026-02-05] [--force]
    python -m engine.collect sector_etfs --bootstrap

Each command writes output to collected/YYYY-MM-DD/<name>.json.
Per-ticker collectors read tickers from the latest universe.json.
If data already exists for the given date, the command is skipped unless --force is set.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time

import pandas as pd

from engine.utils.logger import get_logger

log = get_logger("athene.collect")

COLLECTED_DIR = "collected"


def _get_date_dir(date_str: str) -> str:
    """Return the date-partitioned directory path: collected/YYYY-MM-DD/."""
    return os.path.join(COLLECTED_DIR, date_str)


def _ensure_date_dir(date_str: str) -> str:
    """Create and return the date-partitioned directory."""
    d = _get_date_dir(date_str)
    os.makedirs(d, exist_ok=True)
    return d


def _today() -> str:
    """Return today's date as YYYY-MM-DD string."""
    return time.strftime("%Y-%m-%d")


def _write_json(name: str, data: object, date_str: str | None = None) -> str:
    """Write data as JSON to collected/YYYY-MM-DD/<name>.json. Returns the file path."""
    ds = date_str or _today()
    d = _ensure_date_dir(ds)
    path = os.path.join(d, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str)
    log.info(f"Wrote {path} ({os.path.getsize(path):,} bytes)")
    return path


def _write_json_gz(name: str, data: object, date_str: str | None = None) -> str:
    """Write data as gzipped JSON to collected/YYYY-MM-DD/<name>.json.gz. Returns the file path."""
    ds = date_str or _today()
    d = _ensure_date_dir(ds)
    path = os.path.join(d, f"{name}.json.gz")
    payload = json.dumps(data, default=str).encode("utf-8")
    with gzip.open(path, "wb") as f:
        f.write(payload)
    log.info(f"Wrote {path} ({os.path.getsize(path):,} bytes)")
    return path


def read_json(name: str, date_str: str | None = None) -> object:
    """Read collected data.

    If *date_str* is given, reads from collected/<date_str>/<name>.json[.gz].
    Otherwise finds the latest date directory containing <name>.json[.gz].
    """
    if date_str:
        return _read_json_from_dir(_get_date_dir(date_str), name)
    # Find latest date dir containing this file
    return _read_json_latest(name)


def _read_json_from_dir(dir_path: str, name: str) -> object:
    gz_path = os.path.join(dir_path, f"{name}.json.gz")
    json_path = os.path.join(dir_path, f"{name}.json")
    if os.path.exists(gz_path):
        with gzip.open(gz_path, "rb") as f:
            return json.loads(f.read().decode("utf-8"))
    elif os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"No collected data for '{name}' in {dir_path}")


def _read_json_latest(name: str) -> object:
    """Find the latest date directory containing <name>.json[.gz] and load it."""
    if not os.path.isdir(COLLECTED_DIR):
        raise FileNotFoundError(f"No collected/ directory found")
    date_dirs = sorted(
        d for d in os.listdir(COLLECTED_DIR)
        if os.path.isdir(os.path.join(COLLECTED_DIR, d)) and _is_date_dir(d)
    )
    for d in reversed(date_dirs):
        dir_path = os.path.join(COLLECTED_DIR, d)
        gz = os.path.join(dir_path, f"{name}.json.gz")
        js = os.path.join(dir_path, f"{name}.json")
        if os.path.exists(gz) or os.path.exists(js):
            return _read_json_from_dir(dir_path, name)
    raise FileNotFoundError(f"No collected data for '{name}' in any date directory")


def _is_date_dir(name: str) -> bool:
    """Check if a directory name looks like YYYY-MM-DD."""
    if len(name) != 10:
        return False
    try:
        time.strptime(name, "%Y-%m-%d")
        return True
    except ValueError:
        return False


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
    """Load ticker list from the latest universe.json."""
    data = read_json("universe")
    return [row["ticker"] for row in data]


def _already_collected(name: str, date_str: str) -> bool:
    """Check if collected/<date>/<name>.json[.gz] already exists."""
    d = _get_date_dir(date_str)
    return (
        os.path.exists(os.path.join(d, f"{name}.json"))
        or os.path.exists(os.path.join(d, f"{name}.json.gz"))
    )


def _skip_if_exists(name: str, args: argparse.Namespace) -> bool:
    """Return True (and log) if data already collected and --force not set."""
    if not getattr(args, "force", False) and _already_collected(name, args.date):
        log.info(f"Already collected {name} for {args.date} — skipping (use --force to overwrite)")
        return True
    return False


# ── CLI commands ──────────────────────────────────────────────────

def cmd_universe(args: argparse.Namespace) -> None:
    """Build stock universe and write to collected/<date>/universe.json."""
    if _skip_if_exists("universe", args):
        return
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
    _write_json("universe", records, date_str=args.date)
    log.info(f"Universe: {len(records)} tickers")


def cmd_prices(args: argparse.Namespace) -> None:
    """Collect price data for all tickers."""
    if args.bootstrap:
        _bootstrap_prices(args)
        return
    if _skip_if_exists("prices", args):
        return

    from engine.collectors.price import collect_prices_daily

    tickers = _load_tickers()
    date_str = args.date
    log.info(f"Collecting daily prices for {len(tickers)} tickers (date={date_str})...")
    daily = collect_prices_daily(tickers, date_str)
    _write_json("prices", daily, date_str=date_str)
    log.info(f"Daily price data collected for {len(daily)} tickers")


def _bootstrap_prices(args: argparse.Namespace) -> None:
    """Bootstrap: fetch 365 days of prices and split into daily slices."""
    from engine.collectors.price import collect_prices

    tickers = _load_tickers()
    log.info(f"Bootstrapping prices for {len(tickers)} tickers (365 days)...")
    prices = collect_prices(tickers)

    total_files = 0
    for ticker, df in prices.items():
        for date_val, row in df.iterrows():
            date_str = pd.Timestamp(date_val).strftime("%Y-%m-%d")
            d = _get_date_dir(date_str)
            path = os.path.join(d, "prices.json")

            # Load existing file if present (accumulate tickers)
            existing = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing[ticker] = {
                "Open": float(row["Open"]),
                "High": float(row["High"]),
                "Low": float(row["Low"]),
                "Close": float(row["Close"]),
                "Volume": int(row["Volume"]),
            }

            os.makedirs(d, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, default=str)

        total_files += 1

    # Count date dirs with prices
    date_count = sum(
        1 for d in os.listdir(COLLECTED_DIR)
        if _is_date_dir(d) and os.path.exists(os.path.join(COLLECTED_DIR, d, "prices.json"))
    )
    log.info(f"Bootstrap complete: {len(prices)} tickers across {date_count} date directories")


def cmd_fundamentals(args: argparse.Namespace) -> None:
    """Collect fundamental data for all tickers."""
    if _skip_if_exists("fundamentals", args):
        return
    from engine.collectors.fundamental import collect_fundamentals

    tickers = _load_tickers()
    log.info(f"Collecting fundamentals for {len(tickers)} tickers...")
    fundamentals = collect_fundamentals(tickers)
    _write_json("fundamentals", fundamentals, date_str=args.date)
    log.info(f"Fundamentals collected for {len(fundamentals)} tickers")


def cmd_news(args: argparse.Namespace) -> None:
    """Collect news headlines for all tickers."""
    if _skip_if_exists("news", args):
        return
    from engine.collectors.news import collect_news

    tickers = _load_tickers()
    log.info(f"Collecting news for {len(tickers)} tickers...")
    news = collect_news(tickers)
    _write_json("news", news, date_str=args.date)
    log.info(f"News collected for {len(news)} tickers")


def cmd_analyst(args: argparse.Namespace) -> None:
    """Collect analyst data for all tickers."""
    if _skip_if_exists("analyst", args):
        return
    from engine.collectors.analyst import collect_analyst_data

    tickers = _load_tickers()
    log.info(f"Collecting analyst data for {len(tickers)} tickers...")
    analyst = collect_analyst_data(tickers)
    _write_json("analyst", analyst, date_str=args.date)
    log.info(f"Analyst data collected for {len(analyst)} tickers")


def cmd_macro(args: argparse.Namespace) -> None:
    """Collect macro market indicators."""
    if _skip_if_exists("macro", args):
        return
    from engine.collectors.macro import collect_macro

    log.info("Collecting macro data...")
    macro = collect_macro()
    _write_json("macro", macro, date_str=args.date)


def cmd_sector_etfs(args: argparse.Namespace) -> None:
    """Collect sector ETF price data."""
    if args.bootstrap:
        _bootstrap_sector_etfs(args)
        return
    if _skip_if_exists("sector_etfs", args):
        return

    from engine.collectors.sector_etf import collect_sector_etfs_daily

    date_str = args.date
    log.info(f"Collecting daily sector ETF data (date={date_str})...")
    daily = collect_sector_etfs_daily(date_str)
    _write_json("sector_etfs", daily, date_str=date_str)
    log.info(f"Daily sector ETF data collected for {len(daily)} tickers")


def _bootstrap_sector_etfs(args: argparse.Namespace) -> None:
    """Bootstrap: fetch 365 days of sector ETF data and split into daily slices."""
    from engine.collectors.sector_etf import collect_sector_etfs

    log.info("Bootstrapping sector ETF data (365 days)...")
    etf_prices = collect_sector_etfs()

    for ticker, df in etf_prices.items():
        for date_val, row in df.iterrows():
            date_str = pd.Timestamp(date_val).strftime("%Y-%m-%d")
            d = _get_date_dir(date_str)
            path = os.path.join(d, "sector_etfs.json")

            existing = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)

            existing[ticker] = {
                "Open": float(row["Open"]),
                "High": float(row["High"]),
                "Low": float(row["Low"]),
                "Close": float(row["Close"]),
                "Volume": int(row["Volume"]),
            }

            os.makedirs(d, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, default=str)

    date_count = sum(
        1 for d in os.listdir(COLLECTED_DIR)
        if _is_date_dir(d) and os.path.exists(os.path.join(COLLECTED_DIR, d, "sector_etfs.json"))
    )
    log.info(f"Bootstrap complete: {len(etf_prices)} ETFs across {date_count} date directories")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="engine.collect",
        description="Run individual data collectors for the Athene pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    today = _today()

    # Shared flags added to each subcommand
    def _add_common_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--date", default=today, help="Date partition (default: today)")
        p.add_argument("--force", action="store_true",
                        help="Force re-fetch even if data already exists for this date")

    # universe
    p_universe = subparsers.add_parser("universe", help="Build stock universe")
    p_universe.add_argument("--tickers", nargs="+", help="Override tickers (test mode)")
    _add_common_args(p_universe)
    p_universe.set_defaults(func=cmd_universe)

    # prices
    p_prices = subparsers.add_parser("prices", help="Collect price data")
    _add_common_args(p_prices)
    p_prices.add_argument("--bootstrap", action="store_true",
                          help="Fetch full 365 days and split into daily slices")
    p_prices.set_defaults(func=cmd_prices)

    # fundamentals
    p_fund = subparsers.add_parser("fundamentals", help="Collect fundamental data")
    _add_common_args(p_fund)
    p_fund.set_defaults(func=cmd_fundamentals)

    # news
    p_news = subparsers.add_parser("news", help="Collect news headlines")
    _add_common_args(p_news)
    p_news.set_defaults(func=cmd_news)

    # analyst
    p_analyst = subparsers.add_parser("analyst", help="Collect analyst data")
    _add_common_args(p_analyst)
    p_analyst.set_defaults(func=cmd_analyst)

    # macro
    p_macro = subparsers.add_parser("macro", help="Collect macro indicators")
    _add_common_args(p_macro)
    p_macro.set_defaults(func=cmd_macro)

    # sector_etfs
    p_etfs = subparsers.add_parser("sector_etfs", help="Collect sector ETF data")
    _add_common_args(p_etfs)
    p_etfs.add_argument("--bootstrap", action="store_true",
                        help="Fetch full 365 days and split into daily slices")
    p_etfs.set_defaults(func=cmd_sector_etfs)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
