"""🔥 Test an idea: a match, in four guided steps.

1 Idea → 2 Quantities (units) → 3 Unit-free combinations (π groups) → 4 Verdict
"""

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
from scc_core.matches import MATCH_1
from scc_core.plotdata import SEQUENTIAL, category_colors
from scc_core.units import DIMLESS, UnitError, format_dims, parse_unit, same_dims
from ui.common import NONE, Ctx, hint, meaning, next_step, show_fig, style_fig

STEPS = ["Idea", "Quantities", "Combinations", "Verdict"]
GROUP_TAG = "π group"


# --------------------------------------------------------------------------- callbacks

def go_step(n: int) -> None:
    st.session_state["m_step"] = n


def setup_match(match: dict, params: list[CustomParam], save: Callable[[], None]) -> None:
    """Add the match's parameters (if missing) and pre-fill the selections."""
    have = {p.name for p in params}
    for p in match["params"]:
        if p.name not in have:
            params.append(CustomParam(**vars(p)))
    save()
    st.session_state.update(
        nd_target=match["variables"][0], nd_inputs=list(match["variables"][1:]),
        nd_rep=list(match["repeating"]), nd_prefix=match["prefix"],
        nd_match=match["name"], nd_x_main=match["x"], m_step=2,
    )
    for k in ("nd_group_Y", "nd_group_X", "nd_raw_Y", "nd_raw_X"):
        st.session_state.pop(k, None)


def start_own_idea() -> None:
    st.session_state.update(nd_target="CGR", nd_inputs=[], nd_rep=[], nd_prefix="my",
                            nd_match="My idea", nd_x_main=None, m_step=2)
    for k in ("nd_group_Y", "nd_group_X", "nd_raw_Y", "nd_raw_X"):
        st.session_state.pop(k, None)


def create_groups(params: list[CustomParam], save: Callable[[], None]) -> None:
    """Turn the combinations shown in step 3 into parameters, then go to the verdict."""
    pending = st.session_state.get("pending_groups") or []
    existing = {p.name: p for p in params}
    errors = []
    for g in pending:
        old = existing.get(g["name"])
        if old is not None:
            if old.formula != g["formula"]:
                errors.append(f"'{g['name']}' already exists with a different formula. "
                              "Delete it on the Data page, or change the name prefix.")
            continue
        params.append(CustomParam(name=g["name"], kind="formula", unit="",
                                  description=f"{GROUP_TAG}: {g['label']}",
                                  formula=g["formula"]))
    if errors:
        st.session_state["nd_error"] = "\n\n".join(errors)
        return
    save()
    st.session_state.pop("nd_error", None)
    for k in ("nd_group_Y", "nd_group_X", "nd_raw_Y", "nd_raw_X"):
        st.session_state.pop(k, None)
    st.session_state["m_step"] = 4


# --------------------------------------------------------------------------- page

def render(ctx: Ctx) -> None:
    step = st.session_state.setdefault("m_step", 1)
    name = st.session_state.get("nd_match", "New match")
    chips = " → ".join(f"**{i}. {s}**" if i == step else f"{i}. {s}"
                       for i, s in enumerate(STEPS, start=1))
    st.markdown(f"#### {name}")
    st.progress(step / len(STEPS), text=chips)

    if step == 1:
        _step_idea(ctx)
    elif step == 2:
        _step_quantities(ctx)
    elif step == 3:
        _step_groups(ctx)
    else:
        _step_verdict(ctx)


def _nav(back: bool = True, next_label: str | None = "Next →", next_ok: bool = True,
         on_next: Callable | None = None, args: tuple = ()) -> None:
    st.divider()
    a, _, b = st.columns([1, 3, 1])
    step = st.session_state["m_step"]
    if back and step > 1:
        a.button("← Back", on_click=go_step, args=(step - 1,), key=f"m_back_{step}")
    if next_label:
        b.button(next_label, type="primary", disabled=not next_ok, key=f"m_next_{step}",
                 on_click=on_next or go_step, args=args if on_next else (step + 1,))


# --------------------------------------------------------------------------- step 1

