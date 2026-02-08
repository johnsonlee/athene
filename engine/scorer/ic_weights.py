"""IC-weighted averaging for sub-score and dimension aggregation.

Loads Information Coefficient (IC) data from ic.json and derives weights
proportional to each factor's predictive power.  Falls back to equal
weights when IC data is insufficient (< min_observations).

Weight formula per group:
    raw_weight = max(0.1, |mean_ic|)         # floor prevents zeroing out
    weight_i   = raw_weight_i / sum(raw_weights)

Blend-in: weights transition smoothly from equal-weight to IC-weight
over [min_observations, full_observations] to avoid ranking jumps.

Shrinkage: raw IC values are shrunk toward the grand mean IC of all
factors to reduce noise from small sample sizes.

Two usage layers:
    1. Metric-level (within sub-scores):  value = IC_weighted_avg(pe, fwd_pe, pb, ps)
    2. Sub-score-level (within dimensions): CT = IC_weighted_avg(trend, momentum, ...)
"""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd

from engine.config import OUTPUT_DIR
from engine.utils.logger import get_logger

log = get_logger(__name__)

_IC_HORIZON = 21           # use 21-day forward return IC by default
_MIN_OBSERVATIONS = 20     # minimum IC observations to trust the weights
_FULL_OBSERVATIONS = 40    # observations for full IC weighting (blend-in complete)
_WEIGHT_FLOOR = 0.1        # minimum raw weight to prevent zeroing out any factor


def _blend_factor(n_obs: int) -> float:
    """Compute blend-in coefficient for smooth equal→IC weight transition.

    Returns 0.0 when n_obs < _MIN_OBSERVATIONS (pure equal-weight),
    1.0 when n_obs >= _FULL_OBSERVATIONS (pure IC-weight),
    and linearly interpolates between.
    """
    if n_obs < _MIN_OBSERVATIONS:
        return 0.0
    if n_obs >= _FULL_OBSERVATIONS:
        return 1.0
    return (n_obs - _MIN_OBSERVATIONS) / (_FULL_OBSERVATIONS - _MIN_OBSERVATIONS)


def load_ic_weights(
    horizon: int = _IC_HORIZON,
    min_observations: int = _MIN_OBSERVATIONS,
) -> dict[str, float]:
    """Load IC-derived raw weights from ic.json.

    Returns a dict mapping factor name -> blended weight.  When observation
    count is in [min_obs, full_obs), the weight is a linear blend of
    equal-weight (1.0) and IC-weight (|shrunk_ic|, floored at 0.1).
    Factors with fewer than min_observations are omitted entirely.
    """
    ic_path = os.path.join(OUTPUT_DIR, "ic.json")
    if not os.path.exists(ic_path):
        return {}

    try:
        with open(ic_path, "r", encoding="utf-8") as f:
            ic_data: dict[str, Any] = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    factors = ic_data.get("factors", {})

    # First pass: collect raw |mean IC| for all qualifying factors
    raw_ics: dict[str, tuple[float, int]] = {}  # factor -> (|mean_ic|, count)
    for factor_name, horizons in factors.items():
        h_data = horizons.get(str(horizon), {})
        count = h_data.get("count", 0)
        mean_ic = h_data.get("mean")
        if count < min_observations or mean_ic is None:
            continue
        raw_ics[factor_name] = (abs(mean_ic), count)

    if not raw_ics:
        return {}

    # Shrinkage: pull each factor's |IC| toward the grand mean |IC|
    # shrinkage_coeff = min_obs / n_obs  (more shrinkage when fewer observations)
    grand_mean_ic = sum(ic for ic, _ in raw_ics.values()) / len(raw_ics)

    weights: dict[str, float] = {}
    for factor_name, (raw_ic, count) in raw_ics.items():
        shrinkage = min(1.0, min_observations / count)
        shrunk_ic = shrinkage * grand_mean_ic + (1.0 - shrinkage) * raw_ic
        ic_weight = max(_WEIGHT_FLOOR, shrunk_ic)

        # Blend-in: smooth transition from equal-weight to IC-weight
        alpha = _blend_factor(count)
        blended = alpha * ic_weight + (1.0 - alpha) * 1.0
        weights[factor_name] = blended

    return weights


