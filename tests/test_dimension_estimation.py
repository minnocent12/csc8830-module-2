"""Tests for real-world dimension estimation.

Segments/rectangles of known size are placed in the camera frame at a known depth,
projected through a known camera, and recovered. With zero distortion the recovery is
exact; with distortion it is within the iterative-undistort tolerance.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from module2.dimension_estimation import estimate_length, estimate_width_height
from module2.units import metres_to_mm

K = np.array([[900.0, 0.0, 640.0], [0.0, 900.0, 360.0], [0.0, 0.0, 1.0]])
DIST_ZERO = np.zeros(5)
DIST = np.array([0.10, -0.04, 0.0015, -0.0010, 0.008])


def _project(points_cam: np.ndarray, dist: np.ndarray) -> np.ndarray:
    pts, _ = cv2.projectPoints(
        np.asarray(points_cam, np.float64).reshape(-1, 1, 3),
        np.zeros(3),
        np.zeros(3),
        K,
        np.asarray(dist, np.float64),
    )
    return pts.reshape(-1, 2)


def test_estimate_length_zero_distortion_recovers_known_segment() -> None:
    z = 2600.0
    p = np.array([[-75.0, 0.0, z], [75.0, 0.0, z]])  # 150 mm
    px = _project(p, DIST_ZERO)
    assert estimate_length(px[0], px[1], K, DIST_ZERO, z) == pytest.approx(150.0, rel=1e-6)


def test_estimate_length_with_distortion_recovers_known_segment() -> None:
    z = 2600.0
    p = np.array([[-75.0, 20.0, z], [75.0, 20.0, z]])  # 150 mm
    px = _project(p, DIST)
    assert estimate_length(px[0], px[1], K, DIST, z) == pytest.approx(150.0, rel=1e-3)


def test_estimate_length_scales_with_depth() -> None:
    # Same pixels, deeper plane -> proportionally larger world length.
    px = (np.array([600.0, 360.0]), np.array([760.0, 360.0]))
    near = estimate_length(px[0], px[1], K, DIST_ZERO, 1000.0)
    far = estimate_length(px[0], px[1], K, DIST_ZERO, 2000.0)
    assert far == pytest.approx(2.0 * near, rel=1e-9)


@pytest.mark.parametrize("dist", [DIST_ZERO, DIST])
def test_estimate_width_height_recovers_rectangle(dist: np.ndarray) -> None:
    z = 3000.0
    w_mm, h_mm = 200.0, 120.0
    tl = [-w_mm / 2, -h_mm / 2, z]
    tr = [w_mm / 2, -h_mm / 2, z]
    bl = [-w_mm / 2, h_mm / 2, z]
    px = _project(np.array([tl, tr, bl]), dist)
    dims = estimate_width_height((px[0], px[1]), (px[0], px[2]), K, dist, z)
    rel = 1e-6 if dist is DIST_ZERO else 2e-3
    assert dims["width_mm"] == pytest.approx(w_mm, rel=rel)
    assert dims["height_mm"] == pytest.approx(h_mm, rel=rel)


def test_unit_consistency_metres_in_millimetres_out() -> None:
    assert metres_to_mm(2.6) == pytest.approx(2600.0)
    p = np.array([[-75.0, 0.0, 2600.0], [75.0, 0.0, 2600.0]])  # 150 mm at 2.6 m
    px = _project(p, DIST_ZERO)
    got = estimate_length(px[0], px[1], K, DIST_ZERO, metres_to_mm(2.6))
    assert got == pytest.approx(150.0, rel=1e-6)
