"""The single canonical undistortion + back-projection pipeline for Module 2.

There is exactly **one** estimation path (no "already-undistorted image" mode):

1. The raw distorted image is used for display only; it is never passed through
   ``cv2.undistort`` on the estimation path.
2. ``cv2.undistortPoints(pts, K, dist, P=None)`` maps raw pixel points to **normalized
   camera coordinates** on the ``z = 1`` plane. That output is distortion-corrected *and*
   ``K^-1``-applied in one step. It must **never** be multiplied by ``np.linalg.inv(K)``
   again — doing so is the double-normalization bug this design exists to prevent.
3. Each point becomes a ray ``r = [x_n, y_n, 1]``.
4. Back-projection to the object plane at optical-axis depth ``z_mm``: ``Xc = z_mm * r``.
5. A real-world length is the Euclidean norm of the difference of two back-projected
   points, in millimetres.

Status: stub — implemented in Phase 2.
"""
from __future__ import annotations

import numpy as np


def undistort_points(points_px: np.ndarray, K: np.ndarray, dist: np.ndarray) -> np.ndarray:
    """Map raw-image pixel points to normalized camera coordinates (the ``z = 1`` plane).

    Thin wrapper over ``cv2.undistortPoints(points_px, K, dist, P=None)``. The result is
    already ``K^-1``-applied and distortion-corrected; callers must not apply ``K^-1`` again.

    Args:
        points_px: ``(N, 2)`` pixel coordinates in the raw (distorted) image.
        K: ``(3, 3)`` camera intrinsic matrix.
        dist: distortion coefficients as returned by ``cv2.calibrateCamera``.

    Returns:
        ``(N, 2)`` array of normalized image coordinates ``(x_n, y_n)``.
    """
    raise NotImplementedError("Implemented in Phase 2.")


def backproject_to_object_plane(
    points_px: np.ndarray, K: np.ndarray, dist: np.ndarray, z_mm: float
) -> np.ndarray:
    """Back-project raw pixel points onto a fronto-parallel object plane at depth ``z_mm``.

    Args:
        points_px: ``(N, 2)`` pixel coordinates in the raw image.
        K: ``(3, 3)`` intrinsic matrix.
        dist: distortion coefficients.
        z_mm: object-plane depth along the optical axis, in millimetres (must exceed 2000).

    Returns:
        ``(N, 3)`` array of 3D points in the camera frame, in millimetres.
    """
    raise NotImplementedError("Implemented in Phase 2.")
