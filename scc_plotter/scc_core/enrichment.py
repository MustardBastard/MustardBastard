"""Data enrichment: properties that are not in the workbook, computed per row.

Three groups, each computed from the row's material grade, temperature and
water chemistry:

* Mechanical  – Young's modulus, yield and tensile strength at test temperature,
                from a built-in table modelled on ASME BPVC Section II Part D
                (Tables TM-1, Y-1, U), with optional user tables that override it.
* Chemistry   – Ni/NiO equilibrium hydrogen, pH at test temperature and at
                300 °C (B/Li solution model), and an estimated ECP for
                hydrogenated water.
* Composition – nominal composition of the grade from its specification ranges.

IMPORTANT – where the numbers come from
  The ASME values below are an approximate reproduction (ASME II-D is a licensed
  document and could not be checked here). They are minimum specified values
  for *annealed* material. Use `PropertyTables.from_csv` to replace them with
  values checked against your copy of the code or another database.
  The chemistry functions are published correlations, cited at each function.

Nothing here needs internet. `fetch_csv` can download a property table that a
user exported from a database (JRC MatDB, NIMS MatNavi, …), but those services
need an account and do not offer an open API, so no automatic scraping is done.
"""

from __future__ import annotations

import io
import math
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

GRADES = ("304", "304L", "316", "316L", "316NG", "347")
T_WINDOW_C = (200.0, 350.0)  # PWR operating window the tables are meant for

KSI_TO_MPA = 6.894757
MSI_TO_GPA = 6.894757


# --------------------------------------------------------------------------- temperature

def f_to_c(t_f):
    return (np.asarray(t_f, dtype=float) - 32.0) * 5.0 / 9.0


def c_to_f(t_c):
    return np.asarray(t_c, dtype=float) * 9.0 / 5.0 + 32.0


def c_to_k(t_c):
    return np.asarray(t_c, dtype=float) + 273.15


# --------------------------------------------------------------------------- grades

_GRADE_RE = re.compile(r"(304|316|347)(NG|LN|L)?", re.I)


def normalize_grade(material) -> str | None:
    """Map a free-text material name to one of GRADES, or None.

    '316SS 1', 'SUSF316HAZ', '316*HAZ' -> '316'; '304L' -> '304L'; '316NG' -> '316NG'.
    Nitrogen-alloyed LN variants and other grades (321, 348) are not mapped.
    """
    if material is None or (isinstance(material, float) and math.isnan(material)):
        return None
    m = _GRADE_RE.search(str(material).upper())
    if not m:
        return None
    base, suffix = m.group(1), (m.group(2) or "").upper()
    if suffix == "LN":
        return None
    if suffix == "NG":
        return "316NG" if base == "316" else None
    return base + suffix


# --------------------------------------------------------------------------- mechanical tables

# Temperatures of the strength tables (°F), as in ASME II-D.
_STRENGTH_T_F = [100, 200, 300, 400, 500, 600, 650, 700]

# Minimum yield strength, ksi (modelled on ASME II-D Table Y-1, plate SA-240).
_YS_KSI = {
    "304":   [30.0, 25.0, 22.4, 20.7, 19.4, 18.4, 18.0, 17.6],
    "304L":  [25.0, 21.4, 19.2, 17.5, 16.4, 15.5, 15.1, 14.8],
    "316":   [30.0, 25.9, 23.4, 21.4, 20.0, 18.9, 18.5, 18.2],
    "316L":  [25.0, 21.4, 19.2, 17.6, 16.4, 15.6, 15.2, 14.8],
    "316NG": [30.0, 25.9, 23.4, 21.4, 20.0, 18.9, 18.5, 18.2],  # as 316LN / 316
    "347":   [30.0, 27.6, 25.7, 24.1, 22.9, 22.0, 21.6, 21.4],
}
# Minimum tensile strength, ksi (modelled on ASME II-D Table U). Less certain.
_UTS_KSI = {
    "304":   [75.0, 71.0, 66.2, 64.0, 63.4, 63.4, 63.4, 63.4],
    "304L":  [70.0, 66.2, 60.9, 58.5, 57.5, 57.1, 57.0, 56.8],
    "316":   [75.0, 75.0, 72.9, 71.9, 71.9, 71.9, 71.9, 71.9],
    "316L":  [70.0, 67.8, 63.4, 61.9, 61.9, 61.9, 61.9, 61.9],
    "316NG": [75.0, 75.0, 72.9, 71.9, 71.9, 71.9, 71.9, 71.9],  # as 316LN / 316
    "347":   [75.0, 72.0, 67.6, 65.6, 64.9, 64.9, 64.9, 64.9],
}
# Young's modulus, Msi (modelled on ASME II-D Table TM-1, austenitic group G).
_E_T_F = [70, 200, 300, 400, 500, 600, 700]
_E_MSI = [28.3, 27.6, 27.0, 26.5, 25.8, 25.3, 24.8]


