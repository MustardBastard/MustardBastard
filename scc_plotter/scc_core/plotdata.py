"""Filtering and plot preparation, kept free of any UI code so it can be tested."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Categorical colours, in fixed order (validated colour-blind-safe ordering).
# Colours follow the category, never its position after filtering.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
OTHER_COLOR = "#9a9893"
EMPTY_COLOR = "#cfcdc6"
SYMBOLS = ["circle", "square", "diamond", "triangle-up",
           "triangle-down", "cross", "x", "star"]
# Single-hue sequential ramp (light -> dark) for numeric colouring.
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

OTHER = "Other"
EMPTY = "(empty)"


@dataclass
class Filters:
    categories: dict[str, list[str]] = field(default_factory=dict)  # var -> allowed values
    ranges: dict[str, tuple[float, float]] = field(default_factory=dict)  # var -> (lo, hi)
    flags: list[str] = field(default_factory=list)  # flag vars that must be True


def apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for var, allowed in f.categories.items():
        if allowed:
            vals = df[var].astype("string").fillna(EMPTY)
            mask &= vals.isin(allowed)
    for var, (lo, hi) in f.ranges.items():
        # Rows with an empty cell in a range-filtered column are excluded.
        mask &= df[var].between(lo, hi)
    for var in f.flags:
        mask &= df[var].astype(bool)
    return df[mask]


@dataclass
class XYResult:
    data: pd.DataFrame
    n_total: int
    n_missing_x: int
    n_missing_y: int
    n_nonpositive: int  # dropped because a log axis cannot show values <= 0

    def summary(self) -> str:
        parts = [f"{len(self.data)} of {self.n_total} rows plotted"]
        if self.n_missing_x:
            parts.append(f"{self.n_missing_x} with empty X")
        if self.n_missing_y:
            parts.append(f"{self.n_missing_y} with empty Y")
        if self.n_nonpositive:
            parts.append(f"{self.n_nonpositive} with zero/negative values on a log axis")
        return " · ".join(parts)


def prepare_xy(df: pd.DataFrame, x: str, y: str, log_x: bool, log_y: bool) -> XYResult:
    n = len(df)
    miss_x = df[x].isna()
    miss_y = df[y].isna() & ~miss_x
    ok = ~(df[x].isna() | df[y].isna())
    nonpos = pd.Series(False, index=df.index)
    if log_x:
        nonpos |= ok & (df[x] <= 0)
    if log_y:
        nonpos |= ok & (df[y] <= 0)
    keep = ok & ~nonpos
    return XYResult(df[keep], n, int(miss_x.sum()), int(miss_y.sum()), int(nonpos.sum()))


def category_colors(full: pd.Series, max_colors: int = 8) -> tuple[pd.Series, dict[str, str], list[str]]:
    """Map a categorical column to display categories and colours.

    The most frequent categories in the *full* (unfiltered) data get the colour
    slots, so filtering never repaints a category. The rest fold into "Other".
    Returns (display series, colour map, legend order).
    """
    s = full.astype("string").fillna(EMPTY)
    counts = s[s != EMPTY].value_counts()
    top = list(counts.index[:max_colors])
    display = s.where(s.isin(top) | (s == EMPTY), OTHER)
    cmap = {c: CATEGORICAL[i % len(CATEGORICAL)] for i, c in enumerate(top)}
    order = list(top)
    if (display == OTHER).any():
        cmap[OTHER] = OTHER_COLOR
        order.append(OTHER)
    if (display == EMPTY).any():
        cmap[EMPTY] = EMPTY_COLOR
        order.append(EMPTY)
    return display, cmap, order


def coverage(df: pd.DataFrame, group: str, columns: list[str]) -> pd.DataFrame:
    """Percentage of non-empty cells per group (e.g. per Lab) and column."""
    g = df[columns].notna().groupby(df[group].astype("string").fillna(EMPTY))
    pct = g.mean() * 100
    pct["rows"] = g.size()
    return pct.sort_values("rows", ascending=False)


def is_discrete(col: pd.Series, max_levels: int = 12) -> bool:
    vals = col.dropna().unique()
    return len(vals) <= max_levels and np.all(np.mod(vals, 1) == 0)
