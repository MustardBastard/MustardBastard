"""🗂 Data → What matters for CGR: which parameters go together with CGR, once the others are
taken out (Kendall partial rank correlation with bootstrap ranges)."""

from __future__ import annotations

import ast

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scc_core import correlation as corr
from ui import theme
from ui.common import Ctx, hint, next_step, show_fig, style_fig

TARGET = "CGR"
OUTCOMES = {"CGR", "da"}                            # what is measured: never a cause
PHYSICS = ["K", "CW", "Temp", "O2", "H2"]          # test conditions
MEASUREMENT = ["Score", "dTime"]                    # how the test was run
CHEMISTRY = ["B", "Li"]                             # PWR water additives (often empty)
EXTRA = ["SO4", "Cl"]                               # impurities: shown, never held fixed
GROUPS = [("Physics", PHYSICS), ("Measurement", MEASUREMENT), ("Water chemistry", CHEMISTRY)]
RECOMMENDED = set(PHYSICS + MEASUREMENT)
ADDED = "Added quantities"
B_REPS = 1000


# --------------------------------------------------------------------------- settings

def _key(v: str) -> str:
    return f"hold_{v}"


def _depends_on_outcome(params, name: str, seen: set | None = None) -> bool:
    """True if a custom quantity is (directly or through others) made from CGR / da."""
    seen = seen or set()
    if name in OUTCOMES:
        return True
    if name in seen:
        return False
    seen.add(name)
    p = next((q for q in params if q.name == name), None)
    if p is None:
        return False
    names: set[str] = set()
    if p.kind == "formula" and p.formula:
        try:
            names = {n.id for n in ast.walk(ast.parse(p.formula, mode="eval"))
                     if isinstance(n, ast.Name)}
        except SyntaxError:
            return True
    elif p.kind == "lookup":
        names = {p.key_column}
    return any(_depends_on_outcome(params, n, seen) for n in names)


def added_quantities(ctx: Ctx) -> tuple[list[str], dict[str, str]]:
    """Quantities the user added (Data page) that can take part, and the ones left out."""
    cols = ctx.cols
    added = [c for c, info in cols.items() if info.source == "custom" and info.kind == "numeric"
             and c in ctx.df_all and c != TARGET]
    circular = {c for c in added if _depends_on_outcome(ctx.params, c)}
    base = [v for v in PHYSICS + MEASUREMENT + CHEMISTRY + EXTRA if v in ctx.df_all]
    usable, skipped = corr.screen_added(ctx.df_all, [c for c in added if c not in circular], base)
    for c in circular:
        skipped[c] = "made from the crack growth itself"
    reasons = {c: (r if r.startswith("made") or r.startswith("has")
                   else r.replace(r.split()[-1], ctx.label(r.split()[-1]))
                   + ", adds nothing new") for c, r in skipped.items()}
    return usable, reasons


def _options(ctx: Ctx) -> list[str]:
    """Every parameter that can be ticked, in display order."""
    base = [v for v in PHYSICS + MEASUREMENT + CHEMISTRY if v in ctx.df.columns]
    return base + added_quantities(ctx)[0]


def held_fixed(ctx: Ctx) -> list[str]:
    """The parameters ticked as 'held fixed' (defaults: physics and measurement)."""
    opts = _options(ctx)
    for v in opts:
        st.session_state.setdefault(_key(v), v in RECOMMENDED)
    return [v for v in opts if st.session_state[_key(v)]]


def is_recommended(ctx: Ctx) -> bool:
    return set(held_fixed(ctx)) == {v for v in _options(ctx) if v in RECOMMENDED}


def _reset(opts: list[str]) -> None:
    for v in opts:
        st.session_state[_key(v)] = v in RECOMMENDED


def candidates(ctx: Ctx) -> list[str]:
    base = [v for v in PHYSICS + MEASUREMENT + CHEMISTRY + EXTRA if v in ctx.df.columns]
    return base + added_quantities(ctx)[0]


@st.cache_data(show_spinner="Calculating which parameters matter …")
def _table(df: pd.DataFrame, cands: tuple, ctrls: tuple) -> pd.DataFrame:
    return corr.table(df, TARGET, list(cands), list(ctrls), B=B_REPS)


@st.cache_data(show_spinner=False)
def _point(df: pd.DataFrame, target: str, x: str, ctrls: tuple) -> dict | None:
    return corr.point_estimate(df, target, x, list(ctrls))


def results(ctx: Ctx) -> pd.DataFrame:
    """The table for the current sidebar rows and settings (cached)."""
    cands = candidates(ctx)
    cols = list(dict.fromkeys([TARGET] + cands + ["Lab", "CT_ID"]))
    df = ctx.df[[c for c in cols if c in ctx.df.columns]]
    df = df[df[TARGET] > 0]
    return _table(df, tuple(cands), tuple(held_fixed(ctx)))


def badge(ctx: Ctx, x: str, y: str) -> None:
    """A one-line result box for a plot of y against x."""
    if x == y or x not in ctx.df or y not in ctx.df:
        return
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
        ctrls = held_fixed(ctx) if y == TARGET else []
        cols = list(dict.fromkeys([x, y] + ctrls + ["Lab", "CT_ID"]))
        df = ctx.df[[c for c in cols if c in ctx.df.columns]]
        p = _point(df, y, x, tuple(c for c in ctrls if c != x))
        if p is None or not np.isfinite(p["tau"]):
            return
        extra = (f" · after removing other effects τ = {p['ptau']:+.2f}" if ctrls else "")
        text = (f"<b>{label(x)} → {label(y)}</b> &nbsp; plain τ = <b>{p['tau']:+.2f}</b>"
                f" ({corr.strength(p['tau'])}){extra} · {p['n']} rows"
                f" <span style='opacity:.7'>· no range: see 🗂 Data → What matters for CGR</span>")
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


