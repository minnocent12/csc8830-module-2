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

import json

import cv2
import numpy as np
import streamlit as st

from module2 import calibration as calib
from module2.dimension_estimation import estimate_width_height
from module2.io_utils import decode_image_bgr
from module2.units import metres_to_mm
from module2.validation import (
    compute_errors,
    parse_measurements_text,
    row_error_columns,
    to_markdown_table,
)
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


def _point_inputs(label: str, defaults: tuple[float, float, float, float]) -> tuple[
    tuple[float, float], tuple[float, float]
]:
    st.markdown(f"**{label}** — two endpoint pixels")
    c1, c2, c3, c4 = st.columns(4)
    x1 = c1.number_input(f"{label} p1 x", value=float(defaults[0]), key=f"{label}_x1")
    y1 = c2.number_input(f"{label} p1 y", value=float(defaults[1]), key=f"{label}_y1")
    x2 = c3.number_input(f"{label} p2 x", value=float(defaults[2]), key=f"{label}_x2")
    y2 = c4.number_input(f"{label} p2 y", value=float(defaults[3]), key=f"{label}_y2")
    return (float(x1), float(y1)), (float(x2), float(y2))


def _estimation_page() -> None:
    st.header("Dimension Estimation")
    st.write(
        "Estimate an object's real-world width and height by back-projecting user-selected "
        "pixel points onto a fronto-parallel plane at the measured optical-axis depth. "
        "See `docs/assumptions.md`. No automatic object detection — you supply the points."
    )

    image_file = st.file_uploader("Object image (raw, undistorted-free)", type=_IMAGE_TYPES)
    calib_file = st.file_uploader("calibration.json", type=["json"])
    if image_file is None or calib_file is None:
        pending_experiment_banner(
            "Upload the object image and the calibration.json produced on the Calibration page."
        )
        return

    try:
        bgr = decode_image_bgr(image_file.getvalue())
    except ValueError:
        st.error("Could not decode the image.")
        return
    try:
        calibration = calib.calibration_from_dict(json.loads(calib_file.getvalue()))
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        st.error(f"Could not read calibration.json: {exc}")
        return

    h, w = bgr.shape[:2]
    st.image(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), caption=f"{w}×{h} px", use_container_width=True)

    distance_m = float(
        st.number_input(
            "Object-plane depth Z along the optical axis (metres)",
            min_value=0.1,
            value=2.5,
            step=0.05,
            format="%.2f",
        )
    )
    if distance_m <= 2.0:
        st.info("Step 3 validation requires the object-plane depth to exceed 2 m.")

    width_pts = _point_inputs("Width", (w * 0.25, h * 0.5, w * 0.75, h * 0.5))
    height_pts = _point_inputs("Height", (w * 0.5, h * 0.25, w * 0.5, h * 0.75))

    if not st.button("Estimate dimensions", type="primary"):
        return

    for name, pts in (("Width", width_pts), ("Height", height_pts)):
        for x, y in pts:
            if not (0 <= x < w and 0 <= y < h):
                st.error(f"{name} point ({x:.0f}, {y:.0f}) is outside the image.")
                return

    z_mm = metres_to_mm(distance_m)
    dims = estimate_width_height(
        width_pts, height_pts, calibration.camera_matrix, calibration.dist_coeffs, z_mm
    )

    annotated = bgr.copy()
    for (p1, p2), colour in ((width_pts, (0, 0, 255)), (height_pts, (0, 200, 0))):
        a = tuple(int(round(v)) for v in p1)
        b = tuple(int(round(v)) for v in p2)
        cv2.line(annotated, a, b, colour, 2)
        cv2.circle(annotated, a, 5, colour, -1)
        cv2.circle(annotated, b, 5, colour, -1)
    st.image(
        cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB),
        caption="Red = width, green = height",
        use_container_width=True,
    )

    m1, m2 = st.columns(2)
    m1.metric("Width", f"{dims['width_mm']:.1f} mm", f"{dims['width_mm'] / 10:.2f} cm")
    m2.metric("Height", f"{dims['height_mm']:.1f} mm", f"{dims['height_mm'] / 10:.2f} cm")
    st.caption(
        f"Z = {distance_m:.2f} m ({z_mm:.0f} mm). Distortion removed once via "
        "cv2.undistortPoints; fronto-parallel plane assumed."
    )


