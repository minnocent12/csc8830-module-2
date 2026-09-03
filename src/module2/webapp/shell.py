"""Streamlit rendering shell: turn a list of pages into a sidebar-navigated app."""
from __future__ import annotations

from collections import defaultdict
from typing import Sequence

import streamlit as st

from module2.webapp._page import PageSpec


def render_app(pages: Sequence[PageSpec], *, title: str = "CSc 8830 — Module 2") -> None:
    """Render a sidebar of ``pages`` grouped by module label and dispatch to the selection.

    Args:
        pages: the pages to expose, already ordered (see :func:`module2.webapp.registry.collect_pages`).
        title: page/tab title for the app.
    """
    st.set_page_config(page_title=title, layout="wide")

    if not pages:
        st.error("No pages registered.")
        return

    by_module: dict[str, list[PageSpec]] = defaultdict(list)
    for page in pages:
        by_module[page.module_label].append(page)

    with st.sidebar:
        st.title(title)
        module_label = st.selectbox("Module", list(by_module))
        module_pages = by_module[module_label]
        page_label = st.radio("Page", [p.page_label for p in module_pages])

    selected = next(p for p in module_pages if p.page_label == page_label)
    selected.render()
