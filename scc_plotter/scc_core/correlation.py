"""Which parameters go together with CGR? Kendall partial rank correlation.

Method (chosen with the tutor, following Kendall 1942, Biometrika 32, 277):

* Kendall's tau-b between every pair of variables. tau-b handles ties, which
  are everywhere in this data (CW = 20 % in 352 rows, O2 = 0 in most).
  Meaning: for two tests picked at random, tau = P(same order) − P(opposite
  order). tau = 0.30 means 65 % of pairs agree.
* Partial tau of CGR and X: the association left after the other chosen
  parameters ("controls") are taken out. Kendall showed that partial tau obeys
  the same formula as the ordinary partial correlation; with several controls
  we use the standard matrix form of that formula (inverse of the tau matrix).
* Partial Spearman (same idea with Spearman's rho) is reported as a check.
* Uncertainty: bootstrap (Efron 1979). Tests from the same specimen are not
  independent, so whole specimens are resampled, not single rows.

The bootstrap is done without re-ranking: a resample is a set of weights w
(how often each original row was drawn), and every pairwise sum becomes the
quadratic form wᵀ·P·w. All resamples are handled at once with a matrix product.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Plain-language strength of |tau| (a convention, not a law; tau runs lower than rho).
STRENGTH = ((0.10, "negligible"), (0.20, "weak"), (0.30, "moderate"), (np.inf, "strong"))


def strength(t: float) -> str:
    a = abs(t)
    return next(name for lim, name in STRENGTH if a < lim)


# --------------------------------------------------------------------------- core maths

def _sign_matrix(x: np.ndarray) -> np.ndarray:
    return np.sign(x[:, None] - x[None, :]).astype(np.float32)


def _tau_matrices(X: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Kendall tau-b matrices for every column of weights W (n × R) -> (R, k, k)."""
    n, k = X.shape
    S = [_sign_matrix(X[:, v]) for v in range(k)]
    W = W.astype(np.float32)
    Q = np.empty((W.shape[1], k, k))
    for v in range(k):
        for u in range(v, k):
            P = S[v] * S[u]                       # for u == v: 1 where the pair is not tied
            q = np.einsum("ir,ir->r", W, P @ W)   # wᵀ·P·w for every resample
            Q[:, v, u] = Q[:, u, v] = q
    d = np.sqrt(np.einsum("rii->ri", Q))
    with np.errstate(invalid="ignore", divide="ignore"):
        T = Q / (d[:, :, None] * d[:, None, :])
    return T


def _partial_first_row(M: np.ndarray) -> np.ndarray:
    """Partial correlation of variable 0 with each other variable, given all the rest.

    M: (R, k, k) correlation-like matrices. Returns (R, k); column 0 is NaN.
    """
    out = np.full(M.shape[:2], np.nan)
    for r in range(M.shape[0]):
        m = M[r]
        if not np.all(np.isfinite(m)):
            continue
        p = np.linalg.pinv(m)
        s = np.sqrt(np.clip(np.diag(p), 1e-12, None))
        out[r, 1:] = np.clip(-p[0, 1:] / (s[0] * s[1:]), -1, 1)
    return out


