"""Validation error definitions and statistics.

Single entry point: :func:`compute_error_statistics`. Mean absolute percentage error cannot
be recovered from signed errors alone, so the function takes the actual and estimated value
arrays and derives everything internally.

Per pair (all lengths in millimetres)::

    signed_error_mm    = estimated_mm - actual_mm
    absolute_error_mm  = abs(signed_error_mm)
    percentage_error   = absolute_error_mm / actual_mm * 100        # requires actual_mm > 0

Aggregates::

    mean_signed_error_mm = mean(signed_error_mm)                    # the assignment's "Mean error"
    MAE_mm               = mean(absolute_error_mm)                   # "Mean absolute error"
    MAPE_pct            = mean(percentage_error)                     # "Mean percentage error"
    sample_std_mm        = stdev(signed_error_mm, ddof=1)           # sample std of the SIGNED error, n - 1
    min_error_mm         = min(absolute_error_mm)
    max_error_mm         = max(absolute_error_mm)

Status: stub — implemented in Phase 3.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ErrorStatistics:
    """Per-row errors and aggregate statistics for one dimension (or a combined set).

    Attributes:
        n: number of pairs.
        mean_signed_error_mm: mean of ``estimated - actual``.
        mae_mm: mean absolute error.
        mape_pct: mean absolute percentage error.
        sample_std_mm: sample standard deviation (``ddof=1``) of the signed error; ``nan``
            when ``n < 2``.
        min_error_mm: minimum absolute error.
        max_error_mm: maximum absolute error.
        signed_error_mm: per-row signed errors.
        absolute_error_mm: per-row absolute errors.
        percentage_error: per-row absolute percentage errors.
    """

    n: int
    mean_signed_error_mm: float
    mae_mm: float
    mape_pct: float
    sample_std_mm: float
    min_error_mm: float
    max_error_mm: float
    signed_error_mm: np.ndarray
    absolute_error_mm: np.ndarray
    percentage_error: np.ndarray


def compute_error_statistics(
    actual_values: np.ndarray, estimated_values: np.ndarray
) -> ErrorStatistics:
    """Derive per-row errors and aggregate statistics from actual/estimated value arrays.

    Args:
        actual_values: ground-truth lengths in millimetres; every entry must be > 0.
        estimated_values: estimated lengths in millimetres; same length as ``actual_values``.

    Returns:
        A populated :class:`ErrorStatistics`.

    Raises:
        ValueError: if the arrays differ in length, are empty, or any actual value is <= 0.
    """
    raise NotImplementedError("Implemented in Phase 3.")
