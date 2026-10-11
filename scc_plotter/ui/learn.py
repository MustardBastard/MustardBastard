"""📖 Learn: short articles and the glossary, read from the help/ folder."""

from __future__ import annotations

import streamlit as st

from ui.common import HELP_DIR, articles, glossary

GLOSSARY = "Glossary (all terms)"


def render() -> None:
    items = articles()
    titles = [t for t, _ in items] + [GLOSSARY]
    left, right = st.columns([1, 3])
    with left:
        choice = st.radio("Articles", titles, key="learn_article")
        st.caption(f"These texts are plain files in `{HELP_DIR.name}/`. "
                   "Edit them with any text editor; the app picks up changes on restart.")
    with right:
        if choice == GLOSSARY:
            st.markdown("# Glossary")
            for term, text in glossary().items():
                st.markdown(f"**{term}**: {text}")
        else:
            title, body = next((t, b) for t, b in items if t == choice)
            st.markdown(f"# {title}")
            st.markdown(body)
