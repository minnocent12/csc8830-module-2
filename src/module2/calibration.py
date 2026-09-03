"""Smartphone camera calibration from chessboard images (OpenCV).

Every result produced here must come from the user's real photographs. Nothing in this
module fabricates intrinsics, distortion coefficients, or reprojection error.

Status: stub — implemented in Phase 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class CalibrationResult:
    """Outcome of a camera-calibration run.

    Attributes:
        camera_matrix: ``(3, 3)`` intrinsic matrix ``K``.
        dist_coeffs: distortion coefficients ``(k1, k2, p1, p2, k3, ...)``.
        image_size: ``(width, height)`` in pixels.
        pattern_size: chessboard inner-corner count ``(cols, rows)``.
        square_size_mm: physically measured printed square edge length, in millimetres.
        rms_reprojection_error: overall RMS reprojection error from ``cv2.calibrateCamera``.
        per_view_errors: mean reprojection error per accepted image.
        used_images: image paths where the chessboard was detected and used.
        failed_images: image paths where detection failed.
    """

    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    image_size: tuple[int, int]
    pattern_size: tuple[int, int]
    square_size_mm: float
    rms_reprojection_error: float
    per_view_errors: list[float] = field(default_factory=list)
    used_images: list[str] = field(default_factory=list)
    failed_images: list[str] = field(default_factory=list)


def find_chessboard_corners(
    image_gray: np.ndarray, pattern_size: tuple[int, int]
) -> np.ndarray | None:
    """Detect and sub-pixel-refine chessboard inner corners in a grayscale image.

    Args:
        image_gray: single-channel ``uint8`` image.
        pattern_size: inner-corner count ``(cols, rows)``.

    Returns:
        ``(N, 2)`` array of refined corner coordinates, or ``None`` if the full pattern
        was not found.
    """
    raise NotImplementedError("Implemented in Phase 1.")


def calibrate_from_images(
    image_paths: list[str | Path],
    pattern_size: tuple[int, int],
    square_size_mm: float,
) -> CalibrationResult:
    """Run OpenCV camera calibration over a set of chessboard images.

    Args:
        image_paths: paths to the calibration photographs.
        pattern_size: inner-corner count ``(cols, rows)``.
        square_size_mm: measured printed square edge length, in millimetres.

    Returns:
        A populated :class:`CalibrationResult`.
    """
    raise NotImplementedError("Implemented in Phase 1.")


def compute_reprojection_error(
    object_points: list[np.ndarray],
    image_points: list[np.ndarray],
    rvecs: list[np.ndarray],
    tvecs: list[np.ndarray],
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> tuple[float, list[float]]:
    """Return ``(overall_rms, per_view_errors)`` for a calibration solution."""
    raise NotImplementedError("Implemented in Phase 1.")


def save_calibration(result: CalibrationResult, path: str | Path) -> Path:
    """Serialize a :class:`CalibrationResult` to JSON. Returns the path written."""
    raise NotImplementedError("Implemented in Phase 1.")


def load_calibration(path: str | Path) -> CalibrationResult:
    """Load a :class:`CalibrationResult` from JSON."""
    raise NotImplementedError("Implemented in Phase 1.")


def undistort_image(
    image: np.ndarray, camera_matrix: np.ndarray, dist_coeffs: np.ndarray
) -> np.ndarray:
    """Return a new, lens-distortion-corrected copy of ``image`` (original untouched)."""
    raise NotImplementedError("Implemented in Phase 1.")
