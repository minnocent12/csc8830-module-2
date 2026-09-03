"""Smartphone camera calibration from chessboard images (OpenCV).

Every result produced here must come from the user's real photographs. Nothing in this
module fabricates intrinsics, distortion coefficients, or reprojection error.

Pipeline
--------
1. Detect the chessboard inner-corner grid in each image
   (:func:`find_chessboard_corners`: ``cv2.findChessboardCorners`` + ``cv2.cornerSubPix``).
2. Pair each detected grid with a metric object-point grid built from the **measured**
   square size (:func:`chessboard_object_points`).
3. Solve for the intrinsics and lens distortion with ``cv2.calibrateCamera``
   (:func:`calibrate`).
4. Report the RMS reprojection error, overall and per view
   (:func:`compute_reprojection_error`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

#: Sub-pixel corner-refinement termination criteria.
_SUBPIX_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
_SUBPIX_WINDOW = (11, 11)

#: Default chessboard inner-corner count ``(cols, rows)``.
DEFAULT_PATTERN_SIZE: tuple[int, int] = (9, 6)


@dataclass
class CalibrationResult:
    """Outcome of a camera-calibration run.

    Attributes:
        camera_matrix: ``(3, 3)`` intrinsic matrix ``K`` (pixels).
        dist_coeffs: distortion coefficients ``(k1, k2, p1, p2, k3, ...)``.
        image_size: ``(width, height)`` in pixels.
        pattern_size: chessboard inner-corner count ``(cols, rows)``.
        square_size_mm: physically measured printed square edge length, in millimetres.
        rms_reprojection_error: overall RMS reprojection error (from ``cv2.calibrateCamera``).
        per_view_errors: RMS reprojection error per accepted image, in pixels.
        used_images: names/paths of images where the chessboard was detected and used.
        failed_images: names/paths of images where detection failed.
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


def parse_pattern_size(spec: str) -> tuple[int, int]:
    """Parse a ``"<cols>x<rows>"`` inner-corner spec (e.g. ``"9x6"``) into ``(cols, rows)``."""
    try:
        a, b = spec.lower().split("x")
        cols, rows = int(a), int(b)
    except ValueError as exc:
        raise ValueError(f"pattern must look like '9x6', got {spec!r}") from exc
    if cols < 2 or rows < 2:
        raise ValueError(f"pattern too small (need >= 2 inner corners each way): {spec!r}")
    return cols, rows


def chessboard_object_points(pattern_size: tuple[int, int], square_size_mm: float) -> np.ndarray:
    """Build the metric object-point grid for one chessboard view.

    Args:
        pattern_size: inner-corner count ``(cols, rows)``.
        square_size_mm: measured square edge length, in millimetres.

    Returns:
        ``(cols * rows, 3)`` ``float32`` array with ``Z = 0`` and spacing ``square_size_mm``.
    """
    cols, rows = pattern_size
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp *= float(square_size_mm)
    return objp


def find_chessboard_corners(
    image_gray: np.ndarray, pattern_size: tuple[int, int]
) -> np.ndarray | None:
    """Detect and sub-pixel-refine chessboard inner corners in a grayscale image.

    Args:
        image_gray: single-channel ``uint8`` image.
        pattern_size: inner-corner count ``(cols, rows)``.

    Returns:
        ``(cols * rows, 2)`` ``float32`` array of refined corner coordinates, or ``None`` if
        the full pattern was not found.

    Raises:
        ValueError: If ``image_gray`` is not single-channel.
    """
    if image_gray.ndim != 2:
        raise ValueError("expected a single-channel grayscale image")
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(image_gray, pattern_size, flags=flags)
    if not found:
        return None
    refined = cv2.cornerSubPix(
        image_gray, corners, _SUBPIX_WINDOW, (-1, -1), _SUBPIX_CRITERIA
    )
    return refined.reshape(-1, 2).astype(np.float32)


