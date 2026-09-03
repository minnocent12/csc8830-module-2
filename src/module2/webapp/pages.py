"""Module 2 Streamlit pages and the ``get_pages`` provider.

Phase 0 ships placeholder pages; each is built in its phase:

===================  =======
Page                 Phase
===================  =======
Calibration          Phase 1
Dimension Estimation  Phase 2
Validation Analysis   Phase 3
Theory                Phase 4
===================  =======
"""
from __future__ import annotations

from module2.webapp._page import PageSpec
from module2.webapp.ui import placeholder_page

_MODULE = "Module 2"


def _calibration_page() -> None:
    placeholder_page("Camera Calibration", "Phase 1")


def _estimation_page() -> None:
    placeholder_page("Dimension Estimation", "Phase 2")


def _validation_page() -> None:
    placeholder_page("Validation Analysis", "Phase 3")


def _theory_page() -> None:
    placeholder_page("Two-Camera Projection Theory", "Phase 4")


def get_pages() -> list[PageSpec]:
    """Return the Module 2 pages contributed to a Streamlit host."""
    return [
        PageSpec(_MODULE, "Calibration", 10, _calibration_page),
        PageSpec(_MODULE, "Dimension Estimation", 20, _estimation_page),
        PageSpec(_MODULE, "Validation Analysis", 30, _validation_page),
        PageSpec(_MODULE, "Theory", 40, _theory_page),
    ]
