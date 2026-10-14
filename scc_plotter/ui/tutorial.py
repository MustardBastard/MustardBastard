"""The interactive tutorial: each step shows a text and changes the screen.

The texts live in help/tutorial.md; this file links each step id to what the
app should show for it.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from ui.common import APP_DIR, DATA, LEARN, LOOK, NONE, tutorial_steps
from ui.look import EVERY, ONE, THREE_D

DONE_FILE = APP_DIR / ".tutorial_done"


def _act(step_id: str, params, save: Callable[[], None]) -> None:
    s = st.session_state
    if step_id == "welcome":
        s.update(area=LOOK, look_view=ONE)
    elif step_id == "which_data":
        s.update(area=LOOK, look_view=ONE)
        s["flag_PWR_Mainstream_Data"] = True
    elif step_id == "first_plot":
        s.update(area=LOOK, look_view=ONE, x="K", y="CGR", log_x=True, log_y=True, color=NONE)
    elif step_id == "lab_effect":
        s.update(area=LOOK, look_view=ONE, x="K", y="CGR", log_x=True, log_y=True, color="Lab")
    elif step_id == "every_param":
        s.update(area=LOOK, look_view=EVERY, y="CGR", log_y=True)
    elif step_id == "three_d":
        s.update(area=LOOK, look_view=THREE_D, z3="CGR", x3="K", y3="CW", log_z3=True,
                 log_x3=True, log_y3=False, color="Lab")
    elif step_id == "data_area":
        s.update(area=DATA, data_view="Who measured what")
    elif step_id == "learn":
        s.update(area=LEARN, learn_article="Cave map")


def start(params, save) -> None:
    steps = tutorial_steps()
    st.session_state.update(tut_on=True, tut_i=0)
    if steps:
        _act(steps[0][0], params, save)


def _go(i: int, params, save) -> None:
    steps = tutorial_steps()
    st.session_state["tut_i"] = i
    _act(steps[i][0], params, save)


def finish() -> None:
    st.session_state["tut_on"] = False
    try:
        DONE_FILE.write_text("done", encoding="utf-8")
    except OSError:
        pass


def first_launch() -> bool:
    return not DONE_FILE.exists()


def render(params, save) -> None:
    if not st.session_state.get("tut_on"):
        return
    steps = tutorial_steps()
    if not steps:
        return
    i = min(st.session_state.get("tut_i", 0), len(steps) - 1)
    sid, title, text = steps[i]
    with st.container(border=True):
        st.markdown(f"🎓 **Tutorial · step {i + 1} of {len(steps)} · {title}**")
        st.markdown(text)
        a, b, _, c = st.columns([1, 1, 3, 1])
        if i > 0:
            a.button("← Back", key="tut_back", on_click=_go, args=(i - 1, params, save))
        if i < len(steps) - 1:
            b.button("Next →", key="tut_next", type="primary", on_click=_go,
                     args=(i + 1, params, save))
        else:
            b.button("Finish ✓", key="tut_done", type="primary", on_click=finish)
        c.button("Skip tutorial", key="tut_skip", on_click=finish)
