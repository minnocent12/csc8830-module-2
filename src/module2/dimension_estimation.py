"""Real-world 2D object dimension estimation via perspective back-projection.

Uses the single canonical pipeline in :mod:`module2.geometry`: raw pixel points ->
``cv2.undistortPoints(..., P=None)`` -> normalized rays -> scale by the object-plane depth.

Assumptions (canonical text in ``docs/assumptions.md``):

* pinhole camera model; lens distortion removed via ``cv2.undistortPoints`` exactly once
  (the raw image is never separately undistorted on this path);
* the object is planar and its plane is parallel to the sensor plane, so every measured
  point shares one depth ``Z``;
* ``Z`` is the perpendicular object-plane depth along the optical axis, approximated in the
  field by the smartphone camera-body position;
* the same camera, lens, and fixed focus / zoom / resolution as calibration;
* negligible motion blur and rolling-shutter effects;
* pixel points are user-supplied; their localisation error is part of the error budget.

All lengths are millimetres. Callers convert a user-supplied distance in metres to
millimetres once, at the IO boundary (see :func:`module2.units.metres_to_mm`).
"""
from __future__ import annotations

import numpy as np

from module2.geometry import backproject_to_object_plane

#: An ``(x, y)`` pixel coordinate in the raw image.
Point = tuple[float, float]


def estimate_length(
    p1_px: Point, p2_px: Point, K: np.ndarray, dist: np.ndarray | None, z_mm: float
) -> float:
    """Estimate the real-world distance, in millimetres, between two raw-image pixel points.

    Args:
        p1_px, p2_px: the two endpoints, in raw-image pixel coordinates.
        K: ``(3, 3)`` intrinsic matrix.
        dist: distortion coefficients (or ``None`` for zero distortion).
        z_mm: object-plane depth along the optical axis, in millimetres.
    """
    xc = backproject_to_object_plane(np.array([p1_px, p2_px], dtype=np.float64), K, dist, z_mm)
    return float(np.linalg.norm(xc[0] - xc[1]))


def estimate_width_height(
    width_points: tuple[Point, Point],
    height_points: tuple[Point, Point],
    K: np.ndarray,
    dist: np.ndarray | None,
    z_mm: float,
) -> dict[str, float]:
    """Estimate ``{"width_mm": ..., "height_mm": ...}`` from two pixel-point pairs.

    ``width_points`` are the two endpoints spanning the object's width; ``height_points``
    the two spanning its height. Both pairs are measured on the same raw image at the same
    object-plane depth.
    """
    (w1, w2) = width_points
    (h1, h2) = height_points
    return {
        "width_mm": estimate_length(w1, w2, K, dist, z_mm),
        "height_mm": estimate_length(h1, h2, K, dist, z_mm),
    }