@dataclass
class PropertyTables:
    """Temperature tables for E, YS and UTS per grade, in °C and SI-ish units.

    tables[(grade, prop)] = (temps_C, values) with prop in {"E", "YS", "UTS"}
    (E in GPa, strengths in MPa). The grade "*" applies to every grade.
    """
    tables: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = field(default_factory=dict)
    source: str = "built-in (approx. ASME II-D)"

    @classmethod
    def builtin(cls) -> "PropertyTables":
        t = {}
        ts = f_to_c(_STRENGTH_T_F)
        for g in GRADES:
            t[(g, "YS")] = (ts, np.array(_YS_KSI[g]) * KSI_TO_MPA)
            t[(g, "UTS")] = (ts, np.array(_UTS_KSI[g]) * KSI_TO_MPA)
        t[("*", "E")] = (f_to_c(_E_T_F), np.array(_E_MSI) * MSI_TO_GPA)
        return cls(t)

    @classmethod
    def from_csv(cls, text_or_path) -> "PropertyTables":
        """Read a table with columns grade, property, temp_C, value.

        property is E (GPa), YS (MPa) or UTS (MPa); grade may be '*' for all.
        """
        if isinstance(text_or_path, (str, Path)) and Path(str(text_or_path)).exists():
            df = pd.read_csv(text_or_path)
        else:
            df = pd.read_csv(io.StringIO(str(text_or_path)))
        df.columns = [c.strip().lower() for c in df.columns]
        need = {"grade", "property", "temp_c", "value"}
        if not need <= set(df.columns):
            raise ValueError("A property table needs the columns: grade, property, temp_C, value")
        t = {}
        for (g, p), sub in df.groupby(["grade", "property"]):
            sub = sub.sort_values("temp_c")
            p = str(p).strip().upper()
            if p not in ("E", "YS", "UTS"):
                raise ValueError(f"Unknown property '{p}' (use E, YS or UTS)")
            t[(str(g).strip().upper(), p)] = (sub["temp_c"].to_numpy(float),
                                              sub["value"].to_numpy(float))
        return cls(t, source="user table")

    def merged_over(self, base: "PropertyTables") -> "PropertyTables":
        """This table where it has data, `base` everywhere else."""
        return PropertyTables({**base.tables, **self.tables},
                              source=f"{self.source} + {base.source}")

    def value(self, grade: str | None, prop: str, t_c: float) -> float:
        """Linear interpolation; NaN for unknown grades or outside the table."""
        if not isinstance(grade, str) or t_c is None or np.isnan(t_c):
            return float("nan")
        key = (grade.upper(), prop) if (grade.upper(), prop) in self.tables else ("*", prop)
        if key not in self.tables:
            return float("nan")
        ts, vs = self.tables[key]
        if t_c < ts.min() - 1e-9 or t_c > ts.max() + 1e-9:
            return float("nan")
        return float(np.interp(t_c, ts, vs))


