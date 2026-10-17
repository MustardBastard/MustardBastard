"""👀 Look: plot anything against anything, Y against every parameter, or in 3D."""

from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from scc_core.plotdata import (
    EMPTY, OTHER, category_colors, prepare_points, prepare_xy,
)
from ui import theme
from scc_core.suggestions import SUGGESTIONS
from ui.common import NONE, Ctx, hint, meaning, next_step, show_fig, style_fig

ONE, EVERY, THREE_D = "One plot", "Y against every parameter", "3D plot"

HOVER_COLS = ("Lab", "Material", "CT_ID", "Condition", "excel_row")


def apply_suggestion(s: dict) -> None:
    st.session_state.update(x=s["x"], y=s["y"], color=s["color"], log_x=s["log_x"],
                            log_y=s["log_y"], look_view=ONE,
                            suggestion_note=f"**{s['title']}**: {s['why']}")


def _defaults(ctx: Ctx) -> None:
    for k, v in {"x": "K", "y": "CGR", "color": "Lab", "log_x": True, "log_y": True,
                 "look_view": ONE, "x3": "K", "y3": "CW", "z3": "CGR", "log_x3": True,
                 "log_y3": False, "log_z3": True}.items():
        st.session_state.setdefault(k, v)
    for k in ("x", "y", "x3", "y3", "z3"):
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
        next_step("try **Y against every parameter** for a quick screening, or the "
                  "**3D plot** to see two drivers at once.")

    view = st.radio("View", [ONE, EVERY, THREE_D], horizontal=True, key="look_view",
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
    elif view == EVERY:
        _every_param(ctx)
    else:
        _three_d(ctx)


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
    kwargs = _color_kwargs(ctx, frame, color, labels, max_colors, use_symbols,
                           theme.palette().symbols)
    fig = px.scatter(frame, x=x, y=y, log_x=log_x, log_y=log_y, hover_data=hover,
                     labels=labels, **kwargs)
    fig.update_traces(marker=dict(size=9, opacity=0.85, line=dict(width=1, color="#ffffff")))
    show_fig(style_fig(fig))

    st.markdown(f"**What am I looking at?** Each point is one test.  \n"
                f"**Y = {label(y)}**: {meaning(y, ctx)}  \n"
                f"**X = {label(x)}**: {meaning(x, ctx)}")
    st.caption("Drag to zoom · double-click to reset · click a legend entry to hide it · "
               "camera icon saves a PNG.")


def _color_kwargs(ctx: Ctx, frame: pd.DataFrame, color: str, labels: dict,
                  max_colors: int, use_symbols: bool, symbols: list[str]) -> dict:
    """Plotly-express keyword arguments for the chosen colour (adds to `labels`)."""
    pal = theme.palette()
    if color == NONE:
        return dict(color_discrete_sequence=[pal.single])
    if color in ctx.numeric:
        labels[color] = ctx.label(color)
        return dict(color=color, color_continuous_scale=pal.sequential)
    src = color + "__label" if color in ctx.flags else color
    display, cmap, order = category_colors(ctx.df_all[src], max_colors, pal.categorical,
                                           pal.other, pal.empty)
    frame["__cat"] = display.loc[frame.index]
    labels["__cat"] = ctx.label(color)
    kwargs = dict(color="__cat", color_discrete_map=cmap, category_orders={"__cat": order})
    if use_symbols:
        smap = {c: symbols[i % len(symbols)] for i, c in enumerate(order)}
        smap.update({OTHER: "circle-open", EMPTY: "circle-open"})
        kwargs.update(symbol="__cat", symbol_map=smap)
    return kwargs


def _three_d(ctx: Ctx) -> None:
    label = ctx.label
    c1, c2, c3, c4 = st.columns(4)
    z = c1.selectbox("Up (vertical): what you want to explain", ctx.numeric, key="z3",
                     format_func=label, help=hint("CGR"))
    x = c2.selectbox("Across: first driver", ctx.numeric, key="x3", format_func=label)
    y = c3.selectbox("Depth: second driver", ctx.numeric, key="y3", format_func=label)
    color = c4.selectbox("Colour", color_options(ctx), key="color", format_func=label,
                         help="A fourth piece of information, e.g. the Lab.")
    a, b, c = st.columns(3)
    log_z = a.checkbox("Log up", key="log_z3", help=hint("log_axis"))
    log_x = b.checkbox("Log across", key="log_x3", help=hint("log_axis"))
    log_y = c.checkbox("Log depth", key="log_y3", help=hint("log_axis"))
    if len({x, y, z}) < 3:
        st.warning("Choose three different quantities for the three axes.")
        return

    res = prepare_points(ctx.df, [x, y, z], [log_x, log_y, log_z])
    st.caption(res.summary())
    if res.data.empty:
        st.warning("Nothing to plot with these choices.")
        return
    frame = res.data.copy()
    hover = [h for h in HOVER_COLS if h in frame.columns]
    labels = {x: label(x), y: label(y), z: label(z), **{h: label(h) for h in hover}}
    kwargs = _color_kwargs(ctx, frame, color, labels, 8, True, theme.palette().symbols_3d)
    fig = px.scatter_3d(frame, x=x, y=y, z=z, log_x=log_x, log_y=log_y, log_z=log_z,
                        hover_data=hover, labels=labels, **kwargs)
    fig.update_traces(marker=dict(size=4, opacity=0.85, line=dict(width=0)))
    fig = style_fig(fig, height=680)
    fig.update_layout(scene=dict(aspectmode="cube"), margin=dict(l=0, r=0, t=10, b=0))
    show_fig(fig)

    st.markdown(f"**What am I looking at?** Each point is one test.  \n"
                f"**Up = {label(z)}**: {meaning(z, ctx)}  \n"
                f"**Across = {label(x)}**: {meaning(x, ctx)}  \n"
                f"**Depth = {label(y)}**: {meaning(y, ctx)}")
    st.caption("Drag to rotate · scroll to zoom · double-click to reset. 3D is good for "
               "spotting a direction; confirm what you see with a 2D plot, because points "
               "can hide behind each other.")


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
            marker=dict(size=6, color=theme.palette().single, opacity=0.6),
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
