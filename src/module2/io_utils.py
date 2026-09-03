"""Image input/output helpers.

Every function returns new arrays or paths; original image files and in-memory arrays are
never modified in place (the "preservation of original images/data" rule in AGENTS.md).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def load_image_bgr(path: str | Path) -> np.ndarray:
    """Load an image from disk as a BGR ``uint8`` array.

    Args:
        path: Path to the image file.

    Returns:
        An ``(H, W, 3)`` BGR ``uint8`` array (OpenCV's native channel order).

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the file exists but cannot be decoded as an image.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"image not found: {path}")
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"could not decode image: {path}")
    return image


def load_image_gray(path: str | Path) -> np.ndarray:
    """Load an image from disk as a single-channel ``uint8`` grayscale array."""
    return cv2.cvtColor(load_image_bgr(path), cv2.COLOR_BGR2GRAY)


def decode_image_bgr(data: bytes) -> np.ndarray:
    """Decode raw image bytes (e.g. an uploaded file) to a BGR ``uint8`` array.

    Raises:
        ValueError: If the bytes cannot be decoded as an image.
    """
    arr = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("could not decode image bytes")
    return image


def save_image(path: str | Path, image: np.ndarray) -> Path:
    """Write ``image`` to ``path``, creating parent directories as needed.

    Args:
        path: Destination path; the extension selects the encoder (``.png``, ``.jpg``, ...).
        image: Image array to write (not modified).

    Returns:
        The path written to.

    Raises:
        ValueError: If the image cannot be written for the given path/extension.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise ValueError(f"could not write image: {path}")
    return path
