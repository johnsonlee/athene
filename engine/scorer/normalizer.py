"""Z-score normalization with winsorization for factor scores."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from engine.config import WINSORIZE_LIMITS
from engine.utils.logger import get_logger

log = get_logger(__name__)


def zscore_normalize(
    series: pd.Series,
    winsorize: bool = True,
) -> pd.Series:
    """Z-score normalize a series, optionally winsorizing tails.

    - Drops NaN before computing stats
    - Winsorizes at configured percentiles to handle outliers
    - Returns z-scored series (NaN where original was NaN)
    """
    if series.dropna().empty:
        return pd.Series(0.0, index=series.index, name=series.name)

    values = series.copy()

    if winsorize and values.dropna().nunique() > 2:
        lower = values.dropna().quantile(WINSORIZE_LIMITS[0])
        upper = values.dropna().quantile(1 - WINSORIZE_LIMITS[1])
        values = values.clip(lower=lower, upper=upper)

    mean = values.mean()
    std = values.std()

    if std == 0 or pd.isna(std):
        return pd.Series(0.0, index=series.index, name=series.name)

    z = (values - mean) / std
    return z


def normalize_columns(
    df: pd.DataFrame,
    columns: list[str],
    suffix: str = "_z",
) -> pd.DataFrame:
    """Z-score normalize multiple columns, adding {col}{suffix} columns.

    Columns not present in df are silently skipped.
    """
    result = df.copy()
    normalized_count = 0

    for col in columns:
        if col not in result.columns:
            continue
        z_col = f"{col}{suffix}"
        result[z_col] = zscore_normalize(result[col])
        normalized_count += 1

    log.info(f"Normalized {normalized_count} columns")
    return result
