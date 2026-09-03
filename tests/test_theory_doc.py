"""Guards that the two-camera projection derivation stays complete and self-consistent.

The assignment's "Items to Address" list is turned into presence checks, and the worked
numerical example in the document is recomputed and compared to the printed values.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

DOC = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "theory_two_camera_projection.md"
)


@pytest.fixture(scope="module")
def text() -> str:
    # collapse whitespace so presence checks are robust to hard line-wrapping
    return " ".join(DOC.read_text(encoding="utf-8").split())


def test_document_exists() -> None:
    assert DOC.is_file()


@pytest.mark.parametrize(
    "needle",
    [
        # 1. coordinate systems
        "## 1. Coordinate systems",
        "World $\\{W\\}$",
        "Camera 1 $\\{C_1\\}$",
        "Camera 2 $\\{C_2\\}$",
        # 2. intrinsics + how calibration yields K
        "f_x & s & c_x",
        "principal point",
        "skew",
        "cv2.calibrateCamera",
        # 3. camera 1 projection with R1 = I, t1 = 0 justified
        "K_1\\,[\\,R_1 \\mid t_1\\,]",
        "R_1 = I",
        "t_1 = 0",
        "loses no generality",
        # 4. camera 2 transformation
        "P_2 = R\\,P_1 + t",
        "relative rotation",
        "baseline length",
        # 5. camera 2 projection
        "K_2\\,[\\,R \\mid t\\,]",
        "\\lambda_2 = (R\\,P_1 + t)_z",
        # 6. relationship: epipolar, essential, fundamental
        "epipolar line",
        "E = [t]_\\times R",
        "F = K_2^{-\\top} [t]_\\times R\\, K_1^{-1}",
        "x_2^\\top F\\,x_1 = 0",
        "epipole",
        # 7. parameter classification table
        "## 7. Parameters and variables",
        "known / static",
        "measured variable",
        # 8. assumptions
        "## 8. Assumptions",
        "Lens distortion removed",
        # 9. example is labelled synthetic
        "synthetic",
        "not* measured",
    ],
)
def test_covers_required_item(text: str, needle: str) -> None:
    assert needle in text


def test_worked_example_matches_recomputation(text: str) -> None:
    K = np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]])
    th = np.deg2rad(10.0)
    R = np.array(
        [[np.cos(th), 0.0, np.sin(th)], [0.0, 1.0, 0.0], [-np.sin(th), 0.0, np.cos(th)]]
    )
    t = np.array([-120.0, 0.0, -15.0])
    P1 = np.array([40.0, 30.0, 1000.0])

    u1 = K @ (P1 / P1[2])
    P2 = R @ P1 + t
    u2 = K @ (P2 / P2[2])
    tx = np.array([[0, -t[2], t[1]], [t[2], 0, -t[0]], [-t[1], t[0], 0.0]])
    E = tx @ R
    x1h, x2h = P1 / P1[2], P2 / P2[2]

    # epipolar constraint holds for the stated point
    assert abs(float(x2h @ E @ x1h)) < 1e-9

    # printed values in the document match the recomputation
    assert f"({u1[0]:.3f},\\ {u1[1]:.3f})" in text  # (352.000, 264.000)
    assert f"({u2[0]:.4f},\\ {u2[1]:.4f})" in text  # (397.3033, 264.9257)
    assert f"E = [t]_\\times R = \\begin{{bmatrix}} 0 & {E[0,1]:.0f} & 0" in text
