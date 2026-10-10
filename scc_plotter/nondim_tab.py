"""The "Nondimensionalize" tab: units → π groups → collapse score."""

from __future__ import annotations

import ast
from typing import Callable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from scc_core.collapse import collapse, valid_mask
from scc_core.custom_params import CustomParam
from scc_core.dimensional import (
    DimensionError, buckingham, formula_dims, is_dimensionless, si_formula,
)
from scc_core.loader import Dataset
from scc_core.matches import MATCH_1
from scc_core.plotdata import SEQUENTIAL, category_colors
from scc_core.units import DIMLESS, UnitError, format_dims, parse_unit, same_dims

NONE = "(none)"


def setup_match(match: dict, params: list[CustomParam], save: Callable[[], None]) -> None:
    """Button callback: add the match's parameters and pre-fill the selections."""
    have = {p.name for p in params}
    for p in match["params"]:
        if p.name not in have:
            params.append(CustomParam(**vars(p)))
    save()
    st.session_state["nd_vars"] = list(match["variables"])
    st.session_state["nd_rep"] = list(match["repeating"])
    st.session_state["nd_prefix"] = match["prefix"]
    st.session_state["nd_match"] = match["name"]


def render(ds: Dataset, df: pd.DataFrame, df_all: pd.DataFrame, params: list[CustomParam],
           unit_text: Callable[[str], str], set_unit: Callable[[dict], None],
           save_params: Callable[[], None], label: Callable[[str], str],
           show_fig: Callable, style_fig: Callable) -> None:
    cols = ds.columns
    numeric = [v for v in ds.numeric_vars() if v not in ("Index",)]
    candidates = numeric + list(ds.constants)

    st.subheader("Nondimensionalize")
    st.write(
        "Pick the variables you think matter. The app reads their units, works out the "
        "Buckingham π groups, and scores whether the data collapses onto one band. "
        "All groups are computed in SI units, so they are pure numbers."
    )

    # ------------------------------------------------------------------ the current match
    with st.container(border=True):
        st.markdown(f"**{MATCH_1['name']}** — {MATCH_1['idea']}")
        st.button(f"Set up {MATCH_1['name']}", on_click=setup_match,
                  args=(MATCH_1, params, save_params),
                  help="Adds T_K, R, sigma_y, Q, d, D0 and D as custom parameters (if missing) "
                       "and fills in the selections below.")

    # ------------------------------------------------------------------ 1. variables
    st.markdown("#### 1 · Variables and their units")
    st.session_state.setdefault("nd_vars", [])
    st.session_state["nd_vars"] = [v for v in st.session_state["nd_vars"] if v in candidates]
    chosen = st.multiselect("Variables (put the result you want to explain first, e.g. CGR)",
                            candidates, key="nd_vars", format_func=label)
    if not chosen:
        st.info("Choose at least two variables, or press the match button above.")
        return

    rows, units, bad = [], {}, []
    for v in chosen:
        text = unit_text(v)
        try:
            u = parse_unit(text)
            units[v] = u
            dims, to_si = format_dims(u.dims), (f"+{u.offset:g} K" if u.offset else f"× {u.scale:g}")
            status = ""
        except UnitError as exc:
            dims, to_si, status = "?", "?", f"⚠ {exc}. Edit the unit."
            bad.append(v)
        if not status:
            if v in ds.constants:
                status = "constant: shifts axes only"
            elif df[v].nunique(dropna=True) <= 1:
                status = "constant in these rows: shifts axes only"
            else:
                status = "ok"
        rows.append({"variable": v, "unit": text, "dimensions": dims, "to SI": to_si,
                     "status": status})
    table = pd.DataFrame(rows)
    edited = st.data_editor(
        table, hide_index=True, disabled=["variable", "dimensions", "to SI", "status"],
        key="nd_unit_editor",
        column_config={"unit": st.column_config.TextColumn(
            "unit (editable)", help="e.g. mm/s, MPa√m, °C, J/(mol·K), µm, m²/s. "
                                    "Leave empty for a dimensionless number.")},
    )
    changes = {r.variable: (r.unit or "").strip() for r in edited.itertuples()
               if (r.unit or "").strip() != unit_text(r.variable)}
    if changes:
        set_unit(changes)
        st.rerun()
    st.caption("Base dimensions: M mass, L length, T time, Θ temperature, N amount (mol). "
               "Unit corrections are saved in unit_overrides.json.")
    if bad:
        st.warning("Fix the units marked ⚠ before building groups.")
        return

    # ------------------------------------------------------------------ 2. groups
    st.markdown("#### 2 · π groups")
    D = np.array([units[v].dims for v in chosen]).T
    rank = int(np.linalg.matrix_rank(D))
    n_groups = len(chosen) - rank
    st.write(f"{len(chosen)} variables, {rank} independent dimensions → "
             f"**{n_groups} dimensionless group{'s' if n_groups != 1 else ''}**.")
    if n_groups == 0:
        st.warning("These variables cannot form any dimensionless group. Add a variable that "
                   "brings the missing dimensions (e.g. a stress, a length or a rate scale).")
        return
    st.session_state["nd_rep"] = [v for v in st.session_state.get("nd_rep", []) if v in chosen]
    rep = st.multiselect(f"Repeating variables (choose {rank}; empty = automatic)", chosen,
                         key="nd_rep", format_func=label,
                         help="The repeating variables are the 'scales' that every other "
                              "variable is measured against. Different choices give different, "
                              "equally valid groups.")
    try:
        res = buckingham(chosen, units, rep or None)
    except DimensionError as exc:
        st.error(str(exc))
        return
    if not rep:
        st.caption("Automatic choice: " + ", ".join(res.repeating))

    prefix = st.text_input("Name prefix for the groups", key="nd_prefix",
                           placeholder="pi") or "pi"
    existing = {p.name: p for p in params}
    group_rows = []
    for g in res.groups:
        name = f"{prefix}_{g.main}"
        consts = [v for v in g.exponents
                  if v in ds.constants or df[v].nunique(dropna=True) <= 1]
        note = ("contains constant " + ", ".join(consts) + " (shifts axes only)") if consts else ""
        group_rows.append({"name": name, "group": g.label(), "note": note})
    st.dataframe(pd.DataFrame(group_rows), hide_index=True)

    if st.button("Add these groups as parameters"):
        errors = []
        for g in res.groups:
            name, formula = f"{prefix}_{g.main}", g.formula(units)
            if name in existing:
                if existing[name].formula != formula:
                    errors.append(f"'{name}' already exists with a different formula; "
                                  "delete it first or use another prefix.")
                continue
            if name in cols:
                errors.append(f"'{name}' is already a column name.")
                continue
            params.append(CustomParam(name=name, kind="formula", unit="",
                                      description=f"π group: {g.label()}", formula=formula))
        if errors:
            st.error("\n\n".join(errors))
        else:
            save_params()
            st.rerun()

    with st.expander("Check a group of your own"):
        own = st.text_input("Formula", placeholder="e.g. CGR * d / D", key="nd_own")
        if own:
            all_units = {}
            for v in candidates:
                try:
                    all_units[v] = parse_unit(unit_text(v))
                except UnitError:
                    pass
            ok, info = is_dimensionless(own, all_units)
            if ok:
                st.success("Dimensionless ✓")
                a, b = st.columns([2, 1])
                own_name = a.text_input("Name", key="nd_own_name", placeholder="e.g. pi_mine")
                if b.button("Add as parameter", key="nd_own_add") and own_name:
                    if own_name in existing or own_name in cols:
                        st.error(f"'{own_name}' is already used.")
                    else:
                        params.append(CustomParam(
                            name=own_name, kind="formula", unit="",
                            description=f"π group: {own}", formula=si_formula(own, all_units)))
                        save_params()
                        st.rerun()
            else:
                st.error(f"Not dimensionless: {info}")

    # ------------------------------------------------------------------ 3. collapse
    st.markdown("#### 3 · Collapse score")
    st.write("Compare a plot of π groups with the raw plot it should improve on. Both are "
             "scored on exactly the same rows (current filters, all four values > 0).")
    groups_avail = [p.name for p in params if p.description.startswith("π group")
                    and p.name in df.columns]
    if not groups_avail:
        st.info("Add the groups as parameters first.")
        return

    def pick(text, key, opts, default):
        if st.session_state.get(key) not in opts:
            st.session_state[key] = default if default in opts else opts[0]
        return st.selectbox(text, opts, key=key, format_func=label)

    y_def = f"{prefix}_{MATCH_1['y']}"
    x_def = f"{prefix}_{MATCH_1['x']}"
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        py = pick("π plot: Y", "nd_group_Y", groups_avail, y_def)
    with c2:
        px_ = pick("π plot: X", "nd_group_X", groups_avail, x_def)
    with c3:
        by = pick("Raw plot: Y", "nd_raw_Y", numeric, MATCH_1["baseline"][1])
    with c4:
        bx = pick("Raw plot: X", "nd_raw_X", numeric, MATCH_1["baseline"][0])
    a, b = st.columns(2)
    degree = a.radio("Fitted curve", [1, 2], horizontal=True, key="nd_degree",
                     format_func={1: "straight line (power law)", 2: "curved (quadratic)"}.get)
    color_opts = (["Lab"] if "Lab" in df.columns else []) + [NONE] + groups_avail + numeric
    color = b.selectbox("Colour by", color_opts, key="nd_color", format_func=label)

    mask = valid_mask(df[py], df[px_], df[by], df[bx])
    sub = df[mask]
    labs = sub["Lab"] if "Lab" in sub.columns else None
    raw = collapse(sub[bx], sub[by], labs, degree)
    grp = collapse(sub[px_], sub[py], labs, degree)
    if raw is None or grp is None:
        st.warning("Not enough rows to score.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("Rows scored", raw.n)
    m2.metric("Scatter, π plot (decades)", f"{grp.scatter:.3f}",
              f"{grp.scatter - raw.scatter:+.3f} vs raw {raw.scatter:.3f}", delta_color="inverse")
    if grp.heldout is not None and raw.heldout is not None:
        m3.metric(f"Held-out labs ({grp.n_labs})", f"{grp.heldout:.3f}",
                  f"{grp.heldout - raw.heldout:+.3f} vs raw {raw.heldout:.3f}",
                  delta_color="inverse")
    change = (grp.scatter - raw.scatter) / raw.scatter
    held = (None if grp.heldout is None or raw.heldout is None
            else (grp.heldout - raw.heldout) / raw.heldout)
    if change <= -0.1 and (held is None or held <= -0.1):
        st.success(f"Tighter by {-change:.0%}, and it holds on labs left out of the fit. "
                   "A torch candidate.")
    elif change >= 0.1 or (held is not None and held >= 0.1):
        st.error(f"Looser ({change:+.0%} scatter"
                 + (f", {held:+.0%} on held-out labs" if held is not None else "")
                 + "). This grouping hides the pattern rather than revealing it.")
    else:
        st.warning(f"No real change ({change:+.0%} scatter"
                   + (f", {held:+.0%} on held-out labs" if held is not None else "")
                   + "). The groups do not explain more than the raw variables.")
    st.caption("Scatter = standard deviation of log10(Y) around the fitted curve; 0.3 decades "
               "is a factor of 2. Held-out = the curve is refitted without one lab at a time "
               "and tested on that lab. Constants in a group do not change either number.")

    left, right = st.columns(2)
    with left:
        show_fig(_fit_figure(sub, bx, by, raw, color, df_all, label, style_fig, "Raw"))
    with right:
        show_fig(_fit_figure(sub, px_, py, grp, color, df_all, label, style_fig, "π groups"))


def _fit_figure(sub, x, y, fit, color, df_all, label, style_fig, title):
    frame = sub.copy()
    kwargs = {}
    if color == "Lab":
        display, cmap, order = category_colors(df_all["Lab"], 8)
        frame["__cat"] = display.loc[frame.index]
        kwargs = dict(color="__cat", color_discrete_map=cmap,
                      category_orders={"__cat": order}, labels={"__cat": "Lab"})
    elif color != NONE:
        kwargs = dict(color=color, color_continuous_scale=SEQUENTIAL,
                      labels={color: label(color)})
    else:
        kwargs = dict(color_discrete_sequence=[SEQUENTIAL[4]])
    hover = [h for h in ("Lab", "Material", "excel_row") if h in frame.columns]
    fig = px.scatter(frame, x=x, y=y, log_x=True, log_y=True, hover_data=hover,
                     title=f"{title}: scatter {fit.scatter:.3f} decades",
                     **{**kwargs, "labels": {x: label(x), y: label(y), **kwargs.get("labels", {})}})
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color="#ffffff")))
    lx = np.linspace(np.log10(frame[x].min()), np.log10(frame[x].max()), 50)
    fig.add_trace(go.Scatter(x=10 ** lx, y=10 ** np.polyval(fit.coefs, lx), mode="lines",
                             line=dict(color="#0b0b0b", width=2), name="fit"))
    return style_fig(fig, height=460)


def formula_unit_problem(formula: str, declared: str, units_for: Callable[[str], object]) -> str:
    """Message if a formula's dimensions disagree with its declared unit, else ''."""
    try:
        dec = parse_unit(declared)
    except UnitError as exc:
        return f"Declared unit: {exc}"
    names = {n.id for n in ast.walk(ast.parse(formula, mode="eval")) if isinstance(n, ast.Name)}
    units = {}
    for n in names:
        u = units_for(n)
        if u is not None:
            units[n] = u
    try:
        got = formula_dims(formula, units) or DIMLESS
    except DimensionError as exc:
        return str(exc)
    if not same_dims(got, dec.dims):
        return (f"The formula gives {format_dims(got)}, but the unit '{declared}' is "
                f"{format_dims(dec.dims)}.")
    return ""
