"""Matches: one small, testable idea at a time.

Each match lists the extra parameters it needs, the variables that go into the
Buckingham analysis, the repeating variables, and what the result should be
compared against. Only Match 1 exists; the next match is designed after
looking at what this one shows.
"""

from .custom_params import CustomParam

MATCH_1 = {
    "name": "Match 1",
    "prefix": "m1",
    "idea": (
        "Crack growth is controlled by the stress intensity relative to the material's "
        "yield strength, and by a thermally activated rate. If so, data from different "
        "cold work levels and temperatures should fall closer to one band in "
        "π(CGR) = CGR·d/D against π(K) = K/(σy·√d) than in the raw CGR vs K plot."
    ),
    "params": [
        CustomParam(name="T_K", kind="formula", unit="K",
                    description="Test temperature in kelvin", formula="Temp + 273.15"),
        CustomParam(name="R", kind="constant", unit="J/(mol·K)",
                    description="Universal gas constant", value=8.314),
        CustomParam(name="sigma_y", kind="formula", unit="MPa",
                    description="Yield strength from %CW, MRP-458 Fig. 3-10 fit "
                                "(based on Type 304 data; applied to all grades)",
                    formula="-0.14465 * CW**2 + 20.892 * CW + 255.7"),
        CustomParam(name="Q", kind="constant", unit="J/mol",
                    description="Activation energy, value used in the MRP-458 disposition curve",
                    value=85000.0),
        CustomParam(name="d", kind="constant", unit="µm",
                    description="Grain size. PLACEHOLDER: one value for all rows, so it only "
                                "shifts the axes and cannot change the collapse",
                    value=50.0),
        CustomParam(name="D0", kind="constant", unit="m²/s",
                    description="Pre-exponential of the rate scale. PLACEHOLDER: constant, "
                                "only shifts the axes",
                    value=1e-6),
        CustomParam(name="D", kind="formula", unit="m²/s",
                    description="Thermally activated rate scale D = D0·exp(−Q/RT)",
                    formula="D0 * exp(-Q / (R * T_K))"),
    ],
    "variables": ["CGR", "K", "sigma_y", "d", "D", "Q", "R", "T_K"],
    "repeating": ["sigma_y", "d", "D", "R", "T_K"],
    "y": "CGR", "x": "K",            # groups built on these are plotted Y vs X
    "baseline": ("K", "CGR"),        # raw plot to beat: CGR vs K
}
