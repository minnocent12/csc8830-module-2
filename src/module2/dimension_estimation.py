"""Real-world 2D object dimension estimation via perspective back-projection.

Uses the single canonical pipeline in :mod:`module2.geometry`: raw pixel points ->
``cv2.undistortPoints(..., P=None)`` -> normalized rays -> scale by the object-plane depth.

Assumptions (canonical text in ``docs/assumptions.md``):

* pinhole camera model; lens distortion removed via ``cv2.undistortPoints`` exactly once;
* the object is planar and its plane is parallel to the sensor plane (a single depth ``Z``);
* ``Z`` is the perpendicular object-plane depth along the optical axis, approximated in the
  field by the smartphone camera-body position;
* the same camera, lens, and fixed focus/zoom/resolution as calibration;
* negligible motion blur and rolling-shutter effects;
* pixel points are user-supplied; their localisation error is part of the error budget.

Status: stub — implemented in Phase 2.
"""
from __future__ import annotations

import numpy as np

#: An ``(x, y)`` pixel coordinate in the raw image.
Point = tuple[float, float]


def estimate_length(
    p1_px: Point, p2_px: Point, K: np.ndarray, dist: np.ndarray, z_mm: float
) -> float:
    """Estimate the real-world distance, in millimetres, between two raw-image pixel points.

    Args:
        p1_px, p2_px: the two endpoints, in raw-image pixel coordinates.
        K: ``(3, 3)`` intrinsic matrix.
        dist: distortion coefficients.
        z_mm: object-plane depth along the optical axis, in millimetres.
    """
    raise NotImplementedError("Implemented in Phase 2.")


def estimate_width_height(
    width_points: tuple[Point, Point],
    height_points: tuple[Point, Point],
    K: np.ndarray,
    dist: np.ndarray,
    z_mm: float,
) -> dict[str, float]:
    """Estimate ``{"width_mm": ..., "height_mm": ...}`` from two pixel-point pairs."""
    raise NotImplementedError("Implemented in Phase 2.")
