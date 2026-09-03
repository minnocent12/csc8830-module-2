"""Tests for the canonical undistortion + back-projection pipeline.

Points are projected through a known camera with ``cv2.projectPoints`` (camera frame ==
world frame, ``rvec = tvec = 0``), so the expected normalized coordinates and 3D points are
exact.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from module2.geometry import backproject_to_object_plane, undistort_points

K = np.array([[900.0, 0.0, 640.0], [0.0, 900.0, 360.0], [0.0, 0.0, 1.0]])
DIST_ZERO = np.zeros(5)
DIST = np.array([0.12, -0.05, 0.001, -0.002, 0.01])


def _project(points_cam: np.ndarray, dist: np.ndarray) -> np.ndarray:
    pts, _ = cv2.projectPoints(
        np.asarray(points_cam, np.float64).reshape(-1, 1, 3),
        np.zeros(3),
        np.zeros(3),
        K,
        np.asarray(dist, np.float64),
    )
    return pts.reshape(-1, 2)


def test_undistort_points_zero_distortion_matches_Kinv() -> None:
    px = np.array([[640.0, 360.0], [740.0, 360.0], [640.0, 460.0]])
    got = undistort_points(px, K, DIST_ZERO)
    expected = np.column_stack([(px[:, 0] - 640.0) / 900.0, (px[:, 1] - 360.0) / 900.0])
    assert np.allclose(got, expected, atol=1e-9)


def test_undistort_points_recovers_normalized_coords_with_distortion() -> None:
    cam = np.array(
        [[-120.0, -80.0, 2000.0], [90.0, 40.0, 2000.0], [0.0, 0.0, 2000.0], [200.0, -150.0, 2500.0]]
    )
    true_norm = cam[:, :2] / cam[:, 2:3]
    px = _project(cam, DIST)
    got = undistort_points(px, K, DIST)
    assert np.allclose(got, true_norm, atol=1e-3)


def test_undistort_points_validates_camera_matrix_shape() -> None:
    with pytest.raises(ValueError, match="3x3"):
        undistort_points(np.array([[1.0, 2.0]]), np.eye(2), DIST_ZERO)


def test_backproject_principal_point_and_linear_depth_scaling() -> None:
    at_pp = backproject_to_object_plane(np.array([[640.0, 360.0]]), K, DIST_ZERO, 1000.0)
    assert np.allclose(at_pp[0], [0.0, 0.0, 1000.0], atol=1e-6)

    off = np.array([[840.0, 360.0]])
    near = backproject_to_object_plane(off, K, DIST_ZERO, 1000.0)
    far = backproject_to_object_plane(off, K, DIST_ZERO, 2000.0)
    assert np.allclose(far, 2.0 * near, rtol=1e-9)
    assert near[0, 2] == pytest.approx(1000.0)


@pytest.mark.parametrize("bad_z", [0.0, -10.0, float("nan"), float("inf")])
def test_backproject_rejects_bad_depth(bad_z: float) -> None:
    with pytest.raises(ValueError, match="finite positive"):
        backproject_to_object_plane(np.array([[640.0, 360.0]]), K, DIST_ZERO, bad_z)


def test_double_normalization_collapses_scale_and_is_wrong() -> None:
    """Applying K^-1 to undistortPoints output (already normalized) is the bug to prevent."""
    z = 2500.0
    p_true = np.array([[-50.0, 0.0, z], [50.0, 0.0, z]])  # 100 mm segment at depth z
    px = _project(p_true, DIST_ZERO)

    # Correct: one-step normalized coords -> scale by depth.
    xc = backproject_to_object_plane(px, K, DIST_ZERO, z)
    correct_len = float(np.linalg.norm(xc[0] - xc[1]))
    assert correct_len == pytest.approx(100.0, rel=1e-6)

    # Wrong: multiply the already-normalized coords by K^-1 again.
    n = undistort_points(px, K, DIST_ZERO)
    rays = np.hstack([n, np.ones((2, 1))])
    bad = (np.linalg.inv(K) @ rays.T).T * z
    bad_len = float(np.linalg.norm(bad[0] - bad[1]))
    assert bad_len < 1.0  # collapsed by ~fx; nowhere near 100 mm
    assert abs(bad_len - correct_len) > 50.0