def ic_weighted_avg(
    scores: dict[str, pd.Series],
    ic_weights: dict[str, float],
) -> pd.Series:
    """Compute IC-weighted average of score Series.

    Args:
        scores: mapping of factor name -> Series of per-ticker scores.
        ic_weights: mapping of factor name -> raw IC weight (from load_ic_weights).
            Factors missing from ic_weights get equal weight (1/n fallback).

    Returns:
        Series of weighted-average scores.
    """
    if not scores:
        return pd.Series(dtype=float)

    names = list(scores.keys())

    # Check how many factors in this group have IC weights
    have_ic = [n for n in names if n in ic_weights]

    if len(have_ic) == len(names):
        # All factors have IC data -> use IC-derived weights
        raw = {n: ic_weights[n] for n in names}
    else:
        # Not all factors have IC data -> fall back to equal weights
        raw = {n: 1.0 for n in names}

    # Normalize within group
    total = sum(raw.values())
    norm = {n: w / total for n, w in raw.items()}

    result = sum(norm[n] * scores[n] for n in names)
    return result


def trimmed_ic_weighted_avg(
    scores: dict[str, pd.Series],
    ic_weights: dict[str, float],
    drop: int = 1,
) -> pd.Series:
    """IC-weighted average with trimmed mean: drop the worst metric per ticker.

    For each ticker, the `drop` lowest-scoring metrics are excluded before
    computing the (IC-)weighted average of the remaining metrics.  This
    prevents a single bad metric from dragging the whole sub-score to neutral.

    Falls back to regular ic_weighted_avg when the group has ≤2 metrics
    (trimming 1 of 2 is too aggressive).
    """
    names = list(scores.keys())
    n = len(names)

    if drop <= 0 or n <= 2:
        return ic_weighted_avg(scores, ic_weights)

    # Build DataFrame: rows=tickers, cols=metrics
    df = pd.DataFrame(scores)

    # Resolve weights (IC or equal)
    have_ic = [name for name in names if name in ic_weights]
    if len(have_ic) == n:
        raw = {name: ic_weights[name] for name in names}
    else:
        raw = {name: 1.0 for name in names}

    # Vectorized fast path for equal-weight + drop=1:
    # trimmed_mean = (sum - min) / (n - 1)
    all_equal = len(set(raw.values())) == 1
    if all_equal and drop == 1:
        return (df.sum(axis=1) - df.min(axis=1)) / (n - 1)

    # General path: per-ticker drop-worst then IC-weighted avg
    result = pd.Series(0.0, index=df.index)
    for idx in df.index:
        row = df.loc[idx]
        keep = row.sort_values().index.tolist()[drop:]  # drop lowest
        kept_raw = {c: raw[c] for c in keep}
        total = sum(kept_raw.values())
        result[idx] = sum(kept_raw[c] / total * row[c] for c in keep)

    return result


def log_ic_status(
    group_name: str,
    factor_names: list[str],
    ic_weights: dict[str, float],
) -> None:
    """Log whether IC weighting is active or falling back for a group."""
    have_ic = [n for n in factor_names if n in ic_weights]

    if len(have_ic) == len(factor_names) and factor_names:
        raw = {n: ic_weights[n] for n in factor_names}
        total = sum(raw.values())
        norm = {n: w / total for n, w in raw.items()}
        parts = " ".join(f"{n.replace('_score', '')}={norm[n]:.2f}" for n in factor_names)
        # Check if weights are still blending in (close to equal)
        equal_w = 1.0 / len(factor_names)
        max_dev = max(abs(norm[n] - equal_w) for n in factor_names)
        blend_note = " (blending in)" if max_dev < 0.02 else ""
        log.info(f"IC weights: {group_name} active{blend_note} — {parts}")
    else:
        log.info(f"IC weights: {group_name} fallback to equal weights "
                 f"({len(have_ic)}/{len(factor_names)} factors have IC data)")
