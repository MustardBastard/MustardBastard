"""Collapse score: how tightly do points fall on one curve in log-log space?

The score is the scatter of log10(Y) around a fitted curve, in decades
(0.3 decades = a factor of 2). Multiplying X or Y by a constant does not change
it, so placeholder constants in a π group cannot fake a better collapse.

The held-out score repeats the fit leaving out one lab at a time and measures
how well the curve predicts the lab it never saw. A real pattern holds up there;
a lucky one does not.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CollapseResult:
    n: int
    scatter: float          # SD of log10 residuals, decades
    heldout: float | None   # RMS of residuals on held-out labs, decades
    coefs: np.ndarray       # polynomial in log10(x), highest power first
    n_labs: int

    @property
    def factor(self) -> float:
        """Scatter as a multiplicative factor (1 SD)."""
        return 10 ** self.scatter


def valid_mask(*cols: pd.Series) -> pd.Series:
    m = pd.Series(True, index=cols[0].index)
    for c in cols:
        m &= c.notna() & np.isfinite(c) & (c > 0)
    return m


def collapse(x: pd.Series, y: pd.Series, groups: pd.Series | None = None,
             degree: int = 1, min_group: int = 3) -> CollapseResult | None:
    lx, ly = np.log10(x.to_numpy(float)), np.log10(y.to_numpy(float))
    n = len(lx)
    if n < degree + 3 or np.ptp(lx) == 0:
        return None
    coefs = np.polyfit(lx, ly, degree)
    res = ly - np.polyval(coefs, lx)
    scatter = float(np.sqrt((res ** 2).sum() / (n - degree - 1)))

    heldout, n_labs = None, 0
    if groups is not None:
        g = groups.astype("string").fillna("(empty)").to_numpy()
        errs = []
        for lab in np.unique(g):
            test = g == lab
            train = ~test
            if test.sum() < min_group or train.sum() < degree + 3 or np.ptp(lx[train]) == 0:
                continue
            c = np.polyfit(lx[train], ly[train], degree)
            errs.append(ly[test] - np.polyval(c, lx[test]))
            n_labs += 1
        if errs:
            e = np.concatenate(errs)
            heldout = float(np.sqrt((e ** 2).mean()))
    return CollapseResult(n, scatter, heldout, coefs, n_labs)
