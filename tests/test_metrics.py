"""Tests for validation error statistics.

Every formula is pinned against a hand-computed fixture.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from module2.metrics import compute_error_statistics


def test_hand_computed_statistics() -> None:
    actual = [100.0, 200.0, 50.0]
    estimated = [110.0, 190.0, 55.0]
    #   signed      = [ 10, -10,  5 ]
    #   absolute    = [ 10,  10,  5 ]
    #   percentage  = [ 10,   5, 10 ]
    s = compute_error_statistics(actual, estimated)

    assert s.n == 3
    assert np.allclose(s.signed_error_mm, [10.0, -10.0, 5.0])
    assert np.allclose(s.absolute_error_mm, [10.0, 10.0, 5.0])
    assert np.allclose(s.percentage_error, [10.0, 5.0, 10.0])
    assert s.mean_signed_error_mm == pytest.approx(5.0 / 3.0)
    assert s.mae_mm == pytest.approx(25.0 / 3.0)
    assert s.mape_pct == pytest.approx(25.0 / 3.0)
    assert s.sample_std_mm == pytest.approx(10.40833, rel=1e-5)  # ddof = 1
    assert s.min_error_mm == 5.0
    assert s.max_error_mm == 10.0


def test_sample_std_uses_ddof_one() -> None:
    s = compute_error_statistics([10.0, 10.0], [12.0, 8.0])  # signed = [2, -2]
    assert s.sample_std_mm == pytest.approx(math.sqrt(8.0))  # not 2.0 (that would be ddof=0)


def test_single_value_has_nan_sample_std() -> None:
    s = compute_error_statistics([10.0], [11.0])
    assert s.n == 1
    assert math.isnan(s.sample_std_mm)
    assert s.mean_signed_error_mm == 1.0
    assert s.mae_mm == 1.0
    assert s.mape_pct == pytest.approx(10.0)


def test_rejects_empty() -> None:
    with pytest.raises(ValueError, match="no values"):
        compute_error_statistics([], [])


def test_rejects_unequal_length() -> None:
    with pytest.raises(ValueError, match="same length"):
        compute_error_statistics([1.0, 2.0, 3.0], [1.0, 2.0])


@pytest.mark.parametrize("bad_actual", [[0.0, 5.0], [-1.0, 5.0]])
def test_rejects_nonpositive_actual(bad_actual: list[float]) -> None:
    with pytest.raises(ValueError, match="must be > 0"):
        compute_error_statistics(bad_actual, [1.0, 5.0])


@pytest.mark.parametrize(
    "actual,estimated",
    [([float("nan"), 5.0], [1.0, 5.0]), ([1.0, 5.0], [float("inf"), 5.0])],
)
def test_rejects_nonfinite(actual: list[float], estimated: list[float]) -> None:
    with pytest.raises(ValueError, match="finite"):
        compute_error_statistics(actual, estimated)