def _step_idea(ctx: Ctx) -> None:
    next_step("start **Match 1**, or build your own idea from scratch.")
    st.markdown("A **match** is one small idea, tested on its own. You choose a few "
                "quantities, the app combines them into unit-free numbers, and checks "
                "whether the data pulls together.", help=hint("match"))
    with st.container(border=True):
        st.markdown(f"**{MATCH_1['name']}**: {MATCH_1['idea']}")
        st.button(f"Use {MATCH_1['name']}", type="primary", on_click=setup_match,
                  args=(MATCH_1, ctx.params, ctx.save_params))
    with st.container(border=True):
        st.markdown("**Your own idea**: pick the quantities yourself.")
        st.button("Build my own idea", on_click=start_own_idea)
    st.caption("What earlier matches taught us is in 📖 Learn → Cave map.")


# --------------------------------------------------------------------------- step 2

def _candidates(ctx: Ctx) -> list[str]:
    return [v for v in ctx.numeric if v != "Index"] + list(ctx.ds.constants)


def _units(ctx: Ctx, names: list[str]) -> tuple[dict, list]:
    units, bad = {}, []
    for v in names:
        try:
            units[v] = parse_unit(ctx.unit_text(v))
        except UnitError:
            bad.append(v)
    return units, bad


def _is_constant(ctx: Ctx, v: str) -> bool:
    return v in ctx.ds.constants or ctx.df[v].nunique(dropna=True) <= 1


def _step_quantities(ctx: Ctx) -> None:
    cands = _candidates(ctx)
    st.session_state.setdefault("nd_target", "CGR")
    if st.session_state["nd_target"] not in cands:
        st.session_state["nd_target"] = cands[0]
    st.session_state["nd_inputs"] = [v for v in st.session_state.get("nd_inputs", [])
                                     if v in cands and v != st.session_state["nd_target"]]
    a, b = st.columns([1, 2])
    target = a.selectbox("What do you want to explain?", cands, key="nd_target",
                         format_func=ctx.label, help=hint("CGR"))
    inputs = b.multiselect("Which quantities might drive it?",
                           [v for v in cands if v != target], key="nd_inputs",
                           format_func=ctx.label,
                           help="Include the scales you want to measure against, "
                                "e.g. a strength, a length, a rate.")
    chosen = [target] + inputs
    units, bad = _units(ctx, chosen)

    if len(chosen) < 2:
        next_step("choose at least one quantity that might drive the one you explain.")
    elif bad:
        next_step("fix the units marked ⚠ in the table (type a unit like mm/s, MPa, °C, µm).")
    else:
        next_step("check the table: every quantity should have a unit and its "
                  "ingredients. Then press **Next**.")

    rows = []
    for v in chosen:
        if v in units:
            u = units[v]
            ingredients = format_dims(u.dims)
            status = ("constant (moves axes only)" if _is_constant(ctx, v) else "✓")
        else:
            ingredients, status = "?", "⚠ unit not understood"
        rows.append({"quantity": v, "meaning": meaning(v, ctx), "unit": ctx.unit_text(v),
                     "ingredients": ingredients, "status": status})
    edited = st.data_editor(
        pd.DataFrame(rows), hide_index=True, key="nd_unit_editor",
        disabled=["quantity", "meaning", "ingredients", "status"],
        column_config={
            "unit": st.column_config.TextColumn(
                "unit ✏️", help="Click to correct. Examples: mm/s, MPa√m, °C, J/(mol·K), "
                               "µm, m²/s. Empty = a plain number."),
            "ingredients": st.column_config.TextColumn("ingredients", help=hint("dimensions")),
            "meaning": st.column_config.TextColumn("meaning", width="large"),
        },
    )
    changes = {r.quantity: (r.unit or "").strip() for r in edited.itertuples()
               if (r.unit or "").strip() != ctx.unit_text(r.quantity)}
    if changes:
        ctx.set_unit(changes)
        st.rerun()
    st.caption("Ingredients: M mass · L length · T time · Θ temperature · N amount (mol).")
    _nav(next_ok=len(chosen) >= 2 and not bad)


# --------------------------------------------------------------------------- step 3

