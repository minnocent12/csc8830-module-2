"""Module 2 Streamlit pages and the ``get_pages`` provider.

===================  =======
Page                 Phase
===================  =======
Calibration          Phase 1  (implemented)
Dimension Estimation  Phase 2
Validation Analysis   Phase 3
Theory                Phase 4
===================  =======
"""
from __future__ import annotations

import cv2
import numpy as np
import streamlit as st

from module2 import calibration as calib
from module2.io_utils import decode_image_bgr
from module2.webapp._page import PageSpec
from module2.webapp.ui import pending_experiment_banner, placeholder_page

_MODULE = "Module 2"
_IMAGE_TYPES = ["jpg", "jpeg", "png", "bmp", "tif", "tiff"]


def _calibration_page() -> None:
    st.header("Camera Calibration")
    st.write(
        "Calibrate the smartphone camera from chessboard photos. Follow "
        "`docs/calibration_capture_protocol.md` first, and enter the **measured** square "
        "edge length (not the nominal print size)."
    )

    c1, c2, c3 = st.columns(3)
    cols = int(c1.number_input("Inner corners — columns", min_value=2, max_value=30, value=9))
    rows = int(c2.number_input("Inner corners — rows", min_value=2, max_value=30, value=6))
    square_mm = float(
        c3.number_input(
            "Measured square edge (mm)", min_value=0.1, value=25.0, step=0.1, format="%.1f"
        )
    )
    pattern_size = (cols, rows)

    uploads = st.file_uploader(
        "Chessboard images", type=_IMAGE_TYPES, accept_multiple_files=True
    )
    if not uploads:
        pending_experiment_banner(
            "Upload 15–25 chessboard photos taken with your smartphone to run calibration."
        )
        return

    grays: list[np.ndarray] = []
    names: list[str] = []
    previews: list[tuple[str, np.ndarray, np.ndarray | None]] = []
    for f in uploads:
        try:
            bgr = decode_image_bgr(f.getvalue())
        except ValueError:
            st.warning(f"{f.name}: could not decode as an image — skipped.")
            continue
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        corners = calib.find_chessboard_corners(gray, pattern_size)
        grays.append(gray)
        names.append(f.name)
        previews.append((f.name, bgr, corners))

    detected = sum(1 for _, _, c in previews if c is not None)
    st.caption(f"Chessboard detected in {detected} / {len(previews)} images.")

    with st.expander("Corner-detection previews"):
        for name, bgr, corners in previews:
            if corners is not None:
                vis = calib.draw_corners(bgr, corners, pattern_size)
                st.image(
                    cv2.cvtColor(vis, cv2.COLOR_BGR2RGB),
                    caption=f"{name} — detected",
                    use_container_width=True,
                )
            else:
                st.image(
                    cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB),
                    caption=f"{name} — NOT detected",
                    use_container_width=True,
                )

    if not st.button("Run calibration", type="primary"):
        return

    try:
        result = calib.calibrate_from_gray_images(grays, names, pattern_size, square_mm)
    except ValueError as exc:
        st.error(f"Calibration failed: {exc}")
        return

    K = np.asarray(result.camera_matrix, dtype=float)
    st.subheader("Camera intrinsic matrix K (pixels)")
    st.dataframe(K)
    st.write(
        f"fx = {K[0, 0]:.2f}  ·  fy = {K[1, 1]:.2f}  ·  "
        f"cx = {K[0, 2]:.2f}  ·  cy = {K[1, 2]:.2f}"
    )

    st.subheader("Distortion coefficients  (k1, k2, p1, p2, k3, …)")
    st.write(np.asarray(result.dist_coeffs, dtype=float).ravel().tolist())

    st.subheader("Reprojection error")
    st.metric("Overall RMS (px)", f"{result.rms_reprojection_error:.4f}")
    if result.per_view_errors:
        st.bar_chart({"per-view RMS (px)": result.per_view_errors})

    st.caption(
        f"{len(result.used_images)} / {len(previews)} images used."
        + (
            "  Not used (no chessboard): " + ", ".join(result.failed_images)
            if result.failed_images
            else ""
        )
    )

    st.download_button(
        "Download calibration.json",
        data=calib.calibration_to_json(result),
        file_name="calibration.json",
        mime="application/json",
    )


def _estimation_page() -> None:
    placeholder_page("Dimension Estimation", "Phase 2")


def _validation_page() -> None:
    placeholder_page("Validation Analysis", "Phase 3")


def _theory_page() -> None:
    placeholder_page("Two-Camera Projection Theory", "Phase 4")


def get_pages() -> list[PageSpec]:
    """Return the Module 2 pages contributed to a Streamlit host."""
    return [
        PageSpec(_MODULE, "Calibration", 10, _calibration_page),
        PageSpec(_MODULE, "Dimension Estimation", 20, _estimation_page),
        PageSpec(_MODULE, "Validation Analysis", 30, _validation_page),
        PageSpec(_MODULE, "Theory", 40, _theory_page),
    ]