def _validation_page() -> None:
    st.header("Validation Analysis")
    st.write(
        "Analyse the 20-trial measurement CSV: per-row errors plus width / height / combined "
        "statistics. See `docs/validation_protocol.md`. Rows with object-plane depth "
        "≤ 2 m, non-positive ground truth, or missing points are rejected."
    )

    csv_file = st.file_uploader("Measurements CSV (from measurements_template.csv)", type=["csv"])
    calib_file = st.file_uploader("calibration.json", type=["json"])
    if csv_file is None or calib_file is None:
        pending_experiment_banner(
            "Upload your filled measurements CSV and calibration.json. No data is present "
            "until you collect the 20 real measurements."
        )
        return

    try:
        rows = parse_measurements_text(csv_file.getvalue().decode("utf-8"))
        calibration = calib.calibration_from_dict(json.loads(calib_file.getvalue()))
    except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        st.error(f"Could not read inputs: {exc}")
        return

    summary = compute_errors(rows, calibration)

    if not summary.rows:
        st.warning(
            "No rows passed the acceptance rules yet — the template is empty or every row "
            "was rejected."
        )
    else:
        table = [
            {
                "id": r.measurement_id,
                "object": r.object_name,
                "Z (m)": round(r.object_plane_depth_z_m, 3),
                "actual W": round(r.actual_width_mm, 2),
                "est W": round(row_error_columns(r)["estimated_width_mm"], 2),
                "W abs err": round(row_error_columns(r)["width_absolute_error_mm"], 2),
                "W %": round(row_error_columns(r)["width_percentage_error"], 2),
                "actual H": round(r.actual_height_mm, 2),
                "est H": round(row_error_columns(r)["estimated_height_mm"], 2),
                "H abs err": round(row_error_columns(r)["height_absolute_error_mm"], 2),
                "H %": round(row_error_columns(r)["height_percentage_error"], 2),
            }
            for r in summary.rows
        ]
        st.dataframe(table, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        for col, label, stats in (
            (c1, "Width", summary.width_stats),
            (c2, "Height", summary.height_stats),
            (c3, "Combined", summary.combined_stats),
        ):
            col.markdown(f"**{label}**")
            col.metric("MAE (mm)", f"{stats.mae_mm:.2f}")
            col.metric("MAPE (%)", f"{stats.mape_pct:.2f}")
            col.caption(
                f"mean signed {stats.mean_signed_error_mm:.2f} mm · "
                f"std(n-1) {stats.sample_std_mm:.2f} mm · "
                f"min {stats.min_error_mm:.2f} · max {stats.max_error_mm:.2f}"
            )

        actual, estimated = [], []
        for r in summary.rows:
            e = row_error_columns(r)
            actual += [r.actual_width_mm, r.actual_height_mm]
            estimated += [e["estimated_width_mm"], e["estimated_height_mm"]]
        st.scatter_chart(
            {"actual (mm)": actual, "estimated (mm)": estimated},
            x="actual (mm)",
            y="estimated (mm)",
        )

    if summary.rejected:
        with st.expander(f"Rejected rows ({len(summary.rejected)})", expanded=not summary.rows):
            for r in summary.rejected:
                reasons = ", ".join(f for f in r.flags if f != "no_image_path") or "—"
                st.write(f"**{r.measurement_id}** — {reasons}")

    with st.expander("validation_summary.md preview"):
        st.markdown(to_markdown_table(summary))


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
