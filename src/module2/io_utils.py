"""Image input/output helpers.

Every function here returns new arrays or paths; original image files and in-memory arrays
are never modified in place (see the "preservation of original images/data" rule in
AGENTS.md).

Status: stub — implemented in Phase 1.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def load_image_bgr(path: str | Path) -> np.ndarray:
    """Load an image from disk as a BGR ``uint8`` array.

    Args:
        path: Path to the image file.

    Returns:
        An ``(H, W, 3)`` BGR ``uint8`` array (OpenCV's native channel order).

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the file cannot be decoded as an image.
    """
    raise NotImplementedError("Implemented in Phase 1.")


def save_image(path: str | Path, image: np.ndarray) -> Path:
    """Write ``image`` to ``path``, creating parent directories as needed.

    Args:
        path: Destination path.
        image: Image array to write (not modified).

    Returns:
        The path written to.
    """
    raise NotImplementedError("Implemented in Phase 1.")