def _spearman_partial(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ranks = pd.DataFrame(X).rank().to_numpy()
    R = np.corrcoef(ranks, rowvar=False)
    return R[0], _partial_first_row(R[None])[0]


def _cluster_weights(groups: np.ndarray, B: int, rng) -> np.ndarray:
    """(n, B) bootstrap weights resampling whole groups (specimens)."""
    codes, inverse = np.unique(groups, return_inverse=True)
    m = len(codes)
    draws = rng.integers(0, m, size=(B, m))
    counts = np.stack([np.bincount(d, minlength=m) for d in draws], axis=1)  # (m, B)
    return counts[inverse]


# --------------------------------------------------------------------------- analysis

@dataclass
class Result:
    names: list[str]            # [target, x1, x2, ...]
    n: int
    labs: int
    tau: np.ndarray             # plain tau of target with each name (index 0 unused)
    ptau: np.ndarray            # partial tau
    tau_ci: np.ndarray          # (k, 2)
    ptau_ci: np.ndarray         # (k, 2)
    rho: np.ndarray             # plain Spearman
    prho: np.ndarray            # partial Spearman


def analyze(df: pd.DataFrame, target: str, variables: list[str], B: int = 300,
            group_col: str | None = "CT_ID", lab_col: str | None = "Lab",
            seed: int = 1) -> Result | None:
    """Partial correlations of `target` with each of `variables`, each controlled
    for all the others. Uses only rows where all of them are present."""
    names = [target] + [v for v in variables if v != target]
    sub = df.dropna(subset=names)
    if len(sub) < 10:
        return None
    X = sub[names].to_numpy(float)
    n = len(sub)
    rng = np.random.default_rng(seed)
    if group_col and group_col in sub and lab_col and lab_col in sub:
        g = (sub[lab_col].astype(str) + "|" + sub[group_col].astype(str)).to_numpy()
        g = np.where(sub[group_col].isna().to_numpy(), "row" + np.arange(n).astype(str), g)
    else:
        g = np.arange(n).astype(str)
    W = np.ones((n, 1))
    if B > 0:
        W = np.concatenate([W, _cluster_weights(g, B, rng)], axis=1)
    T = _tau_matrices(X, W)
    plain = T[:, 0, :]
    part = _partial_first_row(T)
    rho, prho = _spearman_partial(X)
    labs = sub[lab_col].nunique() if lab_col and lab_col in sub else 0
    k = len(names)
    if B > 0:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            tau_ci = np.nanpercentile(plain[1:], [2.5, 97.5], axis=0).T
            ptau_ci = np.nanpercentile(part[1:], [2.5, 97.5], axis=0).T
    else:
        tau_ci = ptau_ci = np.full((k, 2), np.nan)
    return Result(names, n, labs, plain[0], part[0], tau_ci, ptau_ci, rho, prho)


def table(df: pd.DataFrame, target: str, candidates: list[str], controls: list[str],
          B: int = 300, seed: int = 1, **kw) -> pd.DataFrame:
    """One row per candidate: CGR vs that parameter, controlled for `controls`.

    Candidates that are controls themselves come out of one shared analysis;
    every other candidate gets its own (control set + itself), so its row count
    can differ.
    """
    controls = [c for c in controls if c != target]
    rows = []
    shared = [c for c in candidates if c in controls]
    jobs = ([controls] if shared else []) + [controls + [c] for c in candidates
                                               if c not in controls]
    for variables in jobs:
        res = analyze(df, target, variables, B=B, seed=seed, **kw)
        wanted = shared if variables is controls else [variables[-1]]
        for x in wanted:
            if res is None:
                rows.append({"parameter": x, "n": 0})
                continue
            i = res.names.index(x)
            rows.append({
                "parameter": x, "ptau": res.ptau[i], "ptau_lo": res.ptau_ci[i, 0],
                "ptau_hi": res.ptau_ci[i, 1], "tau": res.tau[i], "tau_lo": res.tau_ci[i, 0],
                "tau_hi": res.tau_ci[i, 1], "rho": res.rho[i], "prho": res.prho[i],
                "n": res.n, "labs": res.labs,
                "controls": [c for c in res.names[1:] if c != x],
            })
    out = pd.DataFrame(rows)
    if out.empty or "ptau" not in out:
        return out
    out["clear"] = (out["ptau_lo"] > 0) | (out["ptau_hi"] < 0)
    out["strength"] = out["ptau"].map(lambda t: strength(t) if np.isfinite(t) else "")
    return out.sort_values("ptau", key=lambda s: -s.abs(), na_position="last").reset_index(drop=True)


def notes(row: pd.Series, distinct: int | None = None) -> list[str]:
    """Plain-language warnings for one table row."""
    out = []
    if not np.isfinite(row.get("ptau", np.nan)):
        return ["not enough data"]
    if abs(row["ptau"]) < 0.10 <= abs(row["tau"]) - 0.05:
        out.append("the plain link mostly came from other parameters")
    elif abs(row["tau"]) - abs(row["ptau"]) >= 0.15:
        out.append("the plain link partly came from other parameters")
    elif abs(row["ptau"]) - abs(row["tau"]) >= 0.10:
        out.append("hidden by other parameters until they were taken out")
    if np.sign(row["prho"]) != np.sign(row["ptau"]) and abs(row["ptau"]) >= 0.05:
        out.append("Spearman check disagrees in sign")
    if row["n"] < 100:
        out.append(f"only {int(row['n'])} rows")
    if row["labs"] and row["labs"] < 4:
        out.append(f"only {int(row['labs'])} labs")
    if distinct is not None and distinct < 4:
        out.append(f"only {distinct} different values")
    return out


def point_estimate(df: pd.DataFrame, target: str, x: str, controls: list[str]) -> dict | None:
    """Fast plain and partial tau for one pair (no bootstrap)."""
    variables = [x] + [c for c in controls if c not in (x, target)]
    res = analyze(df, target, variables, B=0)
    if res is None:
        return None
    return {"tau": res.tau[1], "ptau": res.ptau[1], "n": res.n, "labs": res.labs}
