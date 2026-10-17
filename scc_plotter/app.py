"""SCC Plotter.

Run with:   streamlit run app.py
"""

from __future__ import annotations

import io
from pathlib import Path

import streamlit as st

from scc_core.custom_params import (
    CustomParam, apply_params, load_params, load_unit_overrides, save_params,
    save_unit_overrides, valid_name,
)
from scc_core.loader import Dataset, load_workbook
from scc_core.plotdata import EMPTY, Filters, apply_filters, is_discrete
from scc_core.units import UnitError, parse_unit
from ui import data as data_page
from ui import learn as learn_page
from ui import look as look_page
from ui import theme, tutorial
from scc_core.matches import MATCH_1
from ui.common import AREAS, DATA, LEARN, LOOK, Ctx, hint

VERSION = 6

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
PARAMS_FILE = APP_DIR / "custom_parameters.json"
UNITS_FILE = APP_DIR / "unit_overrides.json"

# Widget choices that must survive while their page is not shown. Streamlit forgets
# the value of a widget that is not drawn in a run; writing it back keeps it.
KEEP = ("x", "y", "color", "log_x", "log_y", "look_view", "max_colors", "use_symbols",
        "x3", "y3", "z3", "log_x3", "log_y3", "log_z3",
        "data_view", "cov_group", "learn_article", "add_kind", "range_vars")
KEEP_PREFIXES = ("flag_", "cat_", "range_")

