"""🗂 Data → Auto-fill properties: add material and water-chemistry columns."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from scc_core import enrichment as en
from scc_core.custom_params import CustomParam
from ui.common import APP_DIR, Ctx, next_step

TABLE_FILE = APP_DIR / "data" / "material_properties.csv"
GROUPS = ("Mechanical", "Water chemistry", "Composition")


def table_text() -> str:
    """The user's property table (CSV text), or '' if there is none."""
    try:
        return TABLE_FILE.read_text(encoding="utf-8") if TABLE_FILE.exists() else ""
    except OSError:
        return ""


@st.cache_data(show_spinner=False)
def tables_from(text: str) -> en.PropertyTables:
    base = en.PropertyTables.builtin()
    return en.PropertyTables.from_csv(text).merged_over(base) if text else base


@st.cache_data(show_spinner="Downloading table …", ttl=3600)
def _download(url: str) -> str:
    return en.fetch_csv(url)


@st.cache_data(show_spinner="Calculating …")
def _preview(df: pd.DataFrame, keys: tuple[str, ...], text: str) -> pd.DataFrame:
    tables = tables_from(text)
    rows = []
    for k in keys:
        p = en.BY_KEY[k]
        try:
            s = en.compute(k, df, tables)
        except KeyError as exc:
            rows.append({"column": k, "unit": p.unit, "rows filled": 0, "min": None,
                         "median": None, "max": None, "note": str(exc)})
            continue
        rows.append({"column": k, "unit": p.unit, "rows filled": f"{s.notna().sum()} of {len(s)}",
                     "min": s.min(), "median": s.median(), "max": s.max(), "note": ""})
    return pd.DataFrame(rows)


def builtin_csv() -> str:
    t = en.PropertyTables.builtin()
    rows = [{"grade": g, "property": p, "temp_C": round(float(tc), 1), "value": round(float(v), 2)}
            for (g, p), (ts, vs) in sorted(t.tables.items()) for tc, v in zip(ts, vs)]
    return pd.DataFrame(rows).to_csv(index=False)


def render(ctx: Ctx) -> None:
    params = ctx.params
    have = {p.name for p in params} | set(ctx.cols)
    next_step("tick the properties you want, check the preview, then press **Add**. They "
              "appear in every plot menu, like the workbook's own columns.")
    st.markdown(
        "These columns are **calculated for every test** from its material grade, "
        "temperature and water chemistry, so they can be used later to make quantities "
        "unit-free. Nothing here needs internet.")

    df = ctx.df_all
    outside = int(((df["Temp"] < en.T_WINDOW_C[0]) | (df["Temp"] > en.T_WINDOW_C[1])).sum())
    report = en.grade_report(df)
    unmapped = int(report.loc[report["grade"].str.startswith("—"), "rows"].sum())
    st.caption(f"Grades recognised for {len(df) - unmapped} of {len(df)} rows · "
               f"{outside} rows are outside the 200–350 °C window (still calculated; "
               f"tables cover 38–371 °C).")

    chosen: list[str] = []
    cols = st.columns(len(GROUPS))
    for col, group in zip(cols, GROUPS):
        with col:
            st.markdown(f"**{group}**")
            for p in [p for p in en.PROPERTIES if p.group == group]:
                added = p.key in have
                label = f"{p.label} [{p.unit}]" if p.unit else p.label
                if st.checkbox(label + (" ✓ added" if added else ""), key=f"enr_{p.key}",
                               disabled=added, help=p.description):
                    chosen.append(p.key)

    if chosen:
        st.markdown("##### Preview")
        st.dataframe(_preview(df, tuple(chosen), table_text()), hide_index=True)
        if st.button(f"Add {len(chosen)} column{'s' if len(chosen) > 1 else ''}",
                     type="primary"):
            for k in chosen:
                p = en.BY_KEY[k]
                params.append(CustomParam(name=k, kind="enriched", unit=p.unit,
                                          description=p.description, property=k))
            for k in chosen:
                st.session_state.pop(f"enr_{k}", None)
            ctx.save_params()
            st.rerun()

    with st.expander("How material names were matched to grades"):
        st.dataframe(report, hide_index=True)
        st.caption("Names are matched by their grade number: '316SS 1', 'SUSF316HAZ' and "
                   "'316*HAZ' count as 316. Nitrogen-alloyed LN variants, 321 and 348 are not "
                   "matched, so their material properties stay empty.")

    with st.expander("Where the numbers come from (read before using them)"):
        st.markdown("""
- **Strength and stiffness:** approximate values modelled on **ASME BPVC Section II
  Part D** (Tables Y-1, U, TM-1): minimum specified values for **annealed** plate.
  The code book is licensed and could not be checked here, so verify them against
  your copy, or load your own table below. Most test specimens are **cold worked**,
  which is why *YS from cold work* (MRP-458 fit) is offered as well.
- **pH:** boric acid + lithium hydroxide model (Mesmer et al. 1972 borate constant,
  Marshall & Franck 1981 water constant, ideal solution). Compared with values quoted
  in MRP-458 it reads **about 0.1–0.2 pH high**, because it ignores polyborates.
  430 rows have no B/Li values, so their pH stays empty.
- **ECP:** hydrogen-electrode estimate, only meaningful in deaerated hydrogenated water.
- **Ni/NiO hydrogen:** Attanasio & Morton correlation, log10[H₂] = 0.0111·T − 2.59.
- **Composition:** ASTM A240 specification ranges, not the measured heat composition.
  Sulfur, which MRP-352 calls the biggest gap, is only a maximum here.
""")

    with st.expander("Use your own property table (file or web address)"):
        text = table_text()
        st.write("A table with the columns **grade, property, temp_C, value** "
                 "(property = E in GPa, YS or UTS in MPa; grade may be * for all) replaces "
                 "the built-in values wherever it has data.")
        st.write("Current source: **" + tables_from(text).source + "**")
        st.download_button("Download the built-in table as a template", builtin_csv(),
                           file_name="material_properties_template.csv", mime="text/csv")
        up = st.file_uploader("Load a table (.csv)", type=["csv"], key="enr_upload")
        if up is not None and st.button("Use this table"):
            _save_table(up.getvalue().decode("utf-8", errors="replace"))
        if ctx.expert:
            url = st.text_input("…or download it from a web address (a CSV file you exported, "
                                "e.g. from JRC MatDB or NIMS MatNavi)", key="enr_url")
            if url and st.button("Download and use"):
                try:
                    _save_table(_download(url))
                except Exception as exc:  # network errors, bad addresses
                    st.error(f"Could not download: {exc}")
        if text and st.button("Remove my table (back to built-in values)"):
            TABLE_FILE.unlink(missing_ok=True)
            st.rerun()


def _save_table(text: str) -> None:
    try:
        en.PropertyTables.from_csv(text)  # validate first
    except Exception as exc:
        st.error(f"This table cannot be used: {exc}")
        return
    TABLE_FILE.parent.mkdir(exist_ok=True)
    TABLE_FILE.write_text(text, encoding="utf-8")
    st.rerun()
