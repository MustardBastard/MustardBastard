"""👀 Look: plot anything against anything, or Y against every parameter."""

from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from scc_core.plotdata import (
    EMPTY, OTHER, SEQUENTIAL, SYMBOLS, category_colors, prepare_xy,
)
from scc_core.suggestions import SUGGESTIONS
from ui.common import NONE, Ctx, hint, meaning, next_step, show_fig, style_fig

ONE, EVERY = "One plot", "Y against every parameter"
HOVER_COLS = ("Lab", "Material", "CT_ID", "Condition", "excel_row")


def apply_suggestion(s: dict) -> None:
    st.session_state.update(x=s["x"], y=s["y"], color=s["color"], log_x=s["log_x"],
                            log_y=s["log_y"], look_view=ONE,
                            suggestion_note=f"**{s['title']}**: {s['why']}")


def _defaults(ctx: Ctx) -> None:
    for k, v in {"x": "K", "y": "CGR", "color": "Lab", "log_x": True, "log_y": True,
                 "look_view": ONE}.items():
        st.session_state.setdefault(k, v)
    for k in ("x", "y"):
        if st.session_state[k] not in ctx.numeric:
            st.session_state[k] = ctx.numeric[0]
    if st.session_state["color"] not in color_options(ctx):
        st.session_state["color"] = NONE


def color_options(ctx: Ctx) -> list[str]:
    return [NONE] + ctx.categorical + ctx.flags + ctx.numeric


def render(ctx: Ctx) -> None:
    _defaults(ctx)
    mainstream_on = any(st.session_state.get(f"flag_{f}") for f in ctx.flags if "Mainstream" in f)
    if not mainstream_on:
        next_step("pick what to plot below, or open **Suggested views** for a ready-made "
                  "starting point. Tick *Only PWR Mainstream Data* in the sidebar to see "
                  "the rows the official report used.")
    elif st.session_state["color"] != "Lab":
        next_step("set **Colour** to *Lab* to see how much of the scatter comes from who "
                  "measured it.")
    else:
        next_step("try **Y against every parameter** for a quick screening, or go to "
                  "**🔥 Test an idea** to check an idea with numbers.")

    view = st.radio("View", [ONE, EVERY], horizontal=True, key="look_view",
                    label_visibility="collapsed")

    with st.expander("💡 Suggested views", expanded=False):
        for i, s in enumerate([s for s in SUGGESTIONS
                               if s["x"] in ctx.numeric and s["y"] in ctx.numeric]):
            a, b = st.columns([1, 3])
            a.button(s["title"], key=f"sugg_{i}", on_click=apply_suggestion, args=(s,))
            b.caption(s["why"])
    if note := st.session_state.get("suggestion_note"):
        st.caption("💡 " + note)

    if view == ONE:
        _one_plot(ctx)
    else:
        _every_param(ctx)