st.set_page_config(page_title="SCC Plotter", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
  .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
  [data-testid="stMetricValue"] {font-size: 1.5rem;}
  div[role="radiogroup"] label p {font-size: 1.02rem;}
</style>
""", unsafe_allow_html=True)

for k in list(st.session_state.keys()):
    if k in KEEP or k.startswith(KEEP_PREFIXES):
        st.session_state[k] = st.session_state[k]


# --------------------------------------------------------------------------- data

@st.cache_data(show_spinner="Reading workbook ...")
def _load_bytes(data: bytes, sheet: str | None) -> Dataset:
    return load_workbook(io.BytesIO(data), sheet)


def find_default_workbook() -> Path | None:
    for folder in (DATA_DIR, APP_DIR):
        files = sorted(folder.glob("*.xlsx")) if folder.exists() else []
        files = [f for f in files if not f.name.startswith("~$")]  # Excel lock files
        if files:
            return files[0]
    return None


default = find_default_workbook()
sb_file = st.sidebar.expander("Workbook", expanded=default is None)
uploaded = sb_file.file_uploader("Load a workbook (.xlsx)", type=["xlsx"])
if uploaded is not None:
    raw_bytes, source_name = uploaded.getvalue(), uploaded.name
elif default is not None:
    raw_bytes, source_name = default.read_bytes(), default.name
else:
    st.title("SCC Plotter")
    st.info("Put the workbook (.xlsx) in the `data` folder next to app.py, or upload it in "
            "the sidebar under **Workbook**.")
    st.stop()

base = _load_bytes(raw_bytes, None)
def _drop_match1(params: list[CustomParam]) -> list[CustomParam]:
    """Version 5 removed the match page: remove what Match 1 created on the user's PC.

    Only exact Match 1 items go (same name and description), plus its π groups;
    anything the user added themselves stays.
    """
    made = {(p.name, p.description) for p in MATCH_1["params"]
            if p.name not in ("R", "T_K")}
    return [p for p in params if (p.name, p.description) not in made
            and not p.description.startswith("π group")]


if "params" not in st.session_state:
    loaded = load_params(PARAMS_FILE)
    kept = _drop_match1(loaded)
    if len(kept) != len(loaded):
        save_params(PARAMS_FILE, kept)
    st.session_state["params"] = kept
params: list[CustomParam] = st.session_state["params"]
ds, param_errors = apply_params(base, params)
df_all = ds.df
cols = ds.columns
sb_file.caption(f"{source_name} · sheet '{ds.sheet}' · {len(df_all)} rows")

numeric = ds.numeric_vars()
categorical = [v for v in ds.categorical_vars() if cols[v].kind == "categorical"]
flags = [v for v, c in cols.items() if c.kind == "flag"]
for f in flags:
    df_all[f + "__label"] = df_all[f].map({True: "Yes", False: "No"})


def label(var: str) -> str:
    if var == "excel_row":
        return "Excel row"
    if var in cols:
        return cols[var].label
    if var in ds.constants:
        unit = ds.constants[var][1]
        return f"{var} [{unit}]" if unit else var
    return var


unit_overrides = load_unit_overrides(UNITS_FILE)


def unit_text(var: str) -> str:
    """The unit of a column or constant, after any correction made in the app."""
    if var in unit_overrides:
        return unit_overrides[var]
    if var in ds.constants:
        return ds.constants[var][1]
    return cols[var].unit if var in cols else ""


def unit_or_none(var: str):
    try:
        return parse_unit(unit_text(var))
    except UnitError:
        return None


def set_unit(changes: dict) -> None:
    for var, text in changes.items():
        original = ds.constants[var][1] if var in ds.constants else cols[var].unit
        if text == original:
            unit_overrides.pop(var, None)
        else:
            unit_overrides[var] = text
    save_unit_overrides(UNITS_FILE, unit_overrides)


def save() -> None:
    save_params(PARAMS_FILE, params)


def add_param(p: CustomParam) -> None:
    if not valid_name(p.name):
        st.error("Name must be letters, digits and _ only, not starting with a digit.")
    elif p.name in set(cols) | {q.name for q in params}:
        st.error(f"'{p.name}' is already used.")
    else:
        params.append(p)
        save()
        st.rerun()


# --------------------------------------------------------------------------- sidebar

st.sidebar.title("SCC Plotter")
st.sidebar.caption("Stainless steel crack growth in PWR water")
st.sidebar.button("❓ Tutorial", on_click=tutorial.start, args=(params, save),
                  help="A 3-minute guided tour that shows you each part of the app.")

st.sidebar.header("Which data?")
expert = st.session_state.get("expert", False)
filters = Filters()
for f in flags:
    simple_flag = "Mainstream" in f
    if not (simple_flag or expert):
        continue
    if st.sidebar.checkbox(f"Only {cols[f].name} ({int(df_all[f].sum())} rows)",
                           key=f"flag_{f}",
                           help=hint("Mainstream") if simple_flag else hint("HAZ")):
        filters.flags.append(f)
for var in [v for v in ("Lab", "Material", "Condition") if v in categorical]:
    if var == "Condition" and not expert:
        continue
    options = sorted(df_all[var].astype("string").fillna(EMPTY).unique())
    chosen = st.sidebar.multiselect(var, options, key=f"cat_{var}", placeholder="All",
                                    help=hint(var))
    if chosen:
        filters.categories[var] = chosen
if expert:
    range_vars = st.sidebar.multiselect(
        "Limit a range", numeric, key="range_vars", format_func=label,
        help="Adds a slider for any number column. Rows with that cell empty are left out.")
    for var in range_vars:
        col = df_all[var].dropna()
        if col.empty:
            continue
        lo, hi = float(col.min()), float(col.max())
        if lo == hi:
            st.sidebar.caption(f"{label(var)}: only value {lo:g}")
            continue
        key = f"range_{var}"
        if is_discrete(col):
            values = sorted(col.unique())
            if st.session_state.get(key) is None or st.session_state[key][0] not in values:
                st.session_state[key] = (values[0], values[-1])
            a, b = st.sidebar.select_slider(label(var), options=values, key=key)
        else:
            if st.session_state.get(key) is None:
                st.session_state[key] = (lo, hi)
            a, b = st.sidebar.slider(label(var), lo, hi, key=key)
        filters.ranges[var] = (a, b)


def reset_filters() -> None:
    for k in list(st.session_state):
        if k.startswith(("flag_", "cat_", "range_")):
            del st.session_state[k]


st.sidebar.button("Reset filters", on_click=reset_filters)
st.sidebar.divider()
st.sidebar.toggle("Expert mode", key="expert",
                  help="Shows advanced options: more filters, range sliders, plot options, "
                       "choosing the measuring sticks yourself, and the type of fitted curve.")
# Looks like plain text. It is not.
st.sidebar.button(f"version {VERSION}", key="knock", on_click=theme.knock,
                  help="Some say old doors open to those who knock three times.")
st.markdown(theme.page_css(), unsafe_allow_html=True)
if msg := st.session_state.pop("old_map_toast", None):
    st.toast(msg)

df = apply_filters(df_all, filters)

# --------------------------------------------------------------------------- header + tutorial

if "tut_on" not in st.session_state:
    if tutorial.first_launch():
        tutorial.start(params, save)
    else:
        st.session_state["tut_on"] = False
st.session_state.setdefault("area", LOOK)

st.markdown("## SCC Plotter")
labs_shown = df["Lab"].nunique() if "Lab" in df else 0
st.caption(f"Showing **{len(df)}** of {len(df_all)} measurements · {labs_shown} labs · "
           "change this in the sidebar under *Which data?*")
if param_errors:
    st.error("Some added quantities could not be computed:\n\n- " + "\n- ".join(param_errors))

tutorial.render(params, save)

area = st.radio("Area", AREAS, horizontal=True, key="area", label_visibility="collapsed")

ctx = Ctx(ds=ds, df=df, df_all=df_all, params=params, numeric=numeric,
          categorical=categorical, flags=flags, expert=bool(st.session_state.get("expert")),
          label=label, unit_text=unit_text, set_unit=set_unit, save_params=save,
          add_param=add_param)

if area == LOOK:
    look_page.render(ctx)
elif area == DATA:
    data_page.render(ctx, unit_or_none)
else:
    learn_page.render()
