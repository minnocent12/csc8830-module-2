"""Small shared Streamlit helpers used by the Module 2 pages."""
from __future__ import annotations

import streamlit as st

#: Standard banner for sections that need real experimental data before they mean anything.
PENDING_BANNER = (
    "**PENDING USER EXPERIMENT — NOT MEASURED.** "
    "This section needs real data collected with your smartphone before its values are meaningful."
)


def pending_experiment_banner(detail: str | None = None) -> None:
    """Show the standard 'pending real data' warning, optionally with extra detail."""
    st.warning(PENDING_BANNER if detail is None else f"{PENDING_BANNER}\n\n{detail}")


def placeholder_page(name: str, phase: str) -> None:
    """Render a 'not implemented yet' stub for a page a later phase will build."""
    st.header(name)
    st.info(f"Not implemented yet — planned for {phase}.")
