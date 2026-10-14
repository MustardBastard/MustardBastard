"""Things every page needs: the shared context, figure styling and help texts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scc_core.custom_params import CustomParam
from scc_core.loader import Dataset

APP_DIR = Path(__file__).resolve().parents[1]
HELP_DIR = APP_DIR / "help"
NONE = "(none)"

AREAS = ["👀 Look", "🗂 Data", "📖 Learn"]
LOOK, DATA, LEARN = AREAS


@dataclass
class Ctx:
    ds: Dataset                 # all rows, with custom parameters applied
    df: pd.DataFrame            # rows passing the sidebar filters
    df_all: pd.DataFrame        # all rows
    params: list[CustomParam]
    numeric: list[str]
    categorical: list[str]
    flags: list[str]
    expert: bool
    label: Callable[[str], str]
    unit_text: Callable[[str], str]
    set_unit: Callable[[dict], None]
    save_params: Callable[[], None]
    add_param: Callable[[CustomParam], None]

    @property
    def cols(self):
        return self.ds.columns


def show_fig(fig: go.Figure) -> None:
    try:
        st.plotly_chart(fig, width="stretch")
    except TypeError:  # older Streamlit
        st.plotly_chart(fig, use_container_width=True)


def style_fig(fig: go.Figure, height: int = 560) -> go.Figure:
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(itemsizing="constant"), hoverlabel=dict(namelength=-1),
    )
    fig.update_xaxes(showline=True, linecolor="#b5b3ad", gridcolor="#ecebe7", zeroline=False)
    fig.update_yaxes(showline=True, linecolor="#b5b3ad", gridcolor="#ecebe7", zeroline=False)
    return fig


def _sections(path: Path) -> dict[str, str]:
    """Split a help file into {heading: text} on '## ' headings."""
    out, key, buf = {}, None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if key is not None:
                out[key] = "\n".join(buf).strip()
            key, buf = line[3:].strip(), []
        elif key is not None:
            buf.append(line)
    if key is not None:
        out[key] = "\n".join(buf).strip()
    return out


@st.cache_data
def glossary() -> dict[str, str]:
    path = HELP_DIR / "glossary.md"
    return {k: " ".join(v.split()) for k, v in _sections(path).items()} if path.exists() else {}


def hint(key: str) -> str | None:
    """One-sentence explanation for a ⓘ tooltip (None if unknown)."""
    return glossary().get(key)


@st.cache_data
def tutorial_steps() -> list[tuple[str, str, str]]:
    """[(step id, title, text)] from help/tutorial.md."""
    path = HELP_DIR / "tutorial.md"
    steps = []
    for head, text in _sections(path).items():
        sid, _, title = head.partition("|")
        steps.append((sid.strip(), title.strip() or sid.strip(), text))
    return steps


@st.cache_data
def articles() -> list[tuple[str, str]]:
    """[(title, markdown)] from help/articles/*.md, in file-name order."""
    out = []
    for path in sorted((HELP_DIR / "articles").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = re.match(r"#\s+(.+)", text)
        title = m.group(1).strip() if m else path.stem
        body = text[m.end():].lstrip() if m else text
        out.append((title, body))
    return out


def next_step(text: str) -> None:
    """The 'what to do next' line at the top of a page."""
    st.info(f"**What to do next:** {text}", icon="👉")


def meaning(var: str, ctx: Ctx) -> str:
    """Plain-language meaning of a variable, for captions and tables."""
    if var in ctx.cols and ctx.cols[var].source == "custom":
        p = next((p for p in ctx.params if p.name == var), None)
        if p is not None and p.description:
            return p.description
    if (h := hint(var)) is not None:
        return h
    if var in ctx.ds.constants:
        p = next((p for p in ctx.params if p.name == var), None)
        return p.description if p else ""
    return ctx.cols[var].note if var in ctx.cols else ""
