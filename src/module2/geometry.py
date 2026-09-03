"""The single canonical undistortion + back-projection pipeline for Module 2.

There is exactly **one** estimation path (no "already-undistorted image" mode):

1. The raw distorted image is used for display only; it is never passed through
   ``cv2.undistort`` on the estimation path.
2. :func:`undistort_points` wraps ``cv2.undistortPoints(pts, K, dist, P=None)`` and returns
   **normalized camera coordinates** on the ``z = 1`` plane. That output is
   distortion-corrected *and* ``K^-1``-applied in one step. It must **never** be multiplied
   by ``np.linalg.inv(K)`` again — that double normalization is the bug this design prevents
   (``tests/test_geometry.py`` pins it).
3. Each point becomes a ray ``r = [x_n, y_n, 1]``.
4. :func:`backproject_to_object_plane` scales every ray by the object-plane depth ``z_mm``:
   ``Xc = z_mm * r`` — a point on the object plane at that optical-axis depth (millimetres).
5. A real-world length is the Euclidean norm of the difference of two back-projected points.
"""
from __future__ import annotations

import math

import cv2
import numpy as np


def _as_camera_matrix(K: np.ndarray) -> np.ndarray:
    K = np.asarray(K, dtype=np.float64)
    if K.shape != (3, 3):
        raise ValueError(f"camera matrix K must be 3x3, got shape {K.shape}")
    return K


def _as_points(points_px: np.ndarray) -> np.ndarray:
    pts = np.asarray(points_px, dtype=np.float64).reshape(-1, 2)
    if pts.shape[0] < 1:
        raise ValueError("need at least one pixel point")
    if not np.isfinite(pts).all():
        raise ValueError("pixel points must be finite")
    return pts


def undistort_points(
    points_px: np.ndarray, K: np.ndarray, dist: np.ndarray | None
) -> np.ndarray:
    """Map raw-image pixel points to normalized camera coordinates (the ``z = 1`` plane).

    Thin wrapper over ``cv2.undistortPoints(points_px, K, dist, P=None)``. The result is
    already ``K^-1``-applied and distortion-corrected; callers must not apply ``K^-1`` again.

    Args:
        points_px: ``(N, 2)`` pixel coordinates in the raw (distorted) image.
        K: ``(3, 3)`` camera intrinsic matrix.
        dist: distortion coefficients as returned by ``cv2.calibrateCamera``; ``None`` is
            treated as zero distortion.

    Returns:
        ``(N, 2)`` array of normalized image coordinates ``(x_n, y_n)``.
    """
    pts = _as_points(points_px).reshape(-1, 1, 2)
    K = _as_camera_matrix(K)
    dist_arr = (
        np.zeros(5, dtype=np.float64)
        if dist is None
        else np.asarray(dist, dtype=np.float64).reshape(-1)
    )
    normalized = cv2.undistortPoints(pts, K, dist_arr)  # P=None -> normalized coords
    return np.asarray(normalized, dtype=np.float64).reshape(-1, 2)


def backproject_to_object_plane(
    points_px: np.ndarray, K: np.ndarray, dist: np.ndarray | None, z_mm: float
) -> np.ndarray:
    """Back-project raw pixel points onto a fronto-parallel object plane at depth ``z_mm``.

    Args:
        points_px: ``(N, 2)`` pixel coordinates in the raw image.
        K: ``(3, 3)`` intrinsic matrix.
        dist: distortion coefficients (or ``None`` for zero distortion).
        z_mm: object-plane depth along the optical axis, in millimetres; must be finite
            and > 0.

    Returns:
        ``(N, 3)`` array of 3D points in the camera frame, in millimetres.

    Raises:
        ValueError: If ``z_mm`` is not a finite positive number.
    """
    z = float(z_mm)
    if not math.isfinite(z) or z <= 0.0:
        raise ValueError(f"z_mm must be a finite positive number, got {z_mm!r}")
    normalized = undistort_points(points_px, K, dist)  # (N, 2), on the z = 1 plane
    rays = np.hstack([normalized, np.ones((normalized.shape[0], 1), dtype=np.float64)])
    return rays * z
