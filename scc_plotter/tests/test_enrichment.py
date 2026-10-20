"""Tests for scc_core/enrichment.py. Run: python tests/test_enrichment.py (no xlsx needed)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scc_core import enrichment as en  # noqa: E402
from scc_core.custom_params import CustomParam, apply_params  # noqa: E402
from scc_core.loader import Dataset  # noqa: E402


def test_temperature_conversions():
    assert np.isclose(en.f_to_c(212), 100.0)
    assert np.isclose(en.f_to_c(32), 0.0)
    assert np.isclose(en.c_to_f(100), 212.0)
    assert np.isclose(en.c_to_k(25), 298.15)
    assert np.allclose(en.f_to_c(en.c_to_f([200, 288, 350])), [200, 288, 350])


def test_grade_normalization():
    cases = {"316L": "316L", "304": "304", "304L": "304L", "316NG": "316NG", "347": "347",
             "316SS 1": "316", "SUSF316HAZ": "316", "316*HAZ": "316", "304SS 3": "304",
             "316LN": None, "304LNSS": None, "321": None, "348": None, None: None,
             304: "304"}
    for raw, want in cases.items():
        assert en.normalize_grade(raw) == want, (raw, en.normalize_grade(raw))


def test_tables_hit_table_points_and_interpolate():
    t = en.PropertyTables.builtin()
    # At a table temperature the value is exact: 304 YS at 600 °F = 18.4 ksi.
    assert np.isclose(t.value("304", "YS", float(en.f_to_c(600))), 18.4 * en.KSI_TO_MPA)
    # E at 70 °F = 28.3 Msi = 195.1 GPa, same for every grade.
    assert np.isclose(t.value("316L", "E", float(en.f_to_c(70))), 195.1, atol=0.1)
    # Halfway between 500 and 600 °F: the mean of the two values.
    mid = float(en.f_to_c(550))
    assert np.isclose(t.value("316", "YS", mid), (20.0 + 18.9) / 2 * en.KSI_TO_MPA)
    # Strength falls with temperature; L grades are weaker than their parents.
    for g in en.GRADES:
        assert t.value(g, "YS", 340) < t.value(g, "YS", 200) < t.value(g, "YS", 40)
    assert t.value("304L", "YS", 290) < t.value("304", "YS", 290)
    # Unknown grade or outside the table -> NaN, never a guess.
    assert np.isnan(t.value(None, "YS", 290))
    assert np.isnan(t.value("304", "YS", 500))


def test_user_table_overrides_builtin():
    text = "grade,property,temp_C,value\n304,YS,0,300\n304,YS,400,200\n"
    t = en.PropertyTables.from_csv(text).merged_over(en.PropertyTables.builtin())
    assert np.isclose(t.value("304", "YS", 200), 250.0)            # user values
    assert np.isclose(t.value("316", "YS", 37.78), 30 * en.KSI_TO_MPA)  # built-in kept
    try:
        en.PropertyTables.from_csv("grade,temp_C,value\n304,0,1\n")
        raise AssertionError("accepted a table without a property column")
    except ValueError:
        pass


def test_yield_from_cold_work():
    assert np.isclose(en.yield_strength_from_cw(0), 255.7)
    assert np.isclose(en.yield_strength_from_cw(20), -0.14465 * 400 + 20.892 * 20 + 255.7)


def test_ni_nio_equation():
    # The values quoted in MRP-458 Fig. 1-10.
    assert np.allclose(en.h2_ni_nio([290, 325, 360]), [4.0, 10.4, 25.4], rtol=0.07)
    assert np.isclose(np.log10(en.h2_ni_nio(300)), 0.0111 * 300 - 2.59)


def test_water_properties():
    assert np.isclose(en.water_density_sat(298.15), 0.997, atol=0.002)
    assert np.isclose(en.water_density_sat(573.15), 0.712, atol=0.003)
    assert np.isclose(en.water_psat(373.15), 0.1014, atol=0.001)     # 100 °C
    assert np.isclose(en.pkw(298.15, 0.997), 14.0, atol=0.02)
    assert 11.1 < en.pkw(573.15) < 11.5                                 # 300 °C
    assert np.isclose(en.log_k_borate(298.15), 4.76, atol=0.02)       # pKa(boric acid) 9.24


def test_ph_model():
    # Pure water is neutral at every temperature.
    for t in (25, 288, 300, 325):
        assert np.isclose(en.ph_at(t, 0, 0), en.pkw(en.c_to_k(t)) / 2, atol=1e-3)
    # More lithium -> higher pH; more boron -> lower pH.
    assert en.ph_at(300, 1200, 3) > en.ph_at(300, 1200, 2)
    assert en.ph_at(300, 2000, 2) < en.ph_at(300, 500, 2)
    # Against values quoted in MRP-458 (Fig. 1-6: 1200 ppm B, 2.2 ppm Li, 288 °C ~ 6.79).
    # Known bias: this simple model reads 0.1-0.2 high (no polyborates).
    assert 0.0 < en.ph_at(288, 1200, 2.2) - 6.79 < 0.2
    assert np.isnan(en.ph_at(300, np.nan, 2))


def test_ecp_estimate():
    ph = en.ph_at(290, 1200, 2)
    e = en.ecp_hydrogen(290, ph, 25.0, 0.0)
    assert -0.85 < e < -0.65                            # typical PWR primary water
    assert en.ecp_hydrogen(290, ph, 50.0, 0.0) < e      # more H2 -> lower potential
    assert np.isnan(en.ecp_hydrogen(290, ph, 25.0, 2.0))   # oxygenated: not valid
    assert np.isnan(en.ecp_hydrogen(290, ph, 0.0, 0.0))    # no hydrogen: not valid


def test_composition():
    assert en.composition_value("316L", "Mo") == 2.5
    assert en.composition_value("304", "Mo") == 0.0
    assert en.composition_value("304L", "C") == 0.03
    assert en.composition_value("316NG", "N") == 0.08
    assert np.isnan(en.composition_value(None, "Cr"))


def _frame():
    return pd.DataFrame({
        "Material": ["304", "316SS 1", "321", "316L"],
        "Temp": [290.0, 325.0, 290.0, 360.0], "CW": [20.0, 10.0, 0.0, 20.0],
        "H2": [25.0, 0.0, 30.0, 30.0], "O2": [0.0, 2.0, 0.0, 0.0],
        "B": [1200.0, np.nan, 500.0, 1000.0], "Li": [2.0, np.nan, 2.0, 2.0],
    })


def test_every_property_computes():
    df = _frame()
    for p in en.PROPERTIES:
        s = en.compute(p.key, df)
        assert len(s) == len(df) and s.dtype == float, p.key
    ys = en.compute("YS_ann_T", df)
    assert np.isnan(ys[2])                    # 321 is not a target grade
    assert np.isnan(en.compute("pH_T", df)[1])          # B/Li empty
    assert np.isnan(en.compute("ECP_H2", df)[1])        # oxygenated row
    assert en.compute("YS_cw_T", df)[0] > ys[0]         # 20% CW is stronger than annealed


def test_enriched_parameters_in_dataset():
    df = _frame()
    ds = Dataset(df=df, columns={}, sheet="t", header_row=1)
    params = [CustomParam(name="E_T", kind="enriched", unit="GPa", property="E_T"),
              CustomParam(name="nope", kind="enriched", property="does_not_exist")]
    out, errors = apply_params(ds, params)
    assert "E_T" in out.df and out.columns["E_T"].unit == "GPa"
    assert len(errors) == 1 and errors[0].startswith("nope")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
