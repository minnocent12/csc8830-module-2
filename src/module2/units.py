"""Unit constants and conversions.

Millimetre (mm) is the single internal length unit for every coordinate, length, and error
statistic in Module 2. Distances a user supplies in metres (notably the object-plane depth
``Z``, which must exceed 2 m) are converted to millimetres exactly once, at the IO boundary,
using the helpers here. No other module should hard-code a metre/millimetre factor.
"""
from __future__ import annotations

#: Millimetres per metre.
M_TO_MM: float = 1000.0


def metres_to_mm(value_m: float) -> float:
    """Convert a length in metres to millimetres."""
    return value_m * M_TO_MM


def mm_to_metres(value_mm: float) -> float:
    """Convert a length in millimetres to metres."""
    return value_mm / M_TO_MM