def compute_reprojection_error(
    object_points: list[np.ndarray],
    image_points: list[np.ndarray],
    rvecs: list[np.ndarray],
    tvecs: list[np.ndarray],
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> tuple[float, list[float]]:
    """Return ``(overall_rms, per_view_rms)`` reprojection error, in pixels.

    ``overall_rms`` is the root-mean-square over every corner of every view;
    ``per_view_rms`` is the RMS within each view.
    """
    per_view: list[float] = []
    total_sq = 0.0
    total_pts = 0
    for objp, imgp, rvec, tvec in zip(object_points, image_points, rvecs, tvecs):
        projected, _ = cv2.projectPoints(objp, rvec, tvec, camera_matrix, dist_coeffs)
        projected = projected.reshape(-1, 2)
        observed = np.asarray(imgp, dtype=np.float64).reshape(-1, 2)
        sq = np.sum((projected - observed) ** 2, axis=1)
        per_view.append(float(np.sqrt(np.mean(sq))))
        total_sq += float(np.sum(sq))
        total_pts += int(sq.size)
    overall = float(np.sqrt(total_sq / total_pts)) if total_pts else 0.0
    return overall, per_view


def calibrate(
    object_points: list[np.ndarray],
    image_points: list[np.ndarray],
    image_size: tuple[int, int],
    *,
    pattern_size: tuple[int, int],
    square_size_mm: float,
    names: list[str],
) -> CalibrationResult:
    """Solve camera calibration from matched object/image point sets.

    Args:
        object_points: per-view ``(N, 3)`` metric object points (millimetres).
        image_points: per-view ``(N, 2)`` detected pixel corners.
        image_size: ``(width, height)`` in pixels.
        pattern_size: inner-corner count ``(cols, rows)``.
        square_size_mm: measured square edge length, in millimetres.
        names: per-view identifiers, stored on the result.

    Returns:
        A populated :class:`CalibrationResult`.

    Raises:
        ValueError: If fewer than three views are supplied.
    """
    if len(object_points) < 3:
        raise ValueError(f"need at least 3 valid views to calibrate, got {len(object_points)}")
    obj = [np.asarray(o, np.float32).reshape(-1, 1, 3) for o in object_points]
    img = [np.asarray(p, np.float32).reshape(-1, 1, 2) for p in image_points]
    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(obj, img, image_size, None, None)
    _, per_view = compute_reprojection_error(obj, img, rvecs, tvecs, K, dist)
    return CalibrationResult(
        camera_matrix=np.asarray(K, dtype=float),
        dist_coeffs=np.asarray(dist, dtype=float).ravel(),
        image_size=(int(image_size[0]), int(image_size[1])),
        pattern_size=(int(pattern_size[0]), int(pattern_size[1])),
        square_size_mm=float(square_size_mm),
        rms_reprojection_error=float(rms),
        per_view_errors=per_view,
        used_images=list(names),
        failed_images=[],
    )


def calibrate_from_gray_images(
    gray_images: list[np.ndarray],
    names: list[str],
    pattern_size: tuple[int, int],
    square_size_mm: float,
) -> CalibrationResult:
    """Detect corners in each grayscale image, then calibrate.

    Raises:
        ValueError: If the images do not share one resolution, or the chessboard is not
            detected in any image, or fewer than three detections succeed.
    """
    template = chessboard_object_points(pattern_size, square_size_mm)
    obj_points: list[np.ndarray] = []
    img_points: list[np.ndarray] = []
    used: list[str] = []
    failed: list[str] = []
    image_size: tuple[int, int] | None = None

    for gray, name in zip(gray_images, names):
        if gray.ndim != 2:
            raise ValueError(f"{name}: expected a single-channel grayscale image")
        height, width = gray.shape
        size = (int(width), int(height))
        if image_size is None:
            image_size = size
        elif size != image_size:
            raise ValueError(
                f"{name}: image size {size} != {image_size}; all calibration images "
                "must share one resolution"
            )
        corners = find_chessboard_corners(gray, pattern_size)
        if corners is None:
            failed.append(name)
            continue
        obj_points.append(template.copy())
        img_points.append(corners)
        used.append(name)

    if not used:
        raise ValueError("chessboard not detected in any image")

    result = calibrate(
        obj_points,
        img_points,
        image_size,  # type: ignore[arg-type]  # non-None once `used` is non-empty
        pattern_size=pattern_size,
        square_size_mm=square_size_mm,
        names=used,
    )
    result.failed_images = failed
    return result


def calibrate_from_images(
    image_paths: list[str | Path],
    pattern_size: tuple[int, int],
    square_size_mm: float,
) -> CalibrationResult:
    """Run OpenCV camera calibration over a set of chessboard image files."""
    from module2.io_utils import load_image_gray

    paths = [Path(p) for p in image_paths]
    if not paths:
        raise ValueError("no calibration images given")
    grays = [load_image_gray(p) for p in paths]
    return calibrate_from_gray_images(grays, [str(p) for p in paths], pattern_size, square_size_mm)


def draw_corners(
    image_bgr: np.ndarray,
    corners: np.ndarray,
    pattern_size: tuple[int, int],
    *,
    found: bool = True,
) -> np.ndarray:
    """Return a copy of ``image_bgr`` with the detected corners drawn on it."""
    canvas = image_bgr.copy()
    pts = np.asarray(corners, dtype=np.float32).reshape(-1, 1, 2)
    cv2.drawChessboardCorners(canvas, pattern_size, pts, found)
    return canvas


def undistort_image(
    image: np.ndarray, camera_matrix: np.ndarray, dist_coeffs: np.ndarray
) -> np.ndarray:
    """Return a new, lens-distortion-corrected copy of ``image`` (original untouched)."""
    return cv2.undistort(
        image, np.asarray(camera_matrix, dtype=float), np.asarray(dist_coeffs, dtype=float)
    )


def calibration_to_dict(result: CalibrationResult) -> dict:
    """Serialize a :class:`CalibrationResult` to a plain JSON-ready dict."""
    return {
        "camera_matrix": np.asarray(result.camera_matrix, dtype=float).tolist(),
        "dist_coeffs": np.asarray(result.dist_coeffs, dtype=float).ravel().tolist(),
        "image_size": [int(result.image_size[0]), int(result.image_size[1])],
        "pattern_size": [int(result.pattern_size[0]), int(result.pattern_size[1])],
        "square_size_mm": float(result.square_size_mm),
        "num_images": len(result.used_images),
        "rms_reprojection_error": float(result.rms_reprojection_error),
        "per_view_errors": [float(e) for e in result.per_view_errors],
        "used_images": list(result.used_images),
        "failed_images": list(result.failed_images),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "opencv_version": cv2.__version__,
    }


def calibration_to_json(result: CalibrationResult) -> str:
    """Serialize a :class:`CalibrationResult` to a JSON string."""
    return json.dumps(calibration_to_dict(result), indent=2) + "\n"


def save_calibration(result: CalibrationResult, path: str | Path) -> Path:
    """Write a :class:`CalibrationResult` to ``path`` as JSON. Returns the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(calibration_to_json(result))
    return path


def load_calibration(path: str | Path) -> CalibrationResult:
    """Load a :class:`CalibrationResult` from a JSON file written by :func:`save_calibration`."""
    data = json.loads(Path(path).read_text())
    return CalibrationResult(
        camera_matrix=np.asarray(data["camera_matrix"], dtype=float),
        dist_coeffs=np.asarray(data["dist_coeffs"], dtype=float),
        image_size=(int(data["image_size"][0]), int(data["image_size"][1])),
        pattern_size=(int(data["pattern_size"][0]), int(data["pattern_size"][1])),
        square_size_mm=float(data["square_size_mm"]),
        rms_reprojection_error=float(data["rms_reprojection_error"]),
        per_view_errors=[float(e) for e in data.get("per_view_errors", [])],
        used_images=list(data.get("used_images", [])),
        failed_images=list(data.get("failed_images", [])),
    )
