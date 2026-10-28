"""🗂 Data: who measured what, the rows themselves, and quantities you add."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from scc_core.custom_params import FUNCTIONS, CustomParam, FormulaError, check_formula
from scc_core.dimensional import formula_unit_problem
from scc_core.plotdata import coverage
from ui import theme
from ui.common import Ctx, next_step, show_fig, style_fig

COVERAGE, MATTERS_VIEW, TABLE, ENRICH, ADD = ("Who measured what", "What matters for CGR",
                                              "The rows", "Auto-fill properties",
                                 "Add a quantity")


def render(ctx: Ctx, unit_or_none) -> None:
    view = st.radio("View", [COVERAGE, MATTERS_VIEW, TABLE, ENRICH, ADD], horizontal=True,
                    key="data_view",
                    label_visibility="collapsed")
    if view == COVERAGE:
        _coverage(ctx)
    elif view == MATTERS_VIEW:
        from ui import matters
        matters.render(ctx)
    elif view == TABLE:
        _table(ctx)
    elif view == ENRICH:
        from ui import enrich
        enrich.render(ctx)
    else:
        _add(ctx, unit_or_none)


def _coverage(ctx: Ctx) -> None:
    next_step("look for white cells: those labs did not report that quantity. A pattern "
              "that relies on such a column only reflects the labs that did.")
    groups = [v for v in ctx.categorical if v in ("Lab", "Material")] or ctx.categorical
    grp = st.selectbox("Group rows by", groups, key="cov_group")
    cov_cols = [v for v in ctx.numeric if ctx.cols[v].source == "excel" and v != "Index"]
    table = coverage(ctx.df, grp, cov_cols)
    z = table[cov_cols]
    fig = px.imshow(
        z.values, x=[ctx.label(c) for c in cov_cols],
        y=[f"{g} ({n})" for g, n in zip(z.index, table["rows"])],
        color_continuous_scale=theme.palette().sequential, zmin=0, zmax=100, text_auto=".0f", aspect="auto",
        labels=dict(color="% filled"),
    )
    fig.update_xaxes(side="top")
    show_fig(style_fig(fig, height=max(320, 28 * len(z) + 140)))
    st.caption("Percentage of rows with a value, per group and column (sidebar filters "
               "apply). The number in brackets is how many rows each group has.")


def _table(ctx: Ctx) -> None:
    next_step("sort by clicking a column header; download the rows if you want to work "
              "with them elsewhere.")
    show = [c for c in ctx.df.columns if not c.endswith("__label")]
    st.dataframe(ctx.df[show], hide_index=True)
    st.download_button("Download these rows (CSV)", ctx.df[show].to_csv(index=False).encode(),
                       file_name="filtered_rows.csv", mime="text/csv")
    with st.expander("Notes on how the workbook was read"):
        st.write(f"Header found on Excel row {ctx.ds.header_row} of sheet '{ctx.ds.sheet}'.")
        for w in ctx.ds.warnings:
            st.write("• " + w)


def _add(ctx: Ctx, unit_or_none) -> None:
    next_step("add a quantity that is not in the Excel file. It then appears in every menu.")
    params = ctx.params
    st.write("Your added quantities live in `custom_parameters.json`, not in the workbook. "
             "Formulas can use the names in the list at the bottom. Functions: "
             + ", ".join(f"`{f}`" for f in sorted(FUNCTIONS)) + ".")

    st.markdown("##### Already added")
    for i, p in enumerate(params):
        a, b = st.columns([6, 1])
        if p.kind == "constant":
            desc = f"= {p.value:g}"
        elif p.kind == "formula":
            desc = f"= `{p.formula}`" if len(p.formula) < 80 else "(formula)"
        elif p.kind == "enriched":
            desc = "auto-filled property"
        else:
            desc = f"one value per {p.key_column} ({len(p.mapping)} set, default {p.default})"
        a.markdown(f"**{p.name}** [{p.unit or '–'}] · {desc}  \n"
                   f"<span style='color:#6b6a65'>{p.description}</span>",
                   unsafe_allow_html=True)
        if b.button("Delete", key=f"del_{i}"):
            params.pop(i)
            ctx.save_params()
            st.rerun()

    st.markdown("##### Add a new one")
    names_in_use = set(ctx.cols) | {p.name for p in params}
    kind = st.radio("Kind", ["formula", "constant", "lookup"], horizontal=True, key="add_kind",
                    format_func={"formula": "Formula (new column)", "constant": "Constant",
                                 "lookup": "One value per category (e.g. per material)"}.get)
    if kind == "formula":
        with st.form("add_formula"):
            a, b = st.columns(2)
            name = a.text_input("Name", placeholder="e.g. K_over_E")
            unit = b.text_input("Unit", placeholder="e.g. √m")
            formula = st.text_input("Formula", placeholder="e.g. K / E_mod")
            desc = st.text_input("What is it? (shown as its explanation)")
            skip = st.checkbox("Skip the unit check", help="Empirical fits (like yield "
                               "strength from %CW) have hidden units that cannot be checked.")
            if st.form_submit_button("Add formula"):
                try:
                    check_formula(formula, names_in_use)
                    problem = "" if skip else formula_unit_problem(formula, unit, unit_or_none)
                    if problem:
                        st.error(problem + " Fix the unit, or tick 'Skip the unit check'.")
                    else:
                        ctx.add_param(CustomParam(name=name, kind="formula", unit=unit,
                                                  description=desc, formula=formula))
                except FormulaError as exc:
                    st.error(str(exc))
    elif kind == "constant":
        with st.form("add_constant"):
            a, b, c = st.columns(3)
            name = a.text_input("Name", placeholder="e.g. E_mod")
            value = b.number_input("Value", value=0.0, format="%g")
            unit = c.text_input("Unit", placeholder="e.g. GPa")
            desc = st.text_input("What is it? (and where the value comes from)")
            if st.form_submit_button("Add constant"):
                ctx.add_param(CustomParam(name=name, kind="constant", unit=unit,
                                          description=desc, value=value))
    else:
        cats_cols = ctx.categorical
        key_col = st.selectbox("One value per …", cats_cols,
                               index=cats_cols.index("Material") if "Material" in cats_cols else 0)
        cats = sorted(ctx.df_all[key_col].dropna().astype(str).unique())
        a, b, c = st.columns(3)
        name = a.text_input("Name", placeholder="e.g. E_mod", key="lk_name")
        unit = b.text_input("Unit", placeholder="e.g. GPa", key="lk_unit")
        default = c.number_input("Value for blank cells", value=None, format="%g",
                                 key="lk_default")
        desc = st.text_input("What is it? (and where the values come from)", key="lk_desc")
        table = st.data_editor(
            pd.DataFrame({key_col: cats, "value": [None] * len(cats)}).astype({"value": "float"}),
            disabled=[key_col], hide_index=True, key=f"lk_table_{key_col}",
        )
        if st.button("Add lookup"):
            mapping = {str(k): float(v) for k, v in zip(table[key_col], table["value"])
                       if pd.notna(v)}
            ctx.add_param(CustomParam(name=name, kind="lookup", unit=unit, description=desc,
                                      key_column=key_col, mapping=mapping, default=default))

    with st.expander("Names you can use in formulas"):
        st.dataframe(pd.DataFrame([
            {"name": c.var, "column": c.label, "kind": c.kind, "source": c.source}
            for c in ctx.cols.values()
        ] + [{"name": k, "column": f"{k} [{u}]", "kind": "constant", "source": "custom"}
             for k, (_, u) in ctx.ds.constants.items()]), hide_index=True)
