"""Calibrate MA20/50 signal parameters from historical price data.

Loads price series from frontend/public/data/stocks/*.json (1593 days, 535 tickers),
computes rolling MA20/50 gap + slope and forward returns, then grid-searches
k_gap, k_slope, w_gap to maximise Spearman IC at 22-day horizon.

Usage:
    python -m engine.calibrate_ma_signal
    python -m engine.calibrate_ma_signal --horizon 10  # use 10d forward return
    python -m engine.calibrate_ma_signal --top 10      # show top-N results
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

STOCKS_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data" / "stocks"
SLOPE_LOOKBACK = 10   # days — must match technical.py _MA_SLOPE_LOOKBACK

# Grid axes
K_GAP_GRID   = [3, 5, 7, 10, 15, 20, 30]
K_SLOPE_GRID = [5, 10, 15, 20, 30, 50]
W_GAP_GRID   = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def _load_closes(path: Path) -> pd.Series | None:
    """Load daily close prices from a stock JSON file. Returns None if unusable."""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        prices = d.get("prices")
        if not prices or len(prices) < 60:
            return None
        s = pd.Series(
            {row["date"]: row["close"] for row in prices},
            dtype=float,
        ).sort_index()
        # Drop non-positive prices (data errors)
        return s[s > 0] if (s > 0).all() else s[s > 0]
    except Exception:
        return None


def build_panel(horizons: list[int]) -> pd.DataFrame:
    """Build a flat DataFrame of (ticker, date) rows with gap, slope, fwd_returns."""
    files = sorted(STOCKS_DIR.glob("*.json"))
    print(f"Loading {len(files)} tickers …")

    chunks: list[pd.DataFrame] = []
    skipped = 0
    for fp in files:
        close = _load_closes(fp)
        if close is None or len(close) < 60:
            skipped += 1
            continue

        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()

        gap   = (ma20 - ma50) / ma50
        slope = gap - gap.shift(SLOPE_LOOKBACK)

        df = pd.DataFrame({"gap": gap, "slope": slope})
        for h in horizons:
            df[f"fwd_{h}"] = close.pct_change(h).shift(-h)

        # Drop rows missing MA data or future returns
        df = df.dropna()
        if len(df) < 20:
            skipped += 1
            continue

        df["ticker"] = fp.stem
        chunks.append(df)

    print(f"Loaded {len(chunks)} tickers, skipped {skipped}")
    panel = pd.concat(chunks).reset_index(names="date")
    print(f"Panel size: {len(panel):,} rows  ({panel['date'].min()} → {panel['date'].max()})")
    return panel


def compute_signal(gap: np.ndarray, slope: np.ndarray,
                   k_gap: float, k_slope: float, w_gap: float) -> np.ndarray:
    return w_gap * np.tanh(k_gap * gap) + (1 - w_gap) * np.tanh(k_slope * slope)


def grid_search(panel: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Return DataFrame of (k_gap, k_slope, w_gap, ic, p_value) sorted by |ic|."""
    fwd_col = f"fwd_{horizon}"
    gap   = panel["gap"].to_numpy()
    slope = panel["slope"].to_numpy()
    fwd   = panel[fwd_col].to_numpy()

    total = len(K_GAP_GRID) * len(K_SLOPE_GRID) * len(W_GAP_GRID)
    print(f"\nGrid search: {total} combinations (horizon={horizon}d) …")

    rows = []
    for k_gap in K_GAP_GRID:
        for k_slope in K_SLOPE_GRID:
            for w_gap in W_GAP_GRID:
                sig = compute_signal(gap, slope, k_gap, k_slope, w_gap)
                r, p = spearmanr(sig, fwd)
                rows.append({"k_gap": k_gap, "k_slope": k_slope, "w_gap": round(w_gap, 2),
                             "ic": round(r, 4), "p": round(p, 4)})

    results = pd.DataFrame(rows).sort_values("ic", ascending=False)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=22)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    horizons = [5, 10, 22]
    panel = build_panel(horizons)

    for h in horizons:
        results = grid_search(panel, h)
        print(f"\n--- Top {args.top} by IC at {h}d horizon ---")
        print(results.head(args.top).to_string(index=False))
        print(f"Bottom {args.top} (negative IC = sells work):")
        print(results.tail(args.top).to_string(index=False))

    # Summary: best by target horizon
    best = grid_search(panel, args.horizon).iloc[0]
    print(f"\n{'='*60}")
    print(f"Optimal parameters for {args.horizon}d horizon:")
    print(f"  k_gap   = {best['k_gap']}")
    print(f"  k_slope = {best['k_slope']}")
    print(f"  w_gap   = {best['w_gap']}")
    print(f"  IC      = {best['ic']:.4f}  (p={best['p']:.4f})")
    print(f"\nUpdate engine/analyzers/technical.py:")
    print(f"  gap_norm   = result['ma_gap'].apply(lambda x: math.tanh({best['k_gap']} * x))")
    print(f"  slope_norm = result['ma_gap_slope'].apply(lambda x: math.tanh({best['k_slope']} * x))")
    print(f"  ma_trend_signal = {best['w_gap']} * gap_norm + {round(1-best['w_gap'],2)} * slope_norm")


if __name__ == "__main__":
    main()
