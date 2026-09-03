"""The page-provider contract shared by the standalone app and any future course dashboard.

Kept free of Streamlit imports so it can be used in pure unit tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

#: A page render function takes no arguments and draws into the current Streamlit script run.
RenderFn = Callable[[], None]


@dataclass(frozen=True)
class PageSpec:
    """One selectable page in a Streamlit app.

    Attributes:
        module_label: grouping label (e.g. ``"Module 2"``), used by a multi-module dashboard.
        page_label: page name shown in the navigation.
        order: sort key within a module (ascending).
        render: zero-argument callable that renders the page.
    """

    module_label: str
    page_label: str
    order: int
    render: RenderFn
