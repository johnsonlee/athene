"""Collect OHLCV + shares outstanding data for global asset class ETFs.

Fetches daily OHLCV for representative ETFs across major asset classes
(US/EU/JP/EM equity, crypto, gold, treasuries, cash, corporate bonds)
used by the capital flow pipeline to compute direct fund flows from
ETF creation/redemption (shares outstanding changes).

Shares outstanding sources (hybrid approach):
- iShares ETFs (EWJ, EEM, IBIT, TLT, LQD): iShares AJAX CSV endpoint
- GLD: SPDR Gold Shares archive CSV
- SPY, BIL, VGK: No free shares source → proxy fallback in analyzer

Supports two modes:
- **Live fetch**: `collect_capital_flow_etfs()` downloads historical OHLCV from yfinance.
- **Stored daily**: `load_capital_flow_etfs_from_collected()` reconstructs DataFrames
  from stored `collected/YYYY/MM/DD/capital_flow_etfs/<TICKER>.json` daily slices.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import requests
import yfinance as yf

from engine.config import (
    CAPITAL_FLOW_ETFS,
    CAPITAL_FLOW_LOOKBACK_WEEKS,
    CAPITAL_FLOW_WINDOW_DAYS,
)
from engine.utils.logger import get_logger
from engine.utils.rate_limiter import rate_limiter

log = get_logger(__name__)

# Session-level cache for GLD archive CSV (avoids re-downloading)
_gld_archive_cache: pd.DataFrame | None = None


def collect_capital_flow_etfs(
    lookback_weeks: int | None = None,
    end_date: str | None = None,
    start_date: str | None = None,
) -> Dict[str, pd.DataFrame]:
    """Fetch OHLCV for global asset class ETFs.

    Args:
        lookback_weeks: Number of weekly windows to cover. Defaults to
            CAPITAL_FLOW_LOOKBACK_WEEKS.
        end_date: End date (YYYY-MM-DD). Defaults to now.
        start_date: Start date (YYYY-MM-DD). If provided, overrides
            the lookback_weeks calculation.

    Returns:
        dict mapping ticker (e.g. "SPY", "GLD") -> DataFrame with
        columns [Open, High, Low, Close, Volume] indexed by date.
    """
    weeks = lookback_weeks or CAPITAL_FLOW_LOOKBACK_WEEKS
    tickers = list(CAPITAL_FLOW_ETFS.keys())

    from engine.utils.market_calendar import us_market_now
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else us_market_now()
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # Extra buffer for weekends/holidays
        calendar_days = weeks * 7 + 30
        start = end - timedelta(days=calendar_days)

    log.info(f"Downloading capital flow ETF prices: {len(tickers)} tickers, "
             f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    rate_limiter.wait()

    result: Dict[str, pd.DataFrame] = {}

    try:
        data = yf.download(
            tickers,
            start=start.strftime("%Y-%m-%d"),
            end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        log.error(f"Capital flow ETF batch download failed: {e}")
        return result

    if data.empty:
        log.warning("Capital flow ETF download returned empty data")
        return result

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = data.copy()
            else:
                df = (
                    data[ticker].copy()
                    if ticker in data.columns.get_level_values(0)
                    else pd.DataFrame()
                )
            if not df.empty:
                df = df.dropna(how="all")
                if not df.empty:
                    result[ticker] = df
        except (KeyError, Exception) as e:
            log.warning(f"No capital flow ETF data for {ticker}: {e}")

    log.info(f"Capital flow ETF data collected for {len(result)}/{len(tickers)} tickers")
    return result


# ---------------------------------------------------------------------------
# Shares outstanding fetchers
# ---------------------------------------------------------------------------

_ISHARES_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}


def _fetch_ishares_shares(ticker: str, product_id: int, slug: str, date: str) -> int | None:
    """Fetch shares outstanding for an iShares ETF on a specific date.

    Uses the iShares AJAX CSV endpoint which includes fund-level metadata
    rows at the top of the CSV, including "Shares Outstanding".

    Args:
        ticker: ETF ticker symbol (for logging).
        product_id: iShares product ID (e.g. 239454 for TLT).
        slug: iShares product slug (e.g. "ishares-20-plus-year-treasury-bond-etf").
        date: Date string YYYY-MM-DD.

    Returns:
        Shares outstanding as int, or None if unavailable.
    """
    date_formatted = date.replace("-", "")
    url = (
        f"https://www.ishares.com/us/products/{product_id}/{slug}/"
        f"1467271812596.ajax?fileType=csv&fileName={slug}_holdings"
        f"&dataType=fund&asOfDate={date_formatted}"
    )

    try:
        resp = requests.get(url, headers=_ISHARES_HEADERS, timeout=30)
        if resp.status_code != 200:
            log.warning(f"iShares {ticker}: HTTP {resp.status_code} for {date}")
            return None

        text = resp.text
        # Parse CSV — shares outstanding is in the fund metadata rows at top
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Look for a line that starts with "Shares Outstanding"
            if line.startswith('"Shares Outstanding"') or line.startswith("Shares Outstanding"):
                # Parse the CSV row
                reader = csv.reader(io.StringIO(line))
                row = next(reader)
                # The value is typically in the second column
                for cell in row[1:]:
                    cell = cell.strip().replace(",", "").replace('"', '')
                    if cell and cell != "-":
                        try:
                            return int(float(cell))
                        except (ValueError, TypeError):
                            continue
            # Also check for "Shares Outstanding" as part of the metadata block
            # Some iShares CSVs use different formatting
            lower = line.lower()
            if "shares outstanding" in lower and "," in line:
                reader = csv.reader(io.StringIO(line))
                row = next(reader)
                for cell in row[1:]:
                    cell = cell.strip().replace(",", "").replace('"', '')
                    if cell and cell != "-":
                        try:
                            return int(float(cell))
                        except (ValueError, TypeError):
                            continue

        log.warning(f"iShares {ticker}: 'Shares Outstanding' not found in CSV for {date}")
        return None

    except requests.RequestException as e:
        log.warning(f"iShares {ticker}: request failed for {date}: {e}")
        return None
    except Exception as e:
        log.warning(f"iShares {ticker}: parse error for {date}: {e}")
        return None


def _load_gld_archive() -> pd.DataFrame | None:
    """Download and parse the SPDR Gold Shares archive CSV.

    The GLD archive CSV contains columns:
      Date, GLD Close, NAV per GLD in Gold, NAV/share, ...,
      Total Net Asset Value in the Trust

    Shares outstanding is computed as:
      shares = Total Net Asset Value / NAV per share

    Returns a DataFrame with column [shares_outstanding] indexed by Date,
    or None on failure. Caches the result for the session.
    """
    global _gld_archive_cache
    if _gld_archive_cache is not None:
        return _gld_archive_cache

    url = "https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code != 200:
            log.warning(f"GLD archive: HTTP {resp.status_code}")
            return None

        lines = resp.text.strip().split("\n")

        # Find header row (starts with "Date")
        header_idx = None
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("date"):
                header_idx = i
                break

        if header_idx is None:
            log.warning("GLD archive: could not find header row")
            return None

        # Parse header to find column indices
        csv_text = "\n".join(lines[header_idx:])
        reader = csv.reader(io.StringIO(lines[header_idx]))
        header_cols = [col.strip().lower() for col in next(reader)]

        # Find required column indices
        date_idx = 0  # "date" is always first
        nav_share_idx = None  # "nav/share at ..."
        total_nav_idx = None  # "total net asset value in the trust"

        for i, col in enumerate(header_cols):
            if col.startswith("nav/share"):
                nav_share_idx = i
            if col.startswith("total net asset value in the trust"):
                total_nav_idx = i

        if nav_share_idx is None or total_nav_idx is None:
            log.warning(f"GLD archive: required columns not found "
                        f"(nav_share_idx={nav_share_idx}, total_nav_idx={total_nav_idx})")
            return None

        # Parse data rows
        data_reader = csv.reader(io.StringIO("\n".join(lines[header_idx + 1:])))
        rows = []
        for row in data_reader:
            try:
                if len(row) <= max(nav_share_idx, total_nav_idx):
                    continue

                date_str = row[date_idx].strip()
                nav_share_str = row[nav_share_idx].strip().replace(",", "").replace("$", "")
                total_nav_str = row[total_nav_idx].strip().replace(",", "").replace("$", "")

                # Skip holidays and missing data
                if not date_str or "HOLIDAY" in date_str.upper():
                    continue
                if not nav_share_str or "HOLIDAY" in nav_share_str.upper():
                    continue
                if not total_nav_str or "HOLIDAY" in total_nav_str.upper():
                    continue

                nav_share = float(nav_share_str)
                total_nav = float(total_nav_str)

                if nav_share <= 0:
                    continue

                shares = int(round(total_nav / nav_share))

                # Parse date (format: DD-Mon-YYYY, e.g. "06-Feb-2026")
                parsed_date = None
                for fmt in ("%d-%b-%Y", "%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue

                if parsed_date and shares > 0:
                    rows.append({
                        "Date": parsed_date.strftime("%Y-%m-%d"),
                        "shares_outstanding": shares,
                    })
            except (ValueError, TypeError, IndexError):
                continue

        if not rows:
            log.warning("GLD archive: no valid rows parsed")
            return None

        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        df = df[~df.index.duplicated(keep="last")]

        log.info(f"GLD archive loaded: {len(df)} data points "
                 f"({df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')})")
        _gld_archive_cache = df
        return df

    except requests.RequestException as e:
        log.warning(f"GLD archive: request failed: {e}")
        return None
    except Exception as e:
        log.warning(f"GLD archive: parse error: {e}")
        return None


def _fetch_gld_shares(date: str) -> int | None:
    """Fetch GLD shares outstanding for a specific date from the SPDR archive.

    Args:
        date: Date string YYYY-MM-DD.

    Returns:
        Shares outstanding as int, or None if unavailable.
    """
    archive = _load_gld_archive()
    if archive is None or archive.empty:
        return None

    date_ts = pd.Timestamp(date)

    # Try exact date match first, then look back up to 5 days
    for offset in range(6):
        lookup = date_ts - timedelta(days=offset)
        if lookup in archive.index:
            return int(archive.loc[lookup, "shares_outstanding"])

    return None


def _fetch_shares_for_ticker(ticker: str, date: str) -> int | None:
    """Dispatch to the correct shares outstanding fetcher based on config.

    Args:
        ticker: ETF ticker symbol.
        date: Date string YYYY-MM-DD.

    Returns:
        Shares outstanding as int, or None if unavailable or not supported.
    """
    meta = CAPITAL_FLOW_ETFS.get(ticker)
    if not meta:
        return None

    source = meta.get("shares_source")
    if source is None:
        return None  # Proxy-only ticker

    if source == "ishares":
        product_id = meta["ishares_id"]
        slug = meta["ishares_slug"]
        return _fetch_ishares_shares(ticker, product_id, slug, date)
    elif source == "spdr_gold":
        return _fetch_gld_shares(date)

    log.warning(f"Unknown shares_source '{source}' for {ticker}")
    return None


# ---------------------------------------------------------------------------
# Daily collection
# ---------------------------------------------------------------------------

def collect_capital_flow_etfs_daily(target_date: str) -> Dict[str, dict]:
    """Fetch OHLCV + shares outstanding for the latest trading day up to *target_date*.

    Fetches 5 calendar days ending at target_date+1 for capital flow ETFs.
    Shares outstanding are fetched from real sources (iShares/SPDR) for
    supported ETFs; unsupported tickers (SPY, BIL, VGK) get no Shares field.

    Returns:
        dict mapping ticker (e.g. "SPY", "GLD") -> {Open, High, Low, Close, Volume, Shares?}
    """
    tickers = list(CAPITAL_FLOW_ETFS.keys())
    target = pd.Timestamp(target_date)
    start = (target - timedelta(days=5)).strftime("%Y-%m-%d")
    end = (target + timedelta(days=1)).strftime("%Y-%m-%d")

    log.info(f"Downloading daily capital flow ETF prices: {len(tickers)} tickers")
    rate_limiter.wait()

    result: Dict[str, dict] = {}

    try:
        data = yf.download(
            tickers,
            start=start,
            end=end,
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        log.error(f"Capital flow ETF daily download failed: {e}")
        return result

    if data.empty:
        log.warning("Capital flow ETF daily download returned empty data")
        return result

    for ticker in tickers:
        try:
            if len(tickers) == 1:
                df = data.copy()
            else:
                df = (
                    data[ticker].copy()
                    if ticker in data.columns.get_level_values(0)
                    else pd.DataFrame()
                )
            if not df.empty:
                df = df.dropna(how="all")
                if not df.empty:
                    last = df.iloc[-1]
                    entry = {
                        "Open": float(last["Open"]),
                        "High": float(last["High"]),
                        "Low": float(last["Low"]),
                        "Close": float(last["Close"]),
                        "Volume": int(last["Volume"]),
                    }
                    # Fetch shares outstanding from real source
                    shares = _fetch_shares_for_ticker(ticker, target_date)
                    if shares is not None:
                        entry["Shares"] = shares

                    result[ticker] = entry
        except (KeyError, Exception) as e:
            log.warning(f"No daily capital flow ETF data for {ticker}: {e}")

    shares_count = sum(1 for v in result.values() if "Shares" in v)
    log.info(f"Daily capital flow ETF data collected for {len(result)}/{len(tickers)} tickers "
             f"({shares_count} with shares outstanding)")
    return result


def backfill_shares_outstanding() -> None:
    """Backfill shares outstanding data into existing collected daily JSONs.

    Scans all date directories under collected/, fetches historical shares
    outstanding for each capital flow ETF from real sources (iShares/SPDR),
    and updates per-ticker JSONs in-place with a "Shares" field.

    Only processes tickers with a configured shares_source (skips SPY/BIL/VGK).
    """
    from engine.collect import COLLECTED_DIR, iter_date_dirs

    date_dirs = iter_date_dirs()
    if not date_dirs:
        log.warning("No collected/ directories found for shares backfill")
        return

    # Only backfill tickers with a shares source
    tickers_with_source = [
        ticker for ticker, meta in CAPITAL_FLOW_ETFS.items()
        if meta.get("shares_source") is not None
    ]
    if not tickers_with_source:
        log.warning("No tickers configured with shares_source")
        return

    all_dates = [d for d, _ in date_dirs]
    if not all_dates:
        return

    log.info(f"Backfilling shares outstanding: {len(tickers_with_source)} tickers "
             f"({', '.join(tickers_with_source)}), "
             f"{all_dates[0]} to {all_dates[-1]} ({len(all_dates)} date dirs)")

    # For GLD: pre-load the archive once (cached)
    gld_tickers = [t for t in tickers_with_source if CAPITAL_FLOW_ETFS[t].get("shares_source") == "spdr_gold"]
    if gld_tickers:
        log.info("  Pre-loading GLD archive...")
        _load_gld_archive()

    # Process each date directory
    updated_files = 0
    skipped_files = 0
    failed_files = 0

    for date_str, dir_path in date_dirs:
        subdir = os.path.join(dir_path, "capital_flow_etfs")
        if not os.path.isdir(subdir):
            continue

        for ticker in tickers_with_source:
            json_path = os.path.join(subdir, f"{ticker}.json")
            if not os.path.exists(json_path):
                continue

            # Read existing JSON
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Skip if already has Shares data
            if "Shares" in data and data["Shares"] and data["Shares"] > 0:
                skipped_files += 1
                continue

            # Fetch shares outstanding
            shares_val = _fetch_shares_for_ticker(ticker, date_str)

            if shares_val is None:
                failed_files += 1
                continue

            # Update in-place
            data["Shares"] = shares_val
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
            updated_files += 1

            # Rate limiting for iShares requests
            meta = CAPITAL_FLOW_ETFS[ticker]
            if meta.get("shares_source") == "ishares":
                time.sleep(0.5)

    log.info(f"Shares backfill complete: {updated_files} files updated, "
             f"{skipped_files} already had data, {failed_files} failed")


def load_capital_flow_etfs_from_collected(
    lookback_weeks: int | None = None,
    end_date: str | None = None,
) -> Dict[str, pd.DataFrame]:
    """Reconstruct OHLCV+Shares DataFrames from stored daily slices.

    Scans ``collected/YYYY/MM/DD/capital_flow_etfs/<TICKER>.json`` files and assembles them
    into per-ticker DataFrames matching the format returned by
    ``collect_capital_flow_etfs()``.

    Args:
        lookback_weeks: Number of weekly windows to cover (determines how far
            back to load).  Defaults to CAPITAL_FLOW_LOOKBACK_WEEKS.
        end_date: Latest date to include (YYYY-MM-DD).  Defaults to today.

    Returns:
        dict mapping ticker -> DataFrame[Open, High, Low, Close, Volume, Shares?]
        indexed by date, sorted chronologically.
    """
    from engine.collect import COLLECTED_DIR

    weeks = lookback_weeks or CAPITAL_FLOW_LOOKBACK_WEEKS
    from engine.utils.market_calendar import us_market_now
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else us_market_now()
    # Extra buffer for weekends/holidays (same as live fetch)
    calendar_days = weeks * 7 + 30
    start = end - timedelta(days=calendar_days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    if not os.path.isdir(COLLECTED_DIR):
        log.warning(f"No collected/ directory found — falling back to live fetch")
        return {}

    # Scan date directories in range
    from engine.collect import iter_date_dirs, read_per_ticker
    rows_by_ticker: Dict[str, list] = {}
    loaded_dates = 0

    for date_str, dir_path in iter_date_dirs():
        if date_str < start_str or date_str > end_str:
            continue
        try:
            daily = read_per_ticker("capital_flow_etfs", dir_path)
        except Exception as e:
            log.warning(f"Failed to read capital_flow_etfs from {dir_path}: {e}")
            continue
        if not daily:
            continue

        loaded_dates += 1
        for ticker, ohlcv in daily.items():
            if ticker not in rows_by_ticker:
                rows_by_ticker[ticker] = []
            row = {
                "Date": pd.Timestamp(date_str),
                "Open": float(ohlcv["Open"]),
                "High": float(ohlcv["High"]),
                "Low": float(ohlcv["Low"]),
                "Close": float(ohlcv["Close"]),
                "Volume": int(ohlcv["Volume"]),
            }
            if "Shares" in ohlcv:
                row["Shares"] = int(ohlcv["Shares"])
            rows_by_ticker[ticker].append(row)

    if not rows_by_ticker:
        log.warning(f"No capital_flow_etfs data found in collected/ "
                    f"({start_str} to {end_str}) — falling back to live fetch")
        return {}

    result: Dict[str, pd.DataFrame] = {}
    for ticker, rows in rows_by_ticker.items():
        df = pd.DataFrame(rows).set_index("Date").sort_index()
        result[ticker] = df

    log.info(f"Loaded capital flow ETF data from collected/: "
             f"{len(result)} tickers, {loaded_dates} trading days "
             f"({start_str} to {end_str})")
    return result
