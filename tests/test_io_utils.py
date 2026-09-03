"""Tests for image IO helpers."""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from module2.io_utils import decode_image_bgr, load_image_bgr, load_image_gray, save_image


def test_save_then_load_png_is_lossless_roundtrip(tmp_path) -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(12, 20, 3), dtype=np.uint8)
    path = save_image(tmp_path / "x.png", img)
    assert path.exists()
    loaded = load_image_bgr(path)
    assert loaded.shape == img.shape
    assert np.array_equal(loaded, img)


def test_save_image_creates_parent_dirs(tmp_path) -> None:
    img = np.zeros((4, 4, 3), np.uint8)
    out = save_image(tmp_path / "nested" / "deep" / "y.png", img)
    assert out.is_file()


def test_load_missing_file_raises_filenotfound(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_image_bgr(tmp_path / "nope.png")


def test_load_image_gray_shape_and_dtype(tmp_path) -> None:
    save_image(tmp_path / "g.png", np.full((8, 10, 3), 127, np.uint8))
    gray = load_image_gray(tmp_path / "g.png")
    assert gray.shape == (8, 10)
    assert gray.dtype == np.uint8


def test_decode_image_bgr_roundtrip() -> None:
    img = np.full((6, 6, 3), (10, 20, 30), np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    assert np.array_equal(decode_image_bgr(buf.tobytes()), img)


def test_decode_image_bgr_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        decode_image_bgr(b"not an image")
