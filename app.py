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

import sys
from pathlib import Path

# Run straight from a clone even if the editable install's .pth is not honoured
# (seen on some Python 3.14 builds). Harmless when `module2` is already importable.
_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from module2.webapp.pages import get_pages  # noqa: E402
from module2.webapp.registry import collect_pages  # noqa: E402
from module2.webapp.shell import render_app  # noqa: E402


def main() -> None:
    """Collect the Module 2 pages and render the standalone submission app."""
    render_app(collect_pages([get_pages]))


if __name__ == "__main__":
    main()
