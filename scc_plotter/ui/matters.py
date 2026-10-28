"""📊 What matters: which parameters go together with CGR, once the others are
taken out (Kendall partial rank correlation with bootstrap ranges)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scc_core import correlation as corr
from ui import theme
from ui.common import Ctx, hint, next_step, show_fig, style_fig

TARGET = "CGR"
PHYSICS = ["K", "CW", "Temp", "O2", "H2"]          # test conditions, always controlled for
MEASUREMENT = ["Score", "dTime"]                    # how the test was run
CHEMISTRY = ["B", "Li"]                             # PWR water additives (often empty)
EXTRA = ["SO4", "Cl"]                               # impurities: shown, never controlled for
B_REPS = 1000


def settings() -> tuple[bool, bool]:
    st.session_state.setdefault("corr_measure", True)
    st.session_state.setdefault("corr_chem", False)
    return bool(st.session_state["corr_measure"]), bool(st.session_state["corr_chem"])


def controls_for(measure: bool, chem: bool, available) -> list[str]:
    c = PHYSICS + (MEASUREMENT if measure else []) + (CHEMISTRY if chem else [])
    return [v for v in c if v in available]


def candidates(available) -> list[str]:
    return [v for v in PHYSICS + MEASUREMENT + CHEMISTRY + EXTRA if v in available]


@st.cache_data(show_spinner="Calculating which parameters matter …")
def _table(df: pd.DataFrame, cands: tuple, ctrls: tuple) -> pd.DataFrame:
    return corr.table(df, TARGET, list(cands), list(ctrls), B=B_REPS)


@st.cache_data(show_spinner=False)
def _point(df: pd.DataFrame, target: str, x: str, ctrls: tuple) -> dict | None:
    return corr.point_estimate(df, target, x, list(ctrls))


def results(ctx: Ctx) -> pd.DataFrame:
    """The table for the current sidebar rows and settings (cached)."""
    measure, chem = settings()
    cols = list(dict.fromkeys([TARGET] + candidates(ctx.df.columns) + ["Lab", "CT_ID"]))
    df = ctx.df[[c for c in cols if c in ctx.df.columns]]
    df = df[df[TARGET] > 0]
    return _table(df, tuple(candidates(df.columns)), tuple(controls_for(measure, chem, df.columns)))


def badge(ctx: Ctx, x: str, y: str) -> None:
    """A one-line result box for a plot of y against x."""
    if x == y or x not in ctx.df or y not in ctx.df:
        return
    measure, chem = settings()
    label = ctx.label
    row = None
    if y == TARGET:
        tab = results(ctx)
        if not tab.empty and x in set(tab["parameter"]):
            row = tab.set_index("parameter").loc[x]
    if row is not None and np.isfinite(row.get("ptau", np.nan)):
        sign = "+" if row["ptau"] >= 0 else "−"
        clear = "clear" if row["clear"] else "uncertain"
        text = (f"<b>{label(x)} → {label(y)}</b> &nbsp; after removing other effects: "
                f"<b>τ = {sign}{abs(row['ptau']):.2f}</b> "
                f"<span style='opacity:.75'>[{row['ptau_lo']:+.2f} to {row['ptau_hi']:+.2f}]</span>"
                f" · {row['strength']}, {clear} &nbsp;|&nbsp; plain τ = {row['tau']:+.2f}"
                f" · {int(row['n'])} rows, {int(row['labs'])} labs")
        color = "#2a78d6" if row["ptau"] >= 0 else "#e34948"
        if not row["clear"]:
            color = "#9a9893"
    else:
        ctrls = controls_for(measure, chem, ctx.df.columns) if y == TARGET else []
        cols = list(dict.fromkeys([x, y] + ctrls + ["Lab", "CT_ID"]))
        df = ctx.df[[c for c in cols if c in ctx.df.columns]]
        p = _point(df, y, x, tuple(ctrls))
        if p is None or not np.isfinite(p["tau"]):
            return
        extra = (f" · after removing other effects τ = {p['ptau']:+.2f}" if ctrls else "")
        text = (f"<b>{label(x)} → {label(y)}</b> &nbsp; plain τ = <b>{p['tau']:+.2f}</b>"
                f" ({corr.strength(p['tau'])}){extra} · {p['n']} rows"
                f" <span style='opacity:.7'>· no range: open 📊 What matters for the full check</span>")
        color = "#9a9893"
    st.markdown(f"<div style='border-left:4px solid {color};padding:6px 10px;margin:2px 0 6px;"
                f"background:rgba(127,127,127,0.06);border-radius:4px;font-size:0.92rem'>"
                f"{text}</div>", unsafe_allow_html=True, help=hint("partial_tau"))


def subplot_note(ctx: Ctx, x: str, y: str) -> str:
    """Short τ note for small-multiple titles (only for y = CGR)."""
    if y != TARGET:
        return ""
    tab = results(ctx)
    if tab.empty or x not in set(tab["parameter"]):
        return ""
    r = tab.set_index("parameter").loc[x]
    if not np.isfinite(r.get("ptau", np.nan)):
        return ""
    return f"  ·  τ {r['ptau']:+.2f}{'' if r['clear'] else ' ?'}"


# --------------------------------------------------------------------------- page

def _rows_labs(df: pd.DataFrame, cols: list[str]) -> tuple[int, int]:
    sub = df[df[TARGET] > 0].dropna(subset=[TARGET] + cols)
    return len(sub), (sub["Lab"].nunique() if "Lab" in sub else 0)


def render(ctx: Ctx) -> None:
    df = ctx.df
    if TARGET not in df:
        st.warning("This page needs a CGR column.")
        return
    measure, chem = settings()
    avail = df.columns

    st.markdown("#### Which parameters go together with crack growth rate?")
    st.caption("For every parameter: how strongly CGR rises or falls with it **after the "
               "effects of the other parameters are taken out**. Uses the rows chosen in the "
               "sidebar.")

    # ---- settings with their visible effect on the data
    base = _rows_labs(df, controls_for(False, False, avail))
    with_m = _rows_labs(df, controls_for(True, False, avail))
    with_c = _rows_labs(df, controls_for(measure, True, avail))
    without_c = _rows_labs(df, controls_for(measure, False, avail))
    a, b = st.columns(2)
    with a:
        st.toggle("Also remove measurement effects (quality score, test duration)",
                  key="corr_measure",
                  help="How a test was run may change the measured CGR. On: the quality "
                       "score and test duration are taken out like the physical parameters. "
                       "Rows without a test duration are left out.")
        st.caption(f"Rows {base[0]} → {with_m[0]}, labs {base[1]} → {with_m[1]} when on.")
    with b:
        st.toggle("Also remove water chemistry (boron, lithium)", key="corr_chem",
                  help="On: B and Li are taken out too. Many tests have no B/Li values "
                       "(pure-water tests), so those rows are left out — check which labs "
                       "disappear below.")
        lost = df[(df[TARGET] > 0) & df["B"].isna()]["Lab"].value_counts().head(3) \
            if "B" in df and "Lab" in df else pd.Series(dtype=int)
        lost_txt = ", ".join(f"{k} {v}" for k, v in lost.items())
        st.caption(f"Rows {without_c[0]} → {with_c[0]}, labs {without_c[1]} → {with_c[1]} when "
                   f"on" + (f" (most rows lost: {lost_txt})." if lost_txt else "."))

    tab = results(ctx)
    if tab.empty or "ptau" not in tab:
        st.warning("Not enough rows with all values filled in. Loosen the sidebar filters.")
        return
    tab = tab[np.isfinite(tab["ptau"])].copy()
    distinct = {p: int(df[p].nunique()) for p in tab["parameter"]}
    tab["notes"] = [corr.notes(r, distinct.get(r["parameter"])) for _, r in tab.iterrows()]

    _summary(ctx, tab)
    show_fig(_dumbbell(ctx, tab))
    st.caption("○ plain link (everything else ignored)  →  ● after removing the other "
               "effects. The bar is the 95 % range from the bootstrap: if it crosses 0, the "
               "data cannot tell whether there is a real link. Grey band: too weak to matter.")
    _table_view(ctx, tab)

    with st.expander("How is this calculated?"):
        st.markdown(f"""
