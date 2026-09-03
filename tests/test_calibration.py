"""Tests for camera calibration.

The calibration *math* is exercised with synthetic points projected through a known camera
(no rendered images), so the expected intrinsics are exact. Corner *detection* is exercised
separately against a rendered chessboard and against blank images.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from module2.calibration import (
    calibrate,
    calibrate_from_gray_images,
    chessboard_object_points,
    compute_reprojection_error,
    find_chessboard_corners,
    load_calibration,
    parse_pattern_size,
    save_calibration,
    undistort_image,
)

PATTERN = (9, 6)
SQUARE_MM = 25.0
IMAGE_SIZE = (640, 480)  # (width, height)
K_TRUE = np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]])
DIST_TRUE = np.zeros(5)


def _synthetic_views(n: int = 30, seed: int = 0):
    """Project the board through K_TRUE from many poses; keep views fully in frame."""
    rng = np.random.default_rng(seed)
    objp = chessboard_object_points(PATTERN, SQUARE_MM)
    obj_list: list[np.ndarray] = []
    img_list: list[np.ndarray] = []
    for _ in range(n):
        rvec = rng.uniform(-0.3, 0.3, size=3)
        tvec = np.array(
            [rng.uniform(-60.0, 60.0), rng.uniform(-45.0, 45.0), rng.uniform(750.0, 1300.0)]
        )
        pts, _ = cv2.projectPoints(objp, rvec, tvec, K_TRUE, DIST_TRUE)
        pts = pts.reshape(-1, 2)
        if (
            pts[:, 0].min() < 5
            or pts[:, 0].max() > IMAGE_SIZE[0] - 5
            or pts[:, 1].min() < 5
            or pts[:, 1].max() > IMAGE_SIZE[1] - 5
        ):
            continue
        obj_list.append(objp.copy())
        img_list.append(pts.astype(np.float32))
    return obj_list, img_list


def _render_chessboard(pattern_size: tuple[int, int], square_px: int = 40, margin: int = 50):
    cols, rows = pattern_size
    sq_cols, sq_rows = cols + 1, rows + 1
    h = sq_rows * square_px + 2 * margin
    w = sq_cols * square_px + 2 * margin
    img = np.full((h, w), 255, np.uint8)
    for r in range(sq_rows):
        for c in range(sq_cols):
            if (r + c) % 2 == 0:
                y0, x0 = margin + r * square_px, margin + c * square_px
                img[y0 : y0 + square_px, x0 : x0 + square_px] = 0
    return img


def test_chessboard_object_points_grid() -> None:
    objp = chessboard_object_points((9, 6), 25.0)
    assert objp.shape == (54, 3)
    assert np.all(objp[:, 2] == 0.0)
    assert objp[:, :2].min() == 0.0
    assert objp[:, 0].max() == pytest.approx(25.0 * 8)
    assert objp[:, 1].max() == pytest.approx(25.0 * 5)


def test_parse_pattern_size() -> None:
    assert parse_pattern_size("9x6") == (9, 6)
    assert parse_pattern_size("7X5") == (7, 5)
    with pytest.raises(ValueError):
        parse_pattern_size("bogus")
    with pytest.raises(ValueError):
        parse_pattern_size("1x4")


def test_calibrate_recovers_known_intrinsics() -> None:
    obj_list, img_list = _synthetic_views(n=40, seed=1)
    assert len(obj_list) >= 10
    result = calibrate(
        obj_list,
        img_list,
        IMAGE_SIZE,
        pattern_size=PATTERN,
        square_size_mm=SQUARE_MM,
        names=[f"v{i}" for i in range(len(obj_list))],
    )
    K = result.camera_matrix
    assert K[0, 0] == pytest.approx(800.0, rel=0.02)
    assert K[1, 1] == pytest.approx(800.0, rel=0.02)
    assert K[0, 2] == pytest.approx(320.0, abs=10.0)
    assert K[1, 2] == pytest.approx(240.0, abs=10.0)
    assert np.allclose(result.dist_coeffs, 0.0, atol=1e-2)
    assert result.rms_reprojection_error < 1e-2
    assert result.image_size == IMAGE_SIZE
    assert result.square_size_mm == pytest.approx(SQUARE_MM)


def test_calibrate_rejects_too_few_views() -> None:
    obj_list, img_list = _synthetic_views(n=10, seed=2)
    with pytest.raises(ValueError):
        calibrate(
            obj_list[:2],
            img_list[:2],
            IMAGE_SIZE,
            pattern_size=PATTERN,
            square_size_mm=SQUARE_MM,
            names=["a", "b"],
        )


def test_reprojection_error_zero_for_exact_projection() -> None:
    obj_list, img_list = _synthetic_views(n=12, seed=3)
    rvecs, tvecs = [], []
    for objp, imgp in zip(obj_list, img_list):
        ok, rvec, tvec = cv2.solvePnP(objp, imgp, K_TRUE, DIST_TRUE)
        assert ok
        rvecs.append(rvec)
        tvecs.append(tvec)
    overall, per_view = compute_reprojection_error(
        obj_list, img_list, rvecs, tvecs, K_TRUE, DIST_TRUE
    )
    # solvePnP is an iterative solve; its residual is sub-milli-pixel, i.e. effectively zero.
    assert overall < 1e-3
    assert max(per_view) < 1e-3


def test_find_chessboard_corners_detects_rendered_board() -> None:
    board = _render_chessboard(PATTERN)
    corners = find_chessboard_corners(board, PATTERN)
    assert corners is not None
    assert corners.shape == (PATTERN[0] * PATTERN[1], 2)
    assert corners.dtype == np.float32


def test_find_chessboard_corners_returns_none_on_blank() -> None:
    assert find_chessboard_corners(np.zeros((480, 640), np.uint8), PATTERN) is None
    assert find_chessboard_corners(np.full((480, 640), 127, np.uint8), PATTERN) is None


def test_find_chessboard_corners_rejects_colour_image() -> None:
    with pytest.raises(ValueError):
        find_chessboard_corners(np.zeros((10, 10, 3), np.uint8), PATTERN)


def test_calibrate_from_gray_images_requires_consistent_resolution() -> None:
    a = _render_chessboard(PATTERN)
    b = np.full((a.shape[0] + 20, a.shape[1], 3), 255, np.uint8)[:, :, 0]
    with pytest.raises(ValueError):
        calibrate_from_gray_images([a, b], ["a", "b"], PATTERN, SQUARE_MM)


def test_calibrate_from_gray_images_raises_when_no_board_detected() -> None:
    blanks = [np.zeros((200, 200), np.uint8) for _ in range(3)]
    with pytest.raises(ValueError):
        calibrate_from_gray_images(blanks, ["a", "b", "c"], PATTERN, SQUARE_MM)


def test_save_and_load_calibration_roundtrip(tmp_path) -> None:
    obj_list, img_list = _synthetic_views(n=30, seed=4)
    result = calibrate(
        obj_list,
        img_list,
        IMAGE_SIZE,
        pattern_size=PATTERN,
        square_size_mm=SQUARE_MM,
        names=[f"v{i}" for i in range(len(obj_list))],
    )
    path = save_calibration(result, tmp_path / "calibration.json")
    loaded = load_calibration(path)
    assert np.allclose(loaded.camera_matrix, result.camera_matrix)
    assert np.allclose(loaded.dist_coeffs, result.dist_coeffs)
    assert loaded.image_size == result.image_size
    assert loaded.pattern_size == result.pattern_size
    assert loaded.square_size_mm == pytest.approx(result.square_size_mm)
    assert loaded.rms_reprojection_error == pytest.approx(result.rms_reprojection_error)


def test_undistort_image_returns_new_array_without_mutating_input() -> None:
    img = np.random.default_rng(0).integers(0, 256, (32, 40, 3), dtype=np.uint8)
    snapshot = img.copy()
    out = undistort_image(img, K_TRUE, DIST_TRUE)
    assert np.array_equal(img, snapshot)
    assert out.shape == img.shape