def _cost(df: pd.DataFrame, held: list[str], v: str) -> str:
    """How many tests and labs holding v fixed costs, given the other ticks."""
    others = [c for c in held if c != v]
    a, b = _rows_labs(df, others), _rows_labs(df, others + [v])
    if a[0] == b[0]:
        return "costs no tests"
    labs = f" and {a[1] - b[1]} lab{'s' if a[1] - b[1] != 1 else ''}" if a[1] != b[1] else ""
    return f"{'costs' if v in held else 'would cost'} {a[0] - b[0]} tests{labs}"


def _short(ctx: Ctx, v: str) -> str:
    return {"Score": "quality score", "dTime": "test duration", "B": "boron",
            "Li": "lithium"}.get(v, ctx.label(v).split(" [")[0])


def settings_text(ctx: Ctx) -> str:
    """One line saying how the choice differs from the recommended one ('' if it does not)."""
    held = set(held_fixed(ctx))
    rec = {v for v in _options(ctx) if v in RECOMMENDED}
    plus = [_short(ctx, v) for v in _options(ctx) if v in held - rec]
    minus = [_short(ctx, v) for v in _options(ctx) if v in rec - held]
    parts = ([f"also held fixed: {', '.join(plus)}"] if plus else []) + \
            ([f"not held fixed: {', '.join(minus)}"] if minus else [])
    return "; ".join(parts)


def _hold_panel(ctx: Ctx, df: pd.DataFrame) -> None:
    opts = _options(ctx)
    held = held_fixed(ctx)
    usable, skipped = added_quantities(ctx)
    n, labs = _rows_labs(df, held)
    changed = settings_text(ctx)
    title = (f"⚙ Held fixed: {', '.join(_short(ctx, v) for v in held) or 'nothing'}"
             f"  ·  using {n} tests from {labs} labs" + ("  ·  ⚠ changed" if changed else ""))
    with st.expander(title, expanded=ctx.expert):
        st.caption("Ticked parameters are **held fixed** when the link of each *other* "
                   "parameter with CGR is judged. Every parameter keeps its own row in the "
                   "results either way: unticking only stops it being taken out of the "
                   "others. A test needs a value for every ticked parameter, so ticks can cost "
                   "tests; the grey text under each box says how many.")
        groups = [(g, [v for v in vs if v in opts]) for g, vs in GROUPS]
        if usable or skipped:
            groups.append((ADDED, usable))
        for group, vs in groups:
            left, right = st.columns([1, 4])
            left.markdown(f"**{group}**")
            with right:
                if vs:
                    cells = st.columns(min(len(vs), 5))
                    for i, v in enumerate(vs):
                        with cells[i % len(cells)]:
                            st.checkbox(_short(ctx, v) if v in RECOMMENDED | set(CHEMISTRY)
                                        else ctx.label(v), key=_key(v))
                            st.caption(_cost(df, held, v))
                if group == ADDED and skipped:
                    st.caption("Not offered: " + "; ".join(
                        f"{ctx.label(c)} ({r})" for c, r in skipped.items()))
                if group == ADDED and not vs and not skipped:
                    st.caption("None yet.")
        st.caption("SO₄ and Cl are shown in the results but never held fixed: most tests "
                   "have no value for them.")
        a, b = st.columns([1, 3])
        a.button("Reset to recommended", on_click=_reset, args=(opts,),
                 disabled=not changed)
        if changed:
            b.warning("Not the recommended choice (" + changed + "). The results below "
                      "change with it.", icon="⚠")


def render(ctx: Ctx) -> None:
    df = ctx.df
    if TARGET not in df:
        st.warning("This page needs a CGR column.")
        return

    st.markdown("#### Which parameters go together with crack growth rate?")
    st.caption("For every parameter: how strongly CGR rises or falls with it **after the "
               "effects of the other parameters are taken out**. Uses the rows chosen in the "
               "sidebar.")
    _hold_panel(ctx, df)
    held = held_fixed(ctx)

    tab = results(ctx)
    if tab.empty or "ptau" not in tab:
        st.warning("Not enough rows with all values filled in. Loosen the sidebar filters "
                   "or untick some parameters.")
        return
    tab = tab[np.isfinite(tab["ptau"])].copy()
    distinct = {p: int(df[p].nunique()) for p in tab["parameter"]}
    tab["notes"] = [corr.notes(r, distinct.get(r["parameter"])) for _, r in tab.iterrows()]
    tab["held"] = tab["parameter"].isin(held)

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
  over when the other parameters are held fixed. Held fixed here: **{', '.join(ctx.label(c)
  for c in held) or 'nothing'}** (change this in ⚙ above). SO₄ and Cl are shown but never
  held fixed.
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
    changed = settings_text(ctx)
    if changed:
        text += f" *(Not the recommended choice: {changed}.)*"
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
        "held fixed for the others": ["yes" if h else "" for h in tab["held"]],
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
