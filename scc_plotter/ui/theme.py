"""Plot styles: the normal style, and a hidden "old map" style.

The old map is an easter egg. It is unlocked (and locked again) by clicking the
small version text at the bottom of the sidebar three times in quick succession.
Its state is kept in a hidden file, so it survives restarts.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass

import plotly.graph_objects as go
import streamlit as st

from scc_core.plotdata import CATEGORICAL, EMPTY_COLOR, OTHER_COLOR, SEQUENTIAL, SYMBOLS
from ui.common import APP_DIR

STATE_FILE = APP_DIR / ".old_map"
KNOCKS, KNOCK_WINDOW = 3, 4.0  # clicks needed, seconds allowed for all of them


@dataclass(frozen=True)
class Palette:
    categorical: list[str]
    other: str
    empty: str
    sequential: list[str]
    symbols: list[str]
    symbols_3d: list[str]
    single: str          # colour when nothing is coloured by


NORMAL = Palette(
    categorical=CATEGORICAL, other=OTHER_COLOR, empty=EMPTY_COLOR, sequential=SEQUENTIAL,
    symbols=SYMBOLS,
    symbols_3d=["circle", "square", "diamond", "cross", "x",
                "circle-open", "square-open", "diamond-open"],
    single=SEQUENTIAL[4],
)

# Inks of an old chart: sepia, vermilion, woad blue, verdigris, ochre, murrey,
# umber, slate. Order chosen so neighbours differ in both hue and darkness.
OLD_MAP = Palette(
    categorical=["#3b2a1a", "#a3341f", "#2f4f7a", "#4f7a4a", "#b8862b", "#6b3a5e",
                 "#8a5a32", "#5a6b6b"],
    other="#a8977a", empty="#c9b998",
    sequential=["#efe0bd", "#dcc490", "#c4a064", "#a27a46", "#7d562f", "#58391d", "#3a2513"],
    # Map-like signs: city star, mountain, chapel cross, well, hill, ...
    symbols=["star", "triangle-up", "cross", "circle-dot", "diamond", "hexagram",
             "square-x", "star-triangle-up"],
    symbols_3d=["diamond", "cross", "x", "circle", "square", "diamond-open",
                "circle-open", "square-open"],
    single="#3b2a1a",
)

INK = "#3b2a1a"
PARCHMENT = "#f1e2bf"
PAPER_EDGE = "#e2cc9a"
FONT = "'IM Fell English', 'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif"
FONT_SC = "'IM Fell English SC', " + FONT


# --------------------------------------------------------------------------- state

def old_map_on() -> bool:
    if "old_map" not in st.session_state:
        st.session_state["old_map"] = STATE_FILE.exists()
    return bool(st.session_state["old_map"])


def palette() -> Palette:
    return OLD_MAP if old_map_on() else NORMAL


def knock() -> None:
    """Callback of the hidden version button: three quick knocks toggle the map."""
    now = time.time()
    knocks = [t for t in st.session_state.get("knocks", []) if now - t < KNOCK_WINDOW]
    knocks.append(now)
    if len(knocks) < KNOCKS:
        st.session_state["knocks"] = knocks
        return
    st.session_state["knocks"] = []
    on = not old_map_on()
    st.session_state["old_map"] = on
    try:
        if on:
            STATE_FILE.write_text("Hic sunt dracones", encoding="utf-8")
        else:
            STATE_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    st.session_state["old_map_toast"] = (
        "🗺️ The old map unrolls… *Hic sunt dracones.*" if on
        else "📜 The old map is rolled up and put away.")


def page_css() -> str:
    """Extra CSS: hide the version button's looks, load the old fonts when on."""
    css = """
    <style>
      .st-key-knock button {background: none; border: none; padding: 0; min-height: 0;
                            color: #8f8d87; font-size: 0.8rem; box-shadow: none;}
      .st-key-knock button:hover {color: #8f8d87; background: none;}
      .st-key-knock button:focus:not(:active) {color: #8f8d87; box-shadow: none;}
    </style>"""
    if old_map_on():
        css += """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=IM+Fell+English+SC&display=swap');
    </style>"""
    return css


# --------------------------------------------------------------------------- drawing

def _svg_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


# Aged parchment: darker, browner towards the edges.
_VIGNETTE = _svg_uri("""<svg xmlns='http://www.w3.org/2000/svg' width='400' height='400'
 preserveAspectRatio='none' viewBox='0 0 400 400'>
 <defs><radialGradient id='g' cx='50%' cy='50%' r='75%'>
  <stop offset='55%' stop-color='#f6e9cb' stop-opacity='0'/>
  <stop offset='85%' stop-color='#b98f55' stop-opacity='0.28'/>
  <stop offset='100%' stop-color='#7a5530' stop-opacity='0.55'/>
 </radialGradient></defs>
 <rect width='400' height='400' fill='url(#g)'/></svg>""")

