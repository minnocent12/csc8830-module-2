"""Standalone Streamlit entry point for the CSc 8830 Module 2 submission app.

Run it from this repository root::

    streamlit run app.py

or from the ``Assignments/`` workspace root::

    streamlit run Module_2/app.py

This is a thin shell. It collects the Module 2 page components and hands them to the shared
renderer. No computer-vision logic is imported here; that lives in the ``module2`` core
modules, which never import Streamlit.
"""
from __future__ import annotations

from module2.webapp.pages import get_pages
from module2.webapp.registry import collect_pages
from module2.webapp.shell import render_app


def main() -> None:
    """Collect the Module 2 pages and render the standalone submission app."""
    render_app(collect_pages([get_pages]))


if __name__ == "__main__":
    main()
