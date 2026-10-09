"""SCC crack growth plotter.

Run with:   streamlit run app.py
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from scc_core.custom_params import (
    FUNCTIONS, CustomParam, FormulaError, apply_params, check_formula,
    load_params, save_params, valid_name,
)
from scc_core.loader import Dataset, load_workbook
from scc_core.plotdata import (
    EMPTY, OTHER, SEQUENTIAL, SYMBOLS, Filters, apply_filters, category_colors,
    coverage, is_discrete, prepare_xy,
)
from scc_core.suggestions import SUGGESTIONS

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
PARAMS_FILE = APP_DIR / "custom_parameters.json"
NONE = "(none)"

st.set_page_config(page_title="SCC Plotter", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
  .block-container {padding-top: 2rem; padding-bottom: 2rem;}
  [data-testid="stMetricValue"] {font-size: 1.6rem;}
  [data-testid="stMetric"] {background: #f1f0ec; border-radius: 10px; padding: 10px 14px;}
  [data-testid="stSidebar"] [data-testid="stExpander"] summary p {font-weight: 600;}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- helpers

@st.cache_data(show_spinner="Reading workbook ...")
def _load_bytes(data: bytes, sheet: str | None) -> Dataset:
    return load_workbook(io.BytesIO(data), sheet)


def show_fig(fig: go.Figure) -> None:
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:  # older Streamlit
        st.plotly_chart(fig, use_container_width=True)


def style_fig(fig: go.Figure, height: int = 620) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(itemsizing="constant"), hoverlabel=dict(namelength=-1),
    )
    fig.update_xaxes(showline=True, linecolor="#b5b3ad", gridcolor="#ecebe7", zeroline=False)
    fig.update_yaxes(showline=True, linecolor="#b5b3ad", gridcolor="#ecebe7", zeroline=False)
    return fig


def find_default_workbook() -> Path | None:
    for folder in (DATA_DIR, APP_DIR):
        files = sorted(folder.glob("*.xlsx")) if folder.exists() else []
        files = [f for f in files if not f.name.startswith("~$")]  # Excel lock files
        if files:
            return files[0]
    return None


def apply_suggestion(s: dict) -> None:
    st.session_state["x"] = s["x"]
    st.session_state["y"] = s["y"]
    st.session_state["color"] = s["color"]
    st.session_state["log_x"] = s["log_x"]
    st.session_state["log_y"] = s["log_y"]
    st.session_state["suggestion_note"] = f"**{s['title']}** — {s['why']}"


# --------------------------------------------------------------------------- data

st.sidebar.title("SCC Plotter")
st.sidebar.caption("PWR stainless steel · SCC crack growth rate")
default = find_default_workbook()
sb_file = st.sidebar.expander("Workbook", expanded=default is None)
uploaded = sb_file.file_uploader("Load a workbook (.xlsx)", type=["xlsx"])
if uploaded is not None:
    raw_bytes, source_name = uploaded.getvalue(), uploaded.name
else:
    if default is None:
        st.info("Upload the workbook in the sidebar, or put the .xlsx file in the "
                "`data` folder next to app.py so it loads automatically.")
        st.stop()
    raw_bytes, source_name = default.read_bytes(), default.name

base = _load_bytes(raw_bytes, None)
if "params" not in st.session_state:
    st.session_state["params"] = load_params(PARAMS_FILE)
params: list[CustomParam] = st.session_state["params"]
ds, param_errors = apply_params(base, params)
df_all = ds.df
cols = ds.columns
sb_file.caption(f"{source_name} · sheet '{ds.sheet}' · {len(df_all)} rows")


def label(var: str) -> str:
    if var == "excel_row":
        return "Excel row"
    return cols[var].label if var in cols else var


numeric = ds.numeric_vars()
categorical = [v for v in ds.categorical_vars() if cols[v].kind == "categorical"]
flags = [v for v, c in cols.items() if c.kind == "flag"]

# Make flags readable as categories for colouring.
for f in flags:
    df_all[f + "__label"] = df_all[f].map({True: "Yes", False: "No"})

# --------------------------------------------------------------------------- sidebar: axes

sb_plot = st.sidebar.expander("Axes & colour", expanded=True)
defaults = {"x": "K", "y": "CGR", "color": "Material", "log_x": False, "log_y": True}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)
# A deleted custom parameter could leave a stale selection behind.
for k in ("x", "y"):
    if st.session_state[k] not in numeric:
        st.session_state[k] = numeric[0]
color_options = [NONE] + categorical + flags + numeric
if st.session_state["color"] not in color_options:
    st.session_state["color"] = NONE

x = sb_plot.selectbox("X axis", numeric, key="x", format_func=label)
y = sb_plot.selectbox("Y axis", numeric, key="y", format_func=label)
c1, c2 = sb_plot.columns(2)
log_x = c1.checkbox("Log X", key="log_x")
log_y = c2.checkbox("Log Y", key="log_y")
color = sb_plot.selectbox("Colour by", color_options, key="color", format_func=label)
max_colors = sb_plot.slider(
    "Max colours (rest → 'Other')", 3, 8, 8,
    help="Categories beyond this many are grouped as 'Other'. Fewer colours are "
         "easier to tell apart.",
)
use_symbols = sb_plot.checkbox("Also vary marker shape", value=True,
                                  help="Helps tell colours apart, also in print.")

# --------------------------------------------------------------------------- sidebar: filters

sb_filt = st.sidebar.expander("Filters", expanded=True)


def reset_filters() -> None:
    for k in list(st.session_state):
        if k.startswith(("flag_", "cat_", "range_")):
            del st.session_state[k]


sb_filt.button("Reset filters", on_click=reset_filters)
filters = Filters()
for f in flags:
    if sb_filt.checkbox(f"Only {cols[f].name}", key=f"flag_{f}",
                           help=f"{cols[f].note} ({int(df_all[f].sum())} rows)"):
        filters.flags.append(f)
for var in [v for v in ("Lab", "Material", "Condition") if v in categorical]:
    options = sorted(df_all[var].astype("string").fillna(EMPTY).unique())
    chosen = sb_filt.multiselect(var, options, key=f"cat_{var}",
                                    placeholder="All")
    if chosen:
        filters.categories[var] = chosen
range_vars = sb_filt.multiselect(
    "Range filters on", numeric, key="range_vars", format_func=label,
    help="Add a slider for any numeric parameter. Rows with that cell empty are excluded.",
)
for var in range_vars:
    col = df_all[var].dropna()
    if col.empty:
        continue
    lo, hi = float(col.min()), float(col.max())
    if lo == hi:
        sb_filt.caption(f"{label(var)}: only value {lo:g}")
        continue
    if is_discrete(col):
        values = sorted(col.unique())
        a, b = sb_filt.select_slider(label(var), options=values, value=(values[0], values[-1]),
                                        key=f"range_{var}")
    else:
        a, b = sb_filt.slider(label(var), lo, hi, (lo, hi), key=f"range_{var}")
    filters.ranges[var] = (a, b)

df = apply_filters(df_all, filters)

# --------------------------------------------------------------------------- header

st.title("SCC crack growth explorer")
st.caption("Pick any two parameters in the sidebar, colour and filter them, and look for "
           "patterns. Open *Suggested plots* below for ready-made starting points.")
m1, m2, m3, m4 = st.columns(4)
m1.metric(f"Rows shown (of {len(df_all)})", len(df))
if "Lab" in df:
    m2.metric(f"Labs (of {df_all['Lab'].nunique()})", df["Lab"].nunique())
if "Material" in df:
    m3.metric(f"Materials (of {df_all['Material'].nunique()})", df["Material"].nunique())
m4.metric("Custom parameters", len(params))

# --------------------------------------------------------------------------- warnings

if param_errors:
    st.error("Some custom parameters could not be computed:\n\n- " + "\n- ".join(param_errors))
with st.expander(f"Data notes ({len(ds.warnings)})", expanded=False):
    st.write(f"Header found on Excel row {ds.header_row}. "
             f"{len(df)} of {len(df_all)} rows pass the current filters.")
    for w in ds.warnings:
        st.write("• " + w)


# --------------------------------------------------------------------------- tabs

tab_plot, tab_all, tab_cov, tab_params, tab_data = st.tabs(
    ["Plot", "Y vs every parameter", "Data coverage", "Custom parameters", "Data table"]
)


def color_args(frame: pd.DataFrame) -> dict:
    """Plotly-express keyword arguments for the chosen colour column."""
    if color == NONE:
        return {"color_discrete_sequence": [SEQUENTIAL[4]]}
    if color in numeric:
        return {"color": color, "color_continuous_scale": SEQUENTIAL,
                "labels": {color: label(color)}}
    src = color + "__label" if color in flags else color
    display, cmap, order = category_colors(df_all[src], max_colors)
    frame["__cat"] = display.loc[frame.index]
    args = {"color": "__cat", "color_discrete_map": cmap,
            "category_orders": {"__cat": order}, "labels": {"__cat": label(color)}}
    if use_symbols:
        args["symbol"] = "__cat"
        args["symbol_map"] = {c: SYMBOLS[i % len(SYMBOLS)] for i, c in enumerate(order)}
        args["symbol_map"].update({OTHER: "circle-open", EMPTY: "circle-open"})
    return args


HOVER = [v for v in ("Lab", "Material", "CT_ID", "Condition", "excel_row") if v in df_all.columns]

with tab_plot:
    with st.expander("Suggested plots", expanded=False):
        available = [s for s in SUGGESTIONS if s["x"] in numeric and s["y"] in numeric]
        for i, s in enumerate(available):
            a, b = st.columns([1, 3])
            a.button(s["title"], key=f"sugg_{i}", on_click=apply_suggestion, args=(s,))
            b.caption(s["why"])
    if note := st.session_state.get("suggestion_note"):
        st.info(note)

    res = prepare_xy(df, x, y, log_x, log_y)
    st.caption(res.summary())
    if res.data.empty:
        st.warning("Nothing to plot with the current choices.")
    else:
        frame = res.data.copy()
        cargs = color_args(frame)
        labels = {x: label(x), y: label(y), **{h: label(h) for h in HOVER},
                  **cargs.pop("labels", {})}
        fig = px.scatter(frame, x=x, y=y, log_x=log_x, log_y=log_y, hover_data=HOVER,
                         labels=labels, **cargs)
        fig.update_traces(marker=dict(size=9, opacity=0.85,
                                      line=dict(width=1, color="#ffffff")))
        show_fig(style_fig(fig))
        st.caption("Tip: drag to zoom, double-click to reset, click a legend entry to "
                   "hide it, camera icon saves a PNG.")


with tab_all:
    yy = st.selectbox("Y axis", numeric, index=numeric.index(y), format_func=label, key="all_y")
    log_yy = st.checkbox("Log Y", value=log_y, key="all_log_y")
    skip = {"Index", "excel_row", yy}
    xs = [v for v in numeric if v not in skip]
    ncols = 3
    nrows = math.ceil(len(xs) / ncols)
    titles = []
    for v in xs:
        r = prepare_xy(df, v, yy, False, log_yy)
        titles.append(f"{label(v)}  (n={len(r.data)})")
    fig = make_subplots(rows=nrows, cols=ncols, subplot_titles=titles,
                        vertical_spacing=0.35 / max(nrows, 1), horizontal_spacing=0.06)
    for i, v in enumerate(xs):
        r = prepare_xy(df, v, yy, False, log_yy)
        row, col = i // ncols + 1, i % ncols + 1
        fig.add_trace(go.Scatter(
            x=r.data[v], y=r.data[yy], mode="markers", showlegend=False,
            marker=dict(size=6, color=SEQUENTIAL[4], opacity=0.6),
            customdata=r.data[HOVER].astype(str).values if HOVER else None,
            hovertemplate=f"{label(v)}: %{{x}}<br>{label(yy)}: %{{y}}"
                          + "".join(f"<br>{h}: %{{customdata[{j}]}}" for j, h in enumerate(HOVER))
                          + "<extra></extra>",
        ), row=row, col=col)
        if log_yy:
            fig.update_yaxes(type="log", row=row, col=col)
    fig.update_annotations(font_size=12)
    show_fig(style_fig(fig, height=270 * nrows))
    st.caption(f"Y = {label(yy)} against every numeric parameter, with current filters. "
               "Use this to spot which parameters seem to matter before plotting them "
               "one by one.")


with tab_cov:
    groups = [v for v in categorical if v in ("Lab", "Material")] or categorical
    grp = st.selectbox("Group rows by", groups, key="cov_group")
    cov_cols = [v for v in numeric if cols[v].source == "excel" and v != "Index"]
    table = coverage(df, grp, cov_cols)
    z = table[cov_cols]
    fig = px.imshow(
        z.values, x=[label(c) for c in cov_cols],
        y=[f"{g} ({n})" for g, n in zip(z.index, table["rows"])],
        color_continuous_scale=SEQUENTIAL, zmin=0, zmax=100, text_auto=".0f", aspect="auto",
        labels=dict(color="% filled"),
    )
    fig.update_xaxes(side="top")
    show_fig(style_fig(fig, height=max(320, 28 * len(z) + 140)))
    st.caption("Percentage of rows with a value, per group and parameter (current filters). "
               "Shows which researchers left which columns empty.")


with tab_params:
    st.subheader("Custom parameters")
    st.write("Extra parameters live in `custom_parameters.json`, not in the workbook. "
             "Formulas can use the variable names below, constants and earlier custom "
             "parameters. Functions: " + ", ".join(f"`{f}`" for f in sorted(FUNCTIONS)) + ".")

    for i, p in enumerate(params):
        a, b = st.columns([5, 1])
        if p.kind == "constant":
            desc = f"= {p.value:g}"
        elif p.kind == "formula":
            desc = f"= `{p.formula}`"
        else:
            desc = f"lookup by {p.key_column} ({len(p.mapping)} values, default {p.default})"
        a.markdown(f"**{p.name}** [{p.unit}] · *{p.kind}* {desc}  \n{p.description}")
        if b.button("Delete", key=f"del_{i}"):
            params.pop(i)
            save_params(PARAMS_FILE, params)
            st.rerun()

    names_in_use = set(cols) | {p.name for p in params}

    def add_param(p: CustomParam) -> None:
        if not valid_name(p.name):
            st.error("Name must be letters, digits and _ only, not starting with a digit.")
        elif p.name in names_in_use:
            st.error(f"'{p.name}' is already used.")
        else:
            params.append(p)
            save_params(PARAMS_FILE, params)
            st.rerun()

    kind = st.radio("Add a new", ["formula", "constant", "lookup"], horizontal=True,
                    format_func={"formula": "Formula (new column)", "constant": "Constant",
                                 "lookup": "Value per category (e.g. elastic modulus per material)"}.get)
    if kind == "formula":
        with st.form("add_formula", clear_on_submit=False):
            a, b = st.columns(2)
            name = a.text_input("Name", placeholder="e.g. K_over_E")
            unit = b.text_input("Unit", placeholder="e.g. √m")
            formula = st.text_input("Formula", placeholder="e.g. K / E_mod")
            desc = st.text_input("Description (optional)")
            if st.form_submit_button("Add formula"):
                try:
                    check_formula(formula, names_in_use)
                    add_param(CustomParam(name=name, kind="formula", unit=unit,
                                          description=desc, formula=formula))
                except FormulaError as exc:
                    st.error(str(exc))
    elif kind == "constant":
        with st.form("add_constant"):
            a, b, c = st.columns(3)
            name = a.text_input("Name", placeholder="e.g. Q")
            value = b.number_input("Value", value=0.0, format="%g")
            unit = c.text_input("Unit")
            desc = st.text_input("Description (optional)")
            if st.form_submit_button("Add constant"):
                add_param(CustomParam(name=name, kind="constant", unit=unit,
                                      description=desc, value=value))
    else:
        key_col = st.selectbox("Category column", categorical,
                               index=categorical.index("Material") if "Material" in categorical else 0)
        cats = sorted(df_all[key_col].dropna().astype(str).unique())
        a, b, c = st.columns(3)
        name = a.text_input("Name", placeholder="e.g. E_mod", key="lk_name")
        unit = b.text_input("Unit", placeholder="e.g. GPa", key="lk_unit")
        default = c.number_input("Default for blank cells below", value=None, format="%g",
                                 key="lk_default")
        desc = st.text_input("Description / source (optional)", key="lk_desc")
        table = st.data_editor(
            pd.DataFrame({key_col: cats, "value": [None] * len(cats)}).astype({"value": "float"}),
            disabled=[key_col], hide_index=True, key=f"lk_table_{key_col}",
        )
        if st.button("Add lookup"):
            mapping = {str(k): float(v) for k, v in zip(table[key_col], table["value"])
                       if pd.notna(v)}
            add_param(CustomParam(name=name, kind="lookup", unit=unit, description=desc,
                                  key_column=key_col, mapping=mapping, default=default))

    st.subheader("Variable names")
    st.dataframe(pd.DataFrame([
        {"variable": c.var, "column": c.label, "type": c.kind, "source": c.source, "note": c.note}
        for c in cols.values()
    ]), hide_index=True)


with tab_data:
    show = [c for c in df.columns if not c.endswith("__label")]
    st.dataframe(df[show], hide_index=True)
    st.download_button("Download filtered rows (CSV)", df[show].to_csv(index=False).encode(),
                       file_name="filtered_rows.csv", mime="text/csv")