def _step_groups(ctx: Ctx) -> None:
    target = st.session_state.get("nd_target")
    chosen = [target] + list(st.session_state.get("nd_inputs", []))
    units, bad = _units(ctx, chosen)
    if bad or len(chosen) < 2:
        st.warning("Go back to step 2: some quantities are missing or have unknown units.")
        _nav(next_label=None)
        return

    D = np.array([units[v].dims for v in chosen]).T
    rank = int(np.linalg.matrix_rank(D))
    n_groups = len(chosen) - rank
    st.markdown(f"**{len(chosen)} quantities − {rank} ingredients = "
                f"{n_groups} unit-free combination{'s' if n_groups != 1 else ''}**",
                help=hint("buckingham"))
    if n_groups == 0:
        next_step("go back and add a quantity that brings a missing ingredient, such as a "
                  "strength (MPa), a length (µm) or a rate (m²/s).")
        _nav(next_label=None)
        return

    st.session_state["nd_rep"] = [v for v in st.session_state.get("nd_rep", []) if v in chosen]
    if not st.session_state["nd_rep"]:
        st.session_state["nd_rep"] = _auto_sticks(ctx, chosen, units)
    if ctx.expert:
        rep = st.multiselect(f"Measuring sticks (choose {rank}, empty = automatic)",
                             chosen, key="nd_rep", format_func=ctx.label,
                             help=hint("measuring_sticks"))
    else:
        rep = st.session_state["nd_rep"]
    try:
        res = buckingham(chosen, units, rep or None)
    except DimensionError as exc:
        st.error(str(exc))
        _nav(next_label=None)
        return
    st.markdown("**Measuring sticks:** " + ", ".join(res.repeating),
                help=hint("measuring_sticks"))

    prefix = st.session_state.get("nd_prefix") or "pi"
    if ctx.expert:
        prefix = st.text_input("Name prefix", key="nd_prefix", placeholder="pi") or "pi"

    pending, rows = [], []
    for g in res.groups:
        name = f"{prefix}_{g.main}"
        consts = [v for v in g.exponents if _is_constant(ctx, v)]
        pending.append({"name": name, "formula": g.formula(units), "label": g.label(),
                        "main": g.main})
        rows.append({"name": name, "combination": g.label(),
                     "note": ("contains constant " + ", ".join(consts) + ": moves axes only")
                     if consts else ""})
    st.session_state["pending_groups"] = pending
    mains = [g["main"] for g in pending]
    if st.session_state.get("nd_x_main") not in mains:
        # The first quantity the user listed that got its own combination and varies.
        inputs = st.session_state.get("nd_inputs", [])
        st.session_state["nd_x_main"] = next(
            (v for v in inputs + mains if v in mains and v != target
             and not _is_constant(ctx, v)), None)
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Each combination is a pure number: all ingredients cancel. "
               "They are computed in SI units, so mm, MPa and °C are converted first.")

    next_step("press **Create and check →** to turn these into quantities and run the "
              "pattern check.")
    if err := st.session_state.get("nd_error"):
        st.error(err)

    with st.expander("✍️ Check a combination of your own"):
        _own_group(ctx)

    _nav(next_label="Create and check →", on_next=create_groups,
         args=(ctx.params, ctx.save_params))


def _auto_sticks(ctx: Ctx, chosen: list[str], units: dict) -> list[str]:
    """Measuring sticks chosen automatically: constants first, then added scales,
    then workbook columns; the quantity to explain is never a stick."""
    def priority(v):
        if v in ctx.ds.constants:
            return 0
        return 1 if v in ctx.cols and ctx.cols[v].source == "custom" else 2
    order = sorted(chosen[1:], key=priority)
    D = np.array([units[v].dims for v in chosen]).T
    rank = np.linalg.matrix_rank(D)
    sticks: list[str] = []
    for v in order:
        trial = sticks + [v]
        if np.linalg.matrix_rank(np.array([units[t].dims for t in trial]).T) == len(trial):
            sticks = trial
        if len(sticks) == rank:
            break
    return sticks if len(sticks) == rank else []