# A sixteen-point compass rose, inked in sepia with a red north.
_COMPASS = _svg_uri("""<svg xmlns='http://www.w3.org/2000/svg' viewBox='-100 -100 200 200'>
 <g fill='none' stroke='#3b2a1a' stroke-width='1.5'>
  <circle r='92'/><circle r='86'/><circle r='30'/>
 </g>
 <g fill='#3b2a1a' opacity='0.55'>
  <polygon points='0,-60 6,-6 0,0 -6,-6' transform='rotate(45)'/>
  <polygon points='0,-60 6,-6 0,0 -6,-6' transform='rotate(135)'/>
  <polygon points='0,-60 6,-6 0,0 -6,-6' transform='rotate(225)'/>
  <polygon points='0,-60 6,-6 0,0 -6,-6' transform='rotate(315)'/>
 </g>
 <g stroke='#3b2a1a' stroke-width='1'>
  <polygon points='0,-88 11,-11 0,0' fill='#a3341f'/><polygon points='0,-88 -11,-11 0,0' fill='#f1e2bf'/>
  <polygon points='88,0 11,11 0,0' fill='#3b2a1a'/><polygon points='88,0 11,-11 0,0' fill='#f1e2bf'/>
  <polygon points='0,88 -11,11 0,0' fill='#3b2a1a'/><polygon points='0,88 11,11 0,0' fill='#f1e2bf'/>
  <polygon points='-88,0 -11,-11 0,0' fill='#3b2a1a'/><polygon points='-88,0 -11,11 0,0' fill='#f1e2bf'/>
 </g>
 <text x='0' y='-94' text-anchor='middle' font-family='serif' font-size='16' fill='#a3341f'>N</text>
</svg>""")


def apply_old_map(fig: go.Figure) -> go.Figure:
    """Restyle a finished figure as an old chart."""
    is_3d = any(getattr(t, "type", "") == "scatter3d" for t in fig.data)
    axis = dict(
        showline=True, linecolor=INK, linewidth=2, mirror=True, ticks="outside",
        tickcolor=INK, ticklen=6, tickwidth=1.2, gridcolor="rgba(59,42,26,0.18)",
        griddash="dot", zeroline=False, tickfont=dict(family=FONT, color=INK, size=13),
        title_font=dict(family=FONT_SC, color=INK, size=15),
    )
    fig.update_layout(
        font=dict(family=FONT, color=INK, size=13),
        paper_bgcolor=PAPER_EDGE, plot_bgcolor=PARCHMENT,
        title_font=dict(family=FONT_SC, color=INK, size=18),
        legend=dict(bgcolor="rgba(241,226,191,0.92)", bordercolor=INK, borderwidth=1.5,
                    font=dict(family=FONT, color=INK),
                    title=dict(font=dict(family=FONT_SC, color=INK))),
        hoverlabel=dict(bgcolor=PARCHMENT, bordercolor=INK,
                        font=dict(family=FONT, color=INK)),
        coloraxis=dict(colorbar=dict(outlinecolor=INK, outlinewidth=1.5,
                                     tickfont=dict(family=FONT, color=INK),
                                     title=dict(font=dict(family=FONT_SC, color=INK)))),
    )
    fig.update_annotations(font=dict(family=FONT_SC, color=INK))
    fig.update_traces(marker_line_color=INK, marker_line_width=0.9,
                      selector=dict(mode="markers"))
    if is_3d:
        scene_axis = dict(backgroundcolor=PARCHMENT, gridcolor="rgba(59,42,26,0.25)",
                          linecolor=INK, showbackground=True, zerolinecolor=INK,
                          tickfont=dict(family=FONT, color=INK),
                          title=dict(font=dict(family=FONT_SC, color=INK)))
        fig.update_scenes(xaxis=scene_axis, yaxis=scene_axis, zaxis=scene_axis)
        fig.update_traces(marker_line_width=0, selector=dict(type="scatter3d"))
        return fig

    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    # Aged edges and the compass rose sit below the data.
    fig.add_layout_image(source=_VIGNETTE, xref="paper", yref="paper", x=0, y=1,
                         sizex=1, sizey=1, sizing="stretch", layer="below", opacity=1)
    fig.add_layout_image(source=_COMPASS, xref="paper", yref="paper", x=0.985, y=0.02,
                         sizex=0.16, sizey=0.16, xanchor="right", yanchor="bottom",
                         sizing="contain", layer="below", opacity=0.45)
    # A double border, like the frame of an old chart.
    fig.add_shape(type="rect", xref="paper", yref="paper", x0=-0.012, y0=-0.02,
                  x1=1.012, y1=1.02, line=dict(color=INK, width=1), layer="below")
    fig.add_annotation(text="<i>Hic sunt dracones</i>", xref="paper", yref="paper",
                       x=0.02, y=0.97, xanchor="left", yanchor="top", showarrow=False,
                       font=dict(family=FONT, color="rgba(59,42,26,0.45)", size=14))
    return fig