def fetch_csv(url: str, timeout: float = 20.0) -> str:
    """Download a property table (CSV text) that a user exported from a database."""
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("Give a full http(s) address")
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (user's own URL)
        return resp.read().decode("utf-8", errors="replace")


def yield_strength_from_cw(cw_percent):
    """Room-temperature yield strength (MPa) from %CW: MRP-458 Fig. 3-10 fit (Type 304)."""
    cw = np.asarray(cw_percent, dtype=float)
    return -0.14465 * cw ** 2 + 20.892 * cw + 255.7


# --------------------------------------------------------------------------- water chemistry

def h2_ni_nio(t_c):
    """Dissolved H2 (cc/kg) at the Ni/NiO phase boundary.

    log10[H2]_eq = 0.0111·T(°C) − 2.59  (Attanasio & Morton, 2003; used in
    MRP-458 Fig. 1-10: 4 cc/kg at 290 °C, 10.4 at 325 °C, 25.4 at 360 °C).
    The boundary matters for nickel alloys; MRP-458 found no H2 effect for
    stainless steel in hydrogenated water.
    """
    return 10.0 ** (0.0111 * np.asarray(t_c, dtype=float) - 2.59)


_TC, _RHOC, _PC = 647.096, 322.0, 22.064  # water critical point (K, kg/m³, MPa)


def water_density_sat(t_k):
    """Saturated liquid water density, g/cm³ (Wagner & Pruss 1993, IAPWS).

    PWR water at 15.5 MPa is about 2% denser than saturated liquid at 300 °C;
    the effect on pKw is a few hundredths.
    """
    tau = 1.0 - np.asarray(t_k, dtype=float) / _TC
    b = (1.99274064, 1.09965342, -0.510839303, -1.75493479, -45.5170352, -6.74694450e5)
    e = (1 / 3, 2 / 3, 5 / 3, 16 / 3, 43 / 3, 110 / 3)
    s = 1.0 + sum(bi * tau ** ei for bi, ei in zip(b, e))
    return s * _RHOC / 1000.0


def water_psat(t_k):
    """Saturation vapour pressure of water, MPa (Wagner & Pruss 1993, IAPWS)."""
    t = np.asarray(t_k, dtype=float)
    tau = 1.0 - t / _TC
    a = (-7.85951783, 1.84408259, -11.7866497, 22.6807411, -15.9618719, 1.80122502)
    n = (1.0, 1.5, 3.0, 3.5, 4.0, 7.5)
    return _PC * np.exp(_TC / t * sum(ai * tau ** ni for ai, ni in zip(a, n)))


def pkw(t_k, rho=None):
    """−log10 of the ionization constant of water (Marshall & Franck 1981)."""
    t = np.asarray(t_k, dtype=float)
    rho = water_density_sat(t) if rho is None else np.asarray(rho, dtype=float)
    log_kw = (-4.098 - 3245.2 / t + 2.2362e5 / t ** 2 - 3.984e7 / t ** 3
              + (13.957 - 1262.3 / t + 8.5641e5 / t ** 2) * np.log10(rho))
    return -log_kw


def log_k_borate(t_k):
    """log10 K for B(OH)3 + OH⁻ ⇌ B(OH)4⁻ (Mesmer, Baes & Sweeton 1972)."""
    t = np.asarray(t_k, dtype=float)
    return 1573.21 / t + 28.6059 + 0.012078 * t - 13.2258 * np.log10(t)


def ph_at(t_c, b_ppm, li_ppm):
    """pH at temperature for a boric acid / lithium hydroxide solution.

    Ideal solution (activity coefficients 1), monomeric borate only, LiOH fully
    dissociated. Expect agreement with industry pH calculators within about
    0.1–0.2 pH units. B and Li are in ppm as the elements. Pure water: B = Li = 0.
    """
    t_k = c_to_k(t_c)
    b = np.asarray(b_ppm, dtype=float) / 10.811 / 1000.0   # mol/kg
    li = np.asarray(li_ppm, dtype=float) / 6.941 / 1000.0
    t_k, b, li = np.broadcast_arrays(t_k, b, li)
    kw = 10.0 ** (-pkw(t_k))
    k11 = 10.0 ** log_k_borate(t_k)
    lo, hi = np.full(t_k.shape, -14.0), np.full(t_k.shape, 0.0)   # log10[H+]
    for _ in range(70):
        mid = (lo + hi) / 2
        h = 10.0 ** mid
        oh = kw / h
        borate = b * k11 * oh / (1.0 + k11 * oh)
        f = li + h - oh - borate          # grows with h
        hi = np.where(f > 0, mid, hi)
        lo = np.where(f > 0, lo, mid)
    ph = -(lo + hi) / 2
    bad = ~(np.isfinite(t_k) & np.isfinite(b) & np.isfinite(li))
    return np.where(bad, np.nan, ph)


def henry_h2_mpa(t_k):
    """Henry constant of H2 in water, MPa per mole fraction (Fernández-Prini et al. 2003)."""
    t = np.asarray(t_k, dtype=float)
    tr = t / _TC
    tau = 1.0 - tr
    ln_k = -4.73284 / tr + 6.08954 * tau ** 0.355 / tr + 6.06066 * tr ** -0.41 * np.exp(tau)
    return water_psat(t) * np.exp(ln_k)


def ecp_hydrogen(t_c, ph_t, h2_cc_kg, o2_ppm=None, o2_limit_ppm=0.005):
    """Estimated ECP (V vs SHE) of steel in hydrogenated water.

    In deaerated, hydrogenated water the corrosion potential sits close to the
    H2/H2O equilibrium potential: E = −(ln10·RT/F)·pH_T − (RT/2F)·ln(p_H2/1 bar).
    NaN where oxygen is above `o2_limit_ppm` (5 ppb) or hydrogen is zero/unknown,
    because the estimate does not hold there.
    """
    t_k = c_to_k(t_c)
    r, f = 8.314462618, 96485.33212
    h2 = np.asarray(h2_cc_kg, dtype=float)
    n_h2 = h2 / 22414.0                         # mol/kg (STP cc)
    x = n_h2 / (n_h2 + 1000.0 / 18.01528)
    with np.errstate(divide="ignore", invalid="ignore"):
        p_bar = henry_h2_mpa(t_k) * x * 10.0
        e = -(math.log(10) * r * t_k / f) * np.asarray(ph_t, dtype=float) \
            - (r * t_k / (2 * f)) * np.log(p_bar)
    bad = ~(h2 > 0)
    if o2_ppm is not None:
        o2 = np.asarray(o2_ppm, dtype=float)
        bad |= ~(o2 <= o2_limit_ppm)
    return np.where(bad, np.nan, e)


# --------------------------------------------------------------------------- composition

# ASTM A240 ranges, wt% (min, max); None = no minimum. 316NG: nuclear grade,
# low carbon with controlled nitrogen (typical utility specification).
COMPOSITION = {
    "304":   {"C": (None, 0.07), "Cr": (17.5, 19.5), "Ni": (8.0, 10.5), "Mo": None,
              "Si": (None, 0.75), "N": (None, 0.10), "S": (None, 0.030)},
    "304L":  {"C": (None, 0.03), "Cr": (17.5, 19.5), "Ni": (8.0, 12.0), "Mo": None,
              "Si": (None, 0.75), "N": (None, 0.10), "S": (None, 0.030)},
    "316":   {"C": (None, 0.08), "Cr": (16.0, 18.0), "Ni": (10.0, 14.0), "Mo": (2.0, 3.0),
              "Si": (None, 0.75), "N": (None, 0.10), "S": (None, 0.030)},
    "316L":  {"C": (None, 0.03), "Cr": (16.0, 18.0), "Ni": (10.0, 14.0), "Mo": (2.0, 3.0),
              "Si": (None, 0.75), "N": (None, 0.10), "S": (None, 0.030)},
    "316NG": {"C": (None, 0.02), "Cr": (16.0, 18.0), "Ni": (10.0, 14.0), "Mo": (2.0, 3.0),
              "Si": (None, 0.75), "N": (0.06, 0.10), "S": (None, 0.030)},
    "347":   {"C": (None, 0.08), "Cr": (17.0, 19.0), "Ni": (9.0, 13.0), "Mo": None,
              "Si": (None, 0.75), "N": None, "S": (None, 0.030)},
}


def composition_value(grade: str | None, element: str) -> float:
    """Midpoint of a min–max range, the maximum for max-only limits, 0 if absent."""
    if not isinstance(grade, str) or grade not in COMPOSITION:
        return float("nan")
    rng = COMPOSITION[grade].get(element)
    if rng is None:
        return 0.0
    lo, hi = rng
    return hi if lo is None else (lo + hi) / 2.0


# --------------------------------------------------------------------------- registry

@dataclass(frozen=True)
class EnrichedProperty:
    key: str            # column name added to the data
    group: str          # "Mechanical", "Water chemistry", "Composition"
    label: str
    unit: str
    description: str
    needs: tuple[str, ...]   # workbook columns used


def _grades(df):
    return df["Material"].map(normalize_grade) if "Material" in df else pd.Series(None, index=df.index)


def _per_row(df, prop, tables):
    g = _grades(df)
    return pd.Series([tables.value(gi, prop, ti) for gi, ti in zip(g, df["Temp"])],
                     index=df.index, dtype=float)


def _ys_cw_t(df, tables):
    g = _grades(df)
    rt = pd.Series([tables.value(gi, "YS", 37.78) for gi in g], index=df.index)
    ratio = _per_row(df, "YS", tables) / rt
    return pd.Series(yield_strength_from_cw(df["CW"]), index=df.index) * ratio


def _ph_rows(df, t):
    ph = ph_at(t, df["B"], df["Li"])
    return pd.Series(ph, index=df.index)


_COMPUTE: dict[str, Callable[[pd.DataFrame, PropertyTables], pd.Series]] = {
    # One modulus table covers every austenitic grade, so E is filled for all rows.
    "E_T": lambda df, tb: pd.Series([tb.value("*", "E", t) for t in df["Temp"]],
                                    index=df.index, dtype=float),
    "YS_ann_T": lambda df, tb: _per_row(df, "YS", tb),
    "UTS_ann_T": lambda df, tb: _per_row(df, "UTS", tb),
    "YS_cw_RT": lambda df, tb: pd.Series(yield_strength_from_cw(df["CW"]), index=df.index),
    "YS_cw_T": _ys_cw_t,
    "H2_NiNiO": lambda df, tb: pd.Series(h2_ni_nio(df["Temp"]), index=df.index),
    "H2_over_NiNiO": lambda df, tb: pd.Series(
        np.log10(df["H2"].where(df["H2"] > 0) / h2_ni_nio(df["Temp"])), index=df.index),
    "pH_T": lambda df, tb: _ph_rows(df, df["Temp"]),
    "pH_300": lambda df, tb: _ph_rows(df, 300.0),
    "ECP_H2": lambda df, tb: pd.Series(
        ecp_hydrogen(df["Temp"], _ph_rows(df, df["Temp"]), df["H2"], df["O2"]), index=df.index),
}
for _el, _kind in (("Cr", "mid"), ("Ni", "mid"), ("Mo", "mid"), ("C", "max"), ("Si", "max"),
                   ("N", "mid/max"), ("S", "max")):
    _COMPUTE[f"{_el}_wt"] = (lambda el: lambda df, tb: pd.Series(
        [composition_value(g, el) for g in _grades(df)], index=df.index, dtype=float))(_el)

PROPERTIES: list[EnrichedProperty] = [
    EnrichedProperty("E_T", "Mechanical", "Young's modulus at test temperature", "GPa",
                     "Stiffness at T. Approx. ASME II-D TM-1: one table for all austenitic "
                     "steels, so every row gets a value.",
                     ("Temp",)),
    EnrichedProperty("YS_ann_T", "Mechanical", "Yield strength, annealed, at T", "MPa",
                     "Minimum specified yield strength of annealed plate at T (approx. ASME "
                     "II-D Y-1). Not the strength of cold-worked specimens.",
                     ("Material", "Temp")),
    EnrichedProperty("UTS_ann_T", "Mechanical", "Tensile strength, annealed, at T", "MPa",
                     "Minimum specified tensile strength of annealed plate at T (approx. ASME "
                     "II-D Table U).", ("Material", "Temp")),
    EnrichedProperty("YS_cw_RT", "Mechanical", "Yield strength from cold work (room T)", "MPa",
                     "MRP-458 Fig. 3-10 fit: YS from %CW (Type 304 data, all grades).", ("CW",)),
    EnrichedProperty("YS_cw_T", "Mechanical", "Yield strength from cold work, at T", "MPa",
                     "YS_cw_RT scaled by the annealed YS(T)/YS(room T) ratio of the grade. An "
                     "estimate: assumes cold-worked steel weakens with T like annealed steel.",
                     ("CW", "Material", "Temp")),
    EnrichedProperty("H2_NiNiO", "Water chemistry", "H₂ at the Ni/NiO boundary", "cc/kg",
                     "log10[H2]eq = 0.0111·T − 2.59 (Attanasio & Morton). Matters for nickel "
                     "alloys; MRP-458 found no H2 effect for stainless steel.", ("Temp",)),
    EnrichedProperty("H2_over_NiNiO", "Water chemistry", "Distance from Ni/NiO (log10)", "",
                     "log10(H2 / H2 at Ni/NiO). 0 = on the boundary, +1 = 10× more hydrogen. "
                     "Unit-free. Empty where H2 = 0.", ("H2", "Temp")),
    EnrichedProperty("pH_T", "Water chemistry", "pH at test temperature", "",
                     "B/Li solution model (ideal, monomeric borate). ±0.1–0.2. Empty where B "
                     "or Li is empty.", ("B", "Li", "Temp")),
    EnrichedProperty("pH_300", "Water chemistry", "pH at 300 °C", "",
                     "Same model at 300 °C, the usual reference for PWR chemistry.", ("B", "Li")),
    EnrichedProperty("ECP_H2", "Water chemistry", "Estimated ECP (hydrogen electrode)", "V",
                     "Volts vs SHE. H2/H2O equilibrium potential from pH_T and dissolved H2. "
                     "Empty where O2 > 5 ppb or H2 = 0, where it does not apply.",
                     ("H2", "O2", "B", "Li", "Temp")),
]
for _el, _what in (("Cr", "midpoint of the range"), ("Ni", "midpoint of the range"),
                   ("Mo", "midpoint of the range (0 if not alloyed)"),
                   ("C", "maximum allowed"), ("Si", "maximum allowed"),
                   ("N", "midpoint, or maximum allowed"), ("S", "maximum allowed")):
    PROPERTIES.append(EnrichedProperty(
        f"{_el}_wt", "Composition", f"{_el} content (specification)", "%",
        f"{_what}, from the grade's specification (ASTM A240; 316NG nuclear grade). "
        "Not the composition of the actual heat.", ("Material",)))

BY_KEY = {p.key: p for p in PROPERTIES}


def compute(key: str, df: pd.DataFrame, tables: PropertyTables | None = None) -> pd.Series:
    """Compute one enriched property for every row of `df`."""
    if key not in BY_KEY:
        raise KeyError(f"Unknown property '{key}'")
    missing = [c for c in BY_KEY[key].needs if c not in df.columns]
    if missing:
        raise KeyError(f"'{key}' needs the column(s) {', '.join(missing)}")
    return _COMPUTE[key](df, tables or PropertyTables.builtin()).astype(float)


def grade_report(df: pd.DataFrame) -> pd.DataFrame:
    """How each material name in the data maps to a grade, with row counts."""
    s = df["Material"].astype("string")
    out = s.value_counts(dropna=False).rename("rows").reset_index()
    out.columns = ["material", "rows"]
    out["grade"] = out["material"].map(lambda m: normalize_grade(m) or "— (not mapped)")
    return out
