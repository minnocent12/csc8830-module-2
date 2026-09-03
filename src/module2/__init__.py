"""CSc 8830 Module 2 — smartphone camera calibration and real-world 2D object dimension estimation.

Sub-modules
-----------
``units``
    Unit constants and conversions. Millimetre is the internal length unit.
``io_utils``
    Image load/save helpers that never mutate the original data.
``geometry``
    The single canonical undistortion + back-projection pipeline.
``calibration``
    Chessboard detection and OpenCV camera calibration.
``dimension_estimation``
    Object width/height from user pixel points and the object-plane depth.
``metrics``
    Validation error definitions and statistics.
``validation``
    20-trial measurement CSV -> per-row errors + summary.
``webapp``
    Streamlit page components. This is the only sub-package that imports Streamlit.

Core (non-``webapp``) modules never import Streamlit.
"""
from __future__ import annotations

__version__ = "0.1.0"