- **Kendall's τ** (tau-b): pick two tests at random; τ = chance they are in the same order
  for both quantities minus the chance they are in opposite order. τ = +0.30 means 65 % of
  pairs agree. It handles the many equal values in this data (e.g. CW = 20 %).
- **After removing other effects** = Kendall's *partial* τ (Kendall 1942): the link left
  over when the other parameters are held fixed. Taken out here: **{', '.join(ctx.label(c)
  for c in controls_for(measure, chem, avail))}**. SO₄ and Cl are shown but not taken out
  of the others.
- **95 % range**: bootstrap (Efron 1979), {B_REPS} resamples of whole specimens, because
  tests on the same specimen are not independent.
- **Spearman check**: the same idea with Spearman's ρ. Same sign = the result does not
  depend on the method.
- Only rows with every needed value filled in are used, so each row of the table says how
  many tests and labs it rests on.
""")
    next_step("look at the parameters whose dot sits far from 0 with a bar that does not "
              "cross 0. Then plot CGR against them in 👀 Look: the same result appears "
              "above that plot.")


def _summary(ctx: Ctx, tab: pd.DataFrame) -> None:
    lab = ctx.label
    clear = tab[tab["clear"] & (tab["ptau"].abs() >= 0.10)]
    pos = [f"**{lab(p)}**" for p in clear[clear["ptau"] > 0]["parameter"]]
    neg = [f"**{lab(p)}**" for p in clear[clear["ptau"] < 0]["parameter"]]
    mirage = [lab(r["parameter"]) for _, r in tab.iterrows()
              if any("mostly came from other parameters" in n for n in r["notes"])]
    parts = []
    if pos:
        parts.append("CGR clearly **rises** with " + ", ".join(pos))
    if neg:
        parts.append("clearly **falls** with " + ", ".join(neg))
    text = ("; ".join(parts) + ".") if parts else "No parameter shows a clear link with these rows."
    if mirage:
        text += " " + ", ".join(mirage) + (" looks related at first sight, but" if len(mirage) == 1
                                           else " look related at first sight, but") + \
                " that came from the other parameters."
    st.info(text, icon="🔎")


def _dumbbell(ctx: Ctx, tab: pd.DataFrame) -> go.Figure:
    t = tab.iloc[::-1]  # strongest at the top
    names = [ctx.label(p) for p in t["parameter"]]
    if theme.old_map_on():
        pos_c, neg_c, faint = "#2f4f7a", "#a3341f", "#a8977a"
    else:
        pos_c, neg_c, faint = "#2a78d6", "#e34948", "#9a9893"
    colors = [(pos_c if v >= 0 else neg_c) if c else faint for v, c in zip(t["ptau"], t["clear"])]
    fig = go.Figure()
    fig.add_vrect(x0=-0.1, x1=0.1, fillcolor="rgba(127,127,127,0.12)", line_width=0, layer="below")
    fig.add_vline(x=0, line=dict(color="rgba(127,127,127,0.7)", width=1))
    for name, a, b_ in zip(names, t["tau"], t["ptau"]):
        fig.add_trace(go.Scatter(x=[a, b_], y=[name, name], mode="lines", showlegend=False,
                                 line=dict(color="rgba(127,127,127,0.45)", width=2),
                                 hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=t["tau"], y=names, mode="markers", name="plain (everything else ignored)",
        marker=dict(symbol="circle-open", size=11, color="rgba(110,110,110,0.9)", line_width=2),
        hovertemplate="%{y}: plain τ = %{x:+.2f}<extra></extra>"))
    custom = np.stack([[f"{v:+.2f}" for v in t["ptau_lo"]], [f"{v:+.2f}" for v in t["ptau_hi"]],
                       [str(int(v)) for v in t["n"]], [str(int(v)) for v in t["labs"]],
                       list(t["strength"]), ["clear" if c else "uncertain" for c in t["clear"]],
                       ["<br>⚠ " + "<br>⚠ ".join(n) if n else "" for n in t["notes"]]], axis=1)
    fig.add_trace(go.Scatter(
        x=t["ptau"], y=names, mode="markers", name="after removing other effects",
        marker=dict(size=14, color=colors, line=dict(color="white", width=1.5)),
        error_x=dict(type="data", symmetric=False, array=t["ptau_hi"] - t["ptau"],
                     arrayminus=t["ptau"] - t["ptau_lo"], color="rgba(90,90,90,0.65)",
                     thickness=1.6, width=5),
        customdata=custom,
        hovertemplate="<b>%{y}</b><br>after removing other effects: τ = %{x:+.2f}"
                      "<br>95 % range %{customdata[0]} to %{customdata[1]}"
                      "<br>%{customdata[4]}, %{customdata[5]}"
                      "<br>%{customdata[2]} rows, %{customdata[3]} labs%{customdata[6]}"
                      "<extra></extra>"))
    lim = max(0.5, float(np.nanmax(np.abs(np.r_[t["tau"], t["ptau_lo"], t["ptau_hi"]]))) + 0.05)
    fig.update_xaxes(range=[-lim, lim], title="τ  (−: higher value → slower cracking · "
                                              "+: higher value → faster cracking)",
                     zeroline=False)
    fig.update_yaxes(title="")
    fig = style_fig(fig, height=110 + 42 * len(t))
    fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    return fig


def _table_view(ctx: Ctx, tab: pd.DataFrame) -> None:
    def effect(r):
        arrow = "↑ higher → faster" if r["ptau"] >= 0 else "↓ higher → slower"
        return f"{arrow} · {r['strength']}, {'clear' if r['clear'] else 'uncertain'}"
    out = pd.DataFrame({
        "parameter": [ctx.label(p) for p in tab["parameter"]],
        "what it means for CGR": [effect(r) for _, r in tab.iterrows()],
        "τ after removing others": [f"{r['ptau']:+.2f}  [{r['ptau_lo']:+.2f} … {r['ptau_hi']:+.2f}]"
                                    for _, r in tab.iterrows()],
        "plain τ": [f"{v:+.2f}" for v in tab["tau"]],
        "Spearman check": [f"{v:+.2f}" for v in tab["prho"]],
        "rows": tab["n"].astype(int), "labs": tab["labs"].astype(int),
        "notes": ["; ".join(n) for n in tab["notes"]],
    })
    st.dataframe(out, hide_index=True)
    st.download_button("Download this table (CSV)", out.to_csv(index=False).encode(),
                       file_name="what_matters.csv", mime="text/csv")
