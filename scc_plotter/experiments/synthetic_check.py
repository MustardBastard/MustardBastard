"""Synthetic-data check of 🗂 Data → "What matters for CGR" (Kendall partial τ + bootstrap).

The real workbook rows are kept (K, CW, Temp, O2, H2, Score, dTime, B, Li, labs,
specimens and every gap), but CGR is replaced by a law we choose, so the right
answer is known. Then the tool's own calculation is run many times.

Law: MRP-458 50th percentile curve, CGR = 1.50e-18 K^2.5 HV^6 exp(-85000/RT),
HV from %CW (MRP-458 sec. 3.1), x7 when O2 > 5 ppb (all-rows set only).
Scatter sizes were measured on the real data around that curve.

Run:  python experiments/synthetic_check.py [reps] [bootstrap]   (needs the xlsx)
Takes ~9 minutes with 200 reps and 500 bootstrap resamples.
"""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scc_core import correlation as C  # noqa: E402
from scc_core.loader import load_workbook  # noqa: E402

R = 8.314
XLSX = APP / "data" / "MRP-458_PWR-SCC-CGR-Database.xlsx"


def hv(cw):
    return -0.0638 * cw ** 2 + 7.268 * cw + 153.5


def load():
    df = load_workbook(XLSX).df.copy()
    df["CT_ID"] = df["Lab"].astype(str) + "|" + df["CT_ID"].astype(str)
    return df[df["CGR"] > 0].reset_index(drop=True)


def law(df, o2_factor=True):
    """MRP-458 50th percentile curve, log10 mm/s."""
    y = (np.log10(1.5e-18) + 2.5 * np.log10(df["K"]) + 6 * np.log10(hv(df["CW"]))
         - 85000 / (R * (df["Temp"] + 273.15)) / np.log(10))
    if o2_factor:
        y = y + np.where(df["O2"] > 0.005, np.log10(7), 0)
    return y
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
B = int(sys.argv[2]) if len(sys.argv) > 2 else 500
df = load()
SETS = {
  "Mainstream": dict(d=df[df["PWR_Mainstream_Data"] == True].reset_index(drop=True),
                     lab=0.26, spec=0.40, within=0.20, o2=False),
  "All rows":   dict(d=df, lab=0.25, spec=0.70, within=0.44, o2=True),
}
CANDS = ["K","CW","Temp","O2","H2","Score","dTime","B","Li"]
HELD = ["K","CW","Temp","O2","H2","Score","dTime"]
SCEN = {
  "A pure noise":                dict(law=False, lab="none"),
  "B lab+specimen noise only":   dict(law=False, lab="random"),
  "C MRP-458 law, no labs":      dict(law=True,  lab="none"),
  "D law + random lab offsets":  dict(law=True,  lab="random"),
  "E law + real lab offsets":    dict(law=True,  lab="real"),
  "F law + labs + Score effect": dict(law=True,  lab="random", score=-0.15),
}
def truth(name, sset):
    t = {"K": 1, "CW": 1, "Temp": 1}
    if sset["o2"]: t["O2"] = 1
    if "score" in SCEN[name]: t["Score"] = -1
    return t
out = {}
for sname, s in SETS.items():
    d = s["d"]; base = law(d, s["o2"]).to_numpy()
    real_off = (np.log10(d["CGR"]) - base).groupby(d["Lab"]).transform("mean").to_numpy()
    labs = d["Lab"].astype(str).to_numpy(); spec = d["CT_ID"].to_numpy()
    li, ulab = pd.factorize(pd.Series(labs).fillna("?")); si, uspec = pd.factorize(pd.Series(spec).fillna("?"))
    for scn, cfg in SCEN.items():
        rng = np.random.default_rng(7)
        rows = []
        for r in range(REPS):
            sp = s["spec"] if cfg["lab"] != "none" else np.hypot(s["spec"], s["lab"])
            y = (base if cfg["law"] else 0) + rng.normal(0, sp, len(uspec))[si] + rng.normal(0, s["within"], len(d))
            if cfg["lab"] == "random": y = y + rng.normal(0, s["lab"], len(ulab))[li]
            if cfg["lab"] == "real": y = y + real_off
            if "score" in cfg: y = y + cfg["score"] * (d["Score"].to_numpy() - 2)
            dd = d[CANDS + ["Lab", "CT_ID"]].copy(); dd["CGR"] = 10 ** y
            tab = C.table(dd, "CGR", CANDS, HELD, B=B, seed=r + 1).set_index("parameter")
            for p in CANDS:
                if p in tab.index and np.isfinite(tab.loc[p, "ptau"]):
                    rows.append(dict(rep=r, p=p, **{k: float(tab.loc[p, k]) for k in ("tau","ptau","ptau_lo","ptau_hi")}))
        res = pd.DataFrame(rows); t = truth(scn, s)
        summ = {}
        for p, g in res.groupby("p"):
            ref = g["ptau"].mean()
            clear_pos = ((g["ptau_lo"] > 0)).mean(); clear_neg = ((g["ptau_hi"] < 0)).mean()
            summ[p] = dict(truth=t.get(p, 0), mean_ptau=round(ref, 3), sd_ptau=round(g["ptau"].std(), 3),
                           mean_ci_width=round((g["ptau_hi"]-g["ptau_lo"]).mean(), 3),
                           mean_tau=round(g["tau"].mean(), 3),
                           clear_pos=round(clear_pos, 3), clear_neg=round(clear_neg, 3),
                           coverage=round(((g["ptau_lo"] <= ref) & (ref <= g["ptau_hi"])).mean(), 3))
        out[f"{sname} | {scn}"] = summ
        print(sname, "|", scn, flush=True)
        print(pd.DataFrame(summ).T.to_string(), flush=True)
json.dump(out, open(APP / "experiments" / f"results_{REPS}_{B}.json", "w"), indent=1)