def _one_plot(ctx: Ctx) -> None:
    label = ctx.label
    c1, c2, c3, c4 = st.columns([3, 3, 3, 2])
    y = c1.selectbox("Y axis (what you want to explain)", ctx.numeric, key="y",
                     format_func=label, help=hint("CGR"))
    x = c2.selectbox("X axis (what might drive it)", ctx.numeric, key="x", format_func=label)
    color = c3.selectbox("Colour", color_options(ctx), key="color", format_func=label,
                         help="Colour the points by a category (e.g. Lab) or a number.")
    with c4:
        log_x = st.checkbox("Log X", key="log_x", help=hint("log_axis"))
        log_y = st.checkbox("Log Y", key="log_y", help=hint("log_axis"))

    max_colors, use_symbols = 8, True
    if ctx.expert:
        with st.expander("More plot options"):
            st.session_state.setdefault("max_colors", 8)
            st.session_state.setdefault("use_symbols", True)
            max_colors = st.slider("Max colours (rest → 'Other')", 3, 8, key="max_colors")
            use_symbols = st.checkbox("Also vary marker shape", key="use_symbols")

    res = prepare_xy(ctx.df, x, y, log_x, log_y)
    st.caption(res.summary())
    if res.data.empty:
        st.warning("Nothing to plot with these choices.")
        return
    frame = res.data.copy()
    hover = [h for h in HOVER_COLS if h in frame.columns]
    labels = {x: label(x), y: label(y), **{h: label(h) for h in hover}}
    kwargs = {}
    if color == NONE:
        kwargs = dict(color_discrete_sequence=[SEQUENTIAL[4]])
    elif color in ctx.numeric:
        kwargs = dict(color=color, color_continuous_scale=SEQUENTIAL)
        labels[color] = label(color)
    else:
        src = color + "__label" if color in ctx.flags else color
        display, cmap, order = category_colors(ctx.df_all[src], max_colors)
        frame["__cat"] = display.loc[frame.index]
        kwargs = dict(color="__cat", color_discrete_map=cmap, category_orders={"__cat": order})
        labels["__cat"] = label(color)
        if use_symbols:
            smap = {c: SYMBOLS[i % len(SYMBOLS)] for i, c in enumerate(order)}
            smap.update({OTHER: "circle-open", EMPTY: "circle-open"})
            kwargs.update(symbol="__cat", symbol_map=smap)
    fig = px.scatter(frame, x=x, y=y, log_x=log_x, log_y=log_y, hover_data=hover,
                     labels=labels, **kwargs)
    fig.update_traces(marker=dict(size=9, opacity=0.85, line=dict(width=1, color="#ffffff")))
    show_fig(style_fig(fig))

    st.markdown(f"**What am I looking at?** Each point is one test.  \n"
                f"**Y = {label(y)}**: {meaning(y, ctx)}  \n"
                f"**X = {label(x)}**: {meaning(x, ctx)}")
    st.caption("Drag to zoom · double-click to reset · click a legend entry to hide it · "
               "camera icon saves a PNG.")


def _every_param(ctx: Ctx) -> None:
    label = ctx.label
    c1, c2 = st.columns([3, 1])
    yy = c1.selectbox("Y axis (what you want to explain)", ctx.numeric, key="y",
                      format_func=label)
    log_yy = c2.checkbox("Log Y", key="log_y", help=hint("log_axis"))
    xs = [v for v in ctx.numeric if v not in ("Index", "excel_row", yy)]
    ncols = 3
    nrows = math.ceil(len(xs) / ncols)
    results = {v: prepare_xy(ctx.df, v, yy, False, log_yy) for v in xs}
    titles = [f"{label(v)}  (n={len(results[v].data)})" for v in xs]
    fig = make_subplots(rows=nrows, cols=ncols, subplot_titles=titles,
                        vertical_spacing=0.35 / max(nrows, 1), horizontal_spacing=0.06)
    hover = [h for h in HOVER_COLS if h in ctx.df.columns]
    for i, v in enumerate(xs):
        r = results[v]
        row, col = i // ncols + 1, i % ncols + 1
        fig.add_trace(go.Scatter(
            x=r.data[v], y=r.data[yy], mode="markers", showlegend=False,
            marker=dict(size=6, color=SEQUENTIAL[4], opacity=0.6),
            customdata=r.data[hover].astype(str).values if hover else None,
            hovertemplate=f"{label(v)}: %{{x}}<br>{label(yy)}: %{{y}}"
                          + "".join(f"<br>{h}: %{{customdata[{j}]}}" for j, h in enumerate(hover))
                          + "<extra></extra>",
        ), row=row, col=col)
        if log_yy:
            fig.update_yaxes(type="log", row=row, col=col)
    fig.update_annotations(font_size=12)
    show_fig(style_fig(fig, height=270 * nrows))
    st.caption(f"{label(yy)} against every numeric parameter, with the sidebar filters. "
               "A cloud with a clear slope suggests that parameter matters; a flat or "
               "shapeless cloud suggests it does not (or that it hardly varies in the data).")


def frame_for_table(df: pd.DataFrame) -> pd.DataFrame:
    return df[[c for c in df.columns if not c.endswith("__label")]]