def _own_group(ctx: Ctx) -> None:
    st.write("Type any formula. The app tells you whether it is unit-free, and you can "
             "add it to compare in step 4.")
    own = st.text_input("Formula", placeholder="e.g. CGR * exp(Q / (R * T_K))", key="nd_own")
    if not own:
        return
    all_units, _ = _units(ctx, _candidates(ctx))
    ok, info = is_dimensionless(own, all_units)
    if not ok:
        st.error(f"Not unit-free: {info}")
        return
    st.success("Unit-free ✓")
    a, b = st.columns([2, 1])
    own_name = a.text_input("Name", key="nd_own_name", placeholder="e.g. my_temp_corrected")
    if b.button("Add it", key="nd_own_add") and own_name:
        ctx.add_param(CustomParam(name=own_name, kind="formula", unit="",
                                  description=f"{GROUP_TAG}: {own}",
                                  formula=si_formula(own, all_units)))


# --------------------------------------------------------------------------- step 4

def _pick(text, key, opts, default, label):
    if st.session_state.get(key) not in opts:
        st.session_state[key] = default if default in opts else opts[0]
    return st.selectbox(text, opts, key=key, format_func=label)


def _step_verdict(ctx: Ctx) -> None:
    df = ctx.df
    groups = [p.name for p in ctx.params if p.description.startswith(GROUP_TAG)
              and p.name in df.columns]
    if not groups:
        st.warning("No combinations yet. Go back to step 3 and press **Create and check**.")
        _nav(next_label=None)
        return
    prefix = st.session_state.get("nd_prefix") or "pi"
    target = st.session_state.get("nd_target", "CGR")
    x_main = st.session_state.get("nd_x_main") or "K"
    numeric = [v for v in ctx.numeric if v != "Index"]

    with st.expander("⚙️ Change what is compared", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            py = _pick("Combination plot: Y", "nd_group_Y", groups, f"{prefix}_{target}", ctx.label)
        with c2:
            px_ = _pick("Combination plot: X", "nd_group_X", groups, f"{prefix}_{x_main}", ctx.label)
        with c3:
            by = _pick("Raw plot: Y", "nd_raw_Y", numeric, target, ctx.label)
        with c4:
            raw_x = next((v for v in [x_main] + list(st.session_state.get("nd_inputs", []))
                          if v in numeric), x_main)
            bx = _pick("Raw plot: X", "nd_raw_X", numeric, raw_x, ctx.label)
        degree, color = 1, "Lab"
        if ctx.expert:
            a, b = st.columns(2)
            degree = a.radio("Fitted curve", [1, 2], horizontal=True, key="nd_degree",
                             format_func={1: "straight line (power law)",
                                          2: "curved (quadratic)"}.get)
            color_opts = (["Lab"] if "Lab" in df.columns else []) + [NONE] + groups + numeric
            color = b.selectbox("Colour", color_opts, key="nd_color", format_func=ctx.label)

    mask = valid_mask(df[py], df[px_], df[by], df[bx])
    sub = df[mask]
    labs = sub["Lab"] if "Lab" in sub.columns else None
    raw = collapse(sub[bx], sub[by], labs, degree)
    grp = collapse(sub[px_], sub[py], labs, degree)
    if raw is None or grp is None:
        st.warning("Not enough rows to check. Loosen the sidebar filters.")
        _nav(next_label=None)
        return

    st.caption(f"Comparing **{py} vs {px_}** with the raw **{by} vs {bx}**, on the same "
               f"{raw.n} rows (sidebar filters apply).")
    change = (grp.scatter - raw.scatter) / raw.scatter
    held = (None if grp.heldout is None or raw.heldout is None
            else (grp.heldout - raw.heldout) / raw.heldout)
    if change <= -0.1 and (held is None or held <= -0.1):
        light, title, sentence = "🟢", "Pattern found", (
            f"The points sit {-change:.0%} closer to the curve, and it also works on labs "
            "the curve never saw. A torch.")
        todo = "write this torch in 📖 Learn → Cave map, then design the next match around it."
    elif change >= 0.1 or (held is not None and held >= 0.1):
        light, title, sentence = "🔴", "Worse", (
            "The combinations spread the points out more than the raw plot. This idea points "
            "the wrong way, and that is a useful lesson.")
        todo = ("note the lesson in the Cave map. To find which part hurts, check one piece "
                "of the idea at a time with ✍️ in step 3.")
    else:
        light, title, sentence = "🟡", "No real change", (
            "The combinations explain no more than the raw quantities. Part of the idea may "
            "help and another part hurt.")
        todo = ("split the idea: in step 3, use ✍️ to check one piece at a time "
                "(for example only the temperature part).")
    st.markdown(f"<div style='font-size:2.2rem;font-weight:700;margin:0.2rem 0'>"
                f"{light} {title}</div>", unsafe_allow_html=True)
    st.write(sentence)

    m1, m2 = st.columns(2)
    m1.metric("Points typically sit … from the curve", f"×{grp.factor:.2f}",
              f"raw: ×{raw.factor:.2f}", delta_color="off", help=hint("decade"))
    if grp.heldout is not None and raw.heldout is not None:
        works = "✓ yes" if grp.heldout < raw.heldout * 0.9 else (
            "✗ no" if grp.heldout > raw.heldout * 1.1 else "≈ same as raw")
        m2.metric(f"Works on labs it never saw? ({grp.n_labs} labs)", works,
                  f"×{10 ** grp.heldout:.2f} vs raw ×{10 ** raw.heldout:.2f}",
                  delta_color="off", help=hint("held_out"))
    next_step(todo)

    left, right = st.columns(2)
    with left:
        show_fig(_fit_figure(sub, bx, by, raw, color, ctx, "Raw"))
    with right:
        show_fig(_fit_figure(sub, px_, py, grp, color, ctx, "Combinations"))
    with st.expander("The numbers behind the verdict"):
        st.write(f"Scatter (standard deviation of log10 Y around the curve): "
                 f"raw {raw.scatter:.3f}, combinations {grp.scatter:.3f} decades "
                 f"({change:+.0%}).")
        if held is not None:
            st.write(f"Held-out labs: raw {raw.heldout:.3f}, combinations {grp.heldout:.3f} "
                     f"decades ({held:+.0%}).")
        st.write("Thresholds: ±10%. Constants inside a combination cannot change these "
                 "numbers.")
    _nav(next_label="Start a new idea", on_next=go_step, args=(1,))


def _fit_figure(sub, x, y, fit, color, ctx: Ctx, title):
    frame = sub.copy()
    kwargs, labels = {}, {x: ctx.label(x), y: ctx.label(y)}
    if color == "Lab":
        display, cmap, order = category_colors(ctx.df_all["Lab"], 8)
        frame["__cat"] = display.loc[frame.index]
        kwargs = dict(color="__cat", color_discrete_map=cmap, category_orders={"__cat": order})
        labels["__cat"] = "Lab"
    elif color != NONE:
        kwargs = dict(color=color, color_continuous_scale=SEQUENTIAL)
        labels[color] = ctx.label(color)
    else:
        kwargs = dict(color_discrete_sequence=[SEQUENTIAL[4]])
    hover = [h for h in ("Lab", "Material", "excel_row") if h in frame.columns]
    fig = px.scatter(frame, x=x, y=y, log_x=True, log_y=True, hover_data=hover,
                     title=f"{title}: points sit ×{fit.factor:.2f} from the curve",
                     labels=labels, **kwargs)
    fig.update_traces(marker=dict(size=8, opacity=0.8, line=dict(width=1, color="#ffffff")))
    lx = np.linspace(np.log10(frame[x].min()), np.log10(frame[x].max()), 50)
    fig.add_trace(go.Scatter(x=10 ** lx, y=10 ** np.polyval(fit.coefs, lx), mode="lines",
                             line=dict(color="#0b0b0b", width=2), name="curve"))
    return style_fig(fig, height=460)


# --------------------------------------------------------------------------- unit check

def formula_unit_problem(formula: str, declared: str, units_for: Callable[[str], object]) -> str:
    """Message if a formula's dimensions disagree with its declared unit, else ''."""
    try:
        dec = parse_unit(declared)
    except UnitError as exc:
        return f"Declared unit: {exc}"
    names = {n.id for n in ast.walk(ast.parse(formula, mode="eval")) if isinstance(n, ast.Name)}
    units = {n: u for n in names if (u := units_for(n)) is not None}
    try:
        got = formula_dims(formula, units) or DIMLESS
    except DimensionError as exc:
        return str(exc)
    if not same_dims(got, dec.dims):
        return (f"The formula gives {format_dims(got)}, but the unit '{declared}' is "
                f"{format_dims(dec.dims)}.")
    return ""
