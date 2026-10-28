"""Tests for scc_core/correlation.py. Run: python tests/test_correlation.py (no xlsx needed)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scc_core import correlation as C  # noqa: E402


def tau_b_brute(x, y):
    """Textbook tau-b with an explicit loop over pairs."""
    conc = disc = tx = ty = 0
    n = len(x)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = np.sign(x[i] - x[j]), np.sign(y[i] - y[j])
            if a == 0 and b == 0:
                continue
            if a == 0:
                tx += 1
            elif b == 0:
                ty += 1
            elif a == b:
                conc += 1
            else:
                disc += 1
    return (conc - disc) / np.sqrt((conc + disc + tx) * (conc + disc + ty))


def test_tau_b_matches_textbook_with_ties():
    rng = np.random.default_rng(0)
    x = rng.integers(0, 5, 40).astype(float)      # many ties
    y = x + rng.integers(0, 4, 40)
    T = C._tau_matrices(np.column_stack([x, y]), np.ones((40, 1)))[0]
    assert np.isclose(T[0, 1], tau_b_brute(x, y))
    assert np.isclose(T[0, 0], 1.0)


def test_kendall_1942_worked_example():
    # Kendall's paper: tau12 = tau13 = 0.644, tau23 = 0.555 -> partial tau23.1 = 0.24.
    M = np.array([[1.0, 0.555, 0.644], [0.555, 1.0, 0.644], [0.644, 0.644, 1.0]])
    assert np.isclose(C._partial_first_row(M[None])[0, 1], 0.24, atol=0.005)


def test_kendall_1942_rankings():
    # The ten men ranked by intelligence (1), mathematics (2), music (3).
    r1 = np.arange(1, 11)
    r2 = np.array([1, 4, 5, 6, 2, 7, 3, 9, 8, 10])
    r3 = np.array([4, 1, 3, 5, 2, 6, 7, 10, 9, 8])
    T = C._tau_matrices(np.column_stack([r2, r3, r1]).astype(float), np.ones((10, 1)))[0]
    assert np.isclose(T[0, 2], 0.644, atol=0.001) and np.isclose(T[1, 2], 0.644, atol=0.001)
    assert np.isclose(T[0, 1], 0.556, atol=0.001)
    assert np.isclose(C._partial_first_row(T[None])[0, 1], 0.24, atol=0.005)


def test_weights_equal_duplicated_rows():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 3))
    w = rng.integers(0, 3, 30)
    weighted = C._tau_matrices(X, w[:, None].astype(float))[0]
    expanded = C._tau_matrices(np.repeat(X, w, axis=0), np.ones((w.sum(), 1)))[0]
    assert np.allclose(weighted, expanded)


def _confounded(n=400, seed=2):
    """CGR depends on O2 only; H2 looks related because H2 is high when O2 is 0."""
    rng = np.random.default_rng(seed)
    o2 = rng.choice([0.0, 0.0, 0.2, 2.0], n)
    h2 = np.where(o2 == 0, rng.uniform(20, 50, n), rng.uniform(0, 3, n))
    k = rng.uniform(15, 35, n)
    cgr = 1e-8 * (1 + 30 * o2) * k ** 2 * np.exp(rng.normal(0, 0.3, n))
    return pd.DataFrame({"CGR": cgr, "O2": o2, "H2": h2, "K": k,
                         "Lab": rng.choice(list("ABCDE"), n),
                         "CT_ID": [f"s{i // 4}" for i in range(n)]})


def test_partial_removes_a_mirage():
    tab = C.table(_confounded(), "CGR", ["O2", "H2", "K"], ["O2", "H2", "K"], B=200)
    r = tab.set_index("parameter")
    assert r.loc["H2", "tau"] < -0.3                  # looks strongly related ...
    assert abs(r.loc["H2", "ptau"]) < 0.1             # ... but it is not
    assert r.loc["O2", "clear"] and r.loc["K", "clear"]
    assert r.loc["K", "ptau_lo"] < r.loc["K", "ptau"] < r.loc["K", "ptau_hi"]
    assert "the plain link mostly came from other parameters" in C.notes(r.loc["H2"])


def test_extra_candidate_uses_its_own_rows():
    df = _confounded()
    df["Cl"] = np.where(np.arange(len(df)) % 2 == 0, np.nan, df["K"])
    tab = C.table(df, "CGR", ["O2", "K", "Cl"], ["O2", "K"], B=50).set_index("parameter")
    assert tab.loc["Cl", "n"] == len(df) // 2 and tab.loc["K", "n"] == len(df)


def test_point_estimate_and_strength_words():
    p = C.point_estimate(_confounded(), "CGR", "K", ["O2", "H2"])
    assert p["n"] == 400 and 0.1 < p["ptau"] < 0.6
    assert [C.strength(v) for v in (0.05, -0.15, 0.25, -0.4)] == \
        ["negligible", "weak", "moderate", "strong"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
