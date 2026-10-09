"""Suggested plots for PWR stainless-steel SCC crack growth rate (CGR) data.

Each suggestion names the variables it needs; suggestions whose variables are
missing (e.g. a custom parameter that was deleted) are hidden by the app.
"""

SUGGESTIONS = [
    {
        "title": "CGR vs stress intensity K (log-log)",
        "x": "K", "y": "CGR", "color": "Material", "log_x": True, "log_y": True,
        "why": "Crack growth rate is usually described as a power law of the stress "
               "intensity factor, CGR = α·Kⁿ. On log-log axes a power law is a straight "
               "line whose slope is n, so look for straight bands per material.",
    },
    {
        "title": "Arrhenius plot: CGR vs 1000/T",
        "x": "invT_1000", "y": "CGR", "color": "Lab", "log_x": False, "log_y": True,
        "why": "SCC is thermally activated: CGR ∝ exp(−Q/RT). With log CGR against 1/T "
               "the slope is −Q/R, which gives the activation energy Q. Uses the custom "
               "parameter invT_1000 = 1000/(Temp + 273.15).",
    },
    {
        "title": "CGR vs cold work",
        "x": "CW", "y": "CGR", "color": "Material", "log_x": False, "log_y": True,
        "why": "In PWR primary water, unsensitised stainless steel cracks mainly when it "
               "is cold worked; cold work raises yield strength and CGR. Expect CGR to "
               "climb with %CW.",
    },
    {
        "title": "CGR vs dissolved hydrogen",
        "x": "H2", "y": "CGR", "color": "Lab", "log_x": False, "log_y": True,
        "why": "Dissolved hydrogen sets the electrochemical corrosion potential (ECP). "
               "Typical PWR chemistry is 25-50 cc/kg; values near 0 are often oxygenated "
               "or BWR-like tests.",
    },
    {
        "title": "CGR vs dissolved oxygen",
        "x": "O2", "y": "CGR", "color": "Lab", "log_x": False, "log_y": True,
        "why": "Oxygen raises the ECP and is known to speed up SCC strongly. Many points "
               "sit at 0 ppm, so a log X axis would drop them; keep X linear first.",
    },
    {
        "title": "CGR vs chloride",
        "x": "Cl", "y": "CGR", "color": "Lab", "log_x": False, "log_y": True,
        "why": "Anionic impurities (Cl⁻, SO₄²⁻) can accelerate cracking. Most tests are "
               "at 0 ppb, so check whether the few impurity tests stand out.",
    },
    {
        "title": "CGR vs sulfate",
        "x": "SO4", "y": "CGR", "color": "Lab", "log_x": False, "log_y": True,
        "why": "Same idea as chloride; sulfate is the other common impurity in the data.",
    },
    {
        "title": "Temperature vs cold work (test matrix)",
        "x": "CW", "y": "Temp", "color": "Lab", "log_x": False, "log_y": False,
        "why": "Not a result, a map of what was tested. Shows which combinations exist "
               "and which labs cover them, so you know where a trend could be biased by "
               "one lab.",
    },
    {
        "title": "CGR vs data quality score",
        "x": "Score", "y": "CGR", "color": "Lab", "log_x": False, "log_y": True,
        "why": "Score ranks data quality (1 = best). If low-quality data scatters much "
               "more, you may want to filter it out before looking for patterns.",
    },
    {
        "title": "Check: reported CGR vs Δa/Δt",
        "x": "CGR_from_da", "y": "CGR", "color": "Lab", "log_x": True, "log_y": True,
        "why": "Consistency check. CGR should equal crack extension divided by test time. "
               "Points far from the diagonal are worth a second look. Uses the custom "
               "parameter CGR_from_da = da / (dTime·3600).",
    },
]
