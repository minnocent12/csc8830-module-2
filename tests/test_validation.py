"""Tests for the 20-trial validation tooling.

Synthetic measurement CSVs are built in-test by projecting known rectangles through a known
camera. Nothing here is committed as data; it is all clearly synthetic.
"""
from __future__ import annotations

import csv
import io

import cv2
import numpy as np
import pytest

from module2.calibration import CalibrationResult
from module2.validation import (
    INPUT_COLUMNS,
    TEMPLATE_COLUMNS,
    compute_errors,
    load_measurements,
    parse_measurements_text,
    to_filled_csv_text,
    to_markdown_table,
)

K = np.array([[900.0, 0.0, 640.0], [0.0, 900.0, 360.0], [0.0, 0.0, 1.0]])
DIST0 = np.zeros(5)


def _calibration() -> CalibrationResult:
    return CalibrationResult(
        camera_matrix=K,
        dist_coeffs=DIST0,
        image_size=(1280, 720),
        pattern_size=(9, 6),
        square_size_mm=25.0,
        rms_reprojection_error=0.2,
    )


def _project(points_cam: list[list[float]]) -> np.ndarray:
    pts, _ = cv2.projectPoints(
        np.asarray(points_cam, np.float64).reshape(-1, 1, 3),
        np.zeros(3),
        np.zeros(3),
        K,
        DIST0,
    )
    return pts.reshape(-1, 2)


def _rectangle_row(
    mid: str,
    w_mm: float,
    h_mm: float,
    z_m: float,
    *,
    actual_w: float | None = None,
    actual_h: float | None = None,
) -> dict[str, object]:
    z = z_m * 1000.0
    tl, tr, bl = [-w_mm / 2, -h_mm / 2, z], [w_mm / 2, -h_mm / 2, z], [-w_mm / 2, h_mm / 2, z]
    px = _project([tl, tr, bl])
    return {
        "measurement_id": mid,
        "object_name": f"obj{mid}",
        "object_plane_depth_z_m": z_m,
        "image_path": f"data/experiments/{mid}.jpg",
        "w_p1_x": px[0, 0], "w_p1_y": px[0, 1], "w_p2_x": px[1, 0], "w_p2_y": px[1, 1],
        "h_p1_x": px[0, 0], "h_p1_y": px[0, 1], "h_p2_x": px[2, 0], "h_p2_y": px[2, 1],
        "actual_width_mm": w_mm if actual_w is None else actual_w,
        "actual_height_mm": h_mm if actual_h is None else actual_h,
    }


def _csv_text(rows: list[dict[str, object]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(TEMPLATE_COLUMNS))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def test_recovers_known_dimensions() -> None:
    rows = parse_measurements_text(
        _csv_text(
            [
                _rectangle_row("1", 200.0, 120.0, 2.5),
                _rectangle_row("2", 300.0, 220.0, 3.0),
                _rectangle_row("3", 150.0, 400.0, 4.0),
            ]
        )
    )
    summary = compute_errors(rows, _calibration())
    assert len(summary.rows) == 3
    assert summary.rejected == []
    assert summary.width_stats.mae_mm < 0.5
    assert summary.height_stats.mae_mm < 0.5
    assert summary.combined_stats.n == 6


def test_row_with_depth_not_above_2m_is_rejected() -> None:
    rows = parse_measurements_text(
        _csv_text([_rectangle_row("ok", 200.0, 120.0, 2.5), _rectangle_row("shallow", 200.0, 120.0, 1.9)])
    )
    summary = compute_errors(rows, _calibration())
    assert [r.measurement_id for r in summary.rows] == ["ok"]
    assert len(summary.rejected) == 1
    assert any("z_not_above" in f for f in summary.rejected[0].flags)


@pytest.mark.parametrize("field", ["actual_width_mm", "actual_height_mm"])
def test_row_with_nonpositive_ground_truth_is_rejected(field: str) -> None:
    row = _rectangle_row("bad", 200.0, 120.0, 2.5)
    row[field] = 0.0
    summary = compute_errors(parse_measurements_text(_csv_text([row])), _calibration())
    assert summary.rows == []
    assert len(summary.rejected) == 1


def test_row_with_missing_points_is_rejected() -> None:
    row = _rectangle_row("bad", 200.0, 120.0, 2.5)
    row["w_p1_x"] = ""  # blank pixel coordinate
    summary = compute_errors(parse_measurements_text(_csv_text([row])), _calibration())
    assert summary.rows == []
    assert any(f.startswith("missing:") for f in summary.rejected[0].flags)


def test_all_blank_rows_give_no_accepted_and_helpful_summary() -> None:
    blank = {c: "" for c in TEMPLATE_COLUMNS}
    summary = compute_errors(
        parse_measurements_text(_csv_text([blank for _ in range(20)])), _calibration()
    )
    assert summary.rows == []
    assert summary.width_stats is None
    md = to_markdown_table(summary)
    assert "No valid measurements" in md


def test_markdown_table_has_statistics_and_rejected_section() -> None:
    rows = parse_measurements_text(
        _csv_text(
            [
                _rectangle_row("1", 200.0, 120.0, 2.5),
                _rectangle_row("2", 250.0, 180.0, 3.2),
                _rectangle_row("bad", 200.0, 120.0, 1.5),
            ]
        )
    )
    md = to_markdown_table(compute_errors(rows, _calibration()))
    assert "mean absolute error" in md
    assert "Combined (width + height)" in md
    assert "## Rejected rows" in md
    assert "| bad |" in md


def test_parse_rejects_bad_schema() -> None:
    text = "measurement_id,object_name\n1,box\n"
    with pytest.raises(ValueError, match="missing required column"):
        parse_measurements_text(text)


def test_load_measurements_from_file(tmp_path) -> None:
    path = tmp_path / "m.csv"
    path.write_text(_csv_text([_rectangle_row(str(i), 200.0, 120.0, 2.5) for i in range(20)]))
    rows = load_measurements(path)
    assert len(rows) == 20


def test_filled_csv_preserves_input_row_order_with_interleaving() -> None:
    rows = [
        _rectangle_row("a-ok", 200.0, 120.0, 2.5),
        _rectangle_row("b-shallow", 200.0, 120.0, 1.5),  # rejected
        _rectangle_row("c-ok", 250.0, 180.0, 3.0),
        _rectangle_row("d-bad-actual", 200.0, 120.0, 2.5, actual_w=0.0),  # rejected
        _rectangle_row("e-ok", 150.0, 400.0, 4.0),
    ]
    summary = compute_errors(parse_measurements_text(_csv_text(rows)), _calibration())
    out_ids = [
        r["measurement_id"] for r in csv.DictReader(io.StringIO(to_filled_csv_text(summary)))
    ]
    assert out_ids == ["a-ok", "b-shallow", "c-ok", "d-bad-actual", "e-ok"]


def test_filled_csv_preserves_raw_source_values_exactly() -> None:
    good = _rectangle_row("good", 200.0, 120.0, 2.5)
    weird = _rectangle_row("weird", 200.0, 120.0, 2.5)
    weird["actual_width_mm"] = "abc"  # invalid text, must survive verbatim
    weird["object_name"] = "  spaced  "  # whitespace, not stripped in output
    weird["w_p1_x"] = ""  # blank stays blank
    blank = {c: "" for c in TEMPLATE_COLUMNS}

    summary = compute_errors(
        parse_measurements_text(_csv_text([good, weird, blank])), _calibration()
    )
    out_rows = list(csv.DictReader(io.StringIO(to_filled_csv_text(summary))))

    w = next(r for r in out_rows if r["measurement_id"] == "weird")
    assert w["actual_width_mm"] == "abc"
    assert w["object_name"] == "  spaced  "
    assert w["w_p1_x"] == ""

    b = out_rows[2]
    assert all(b[c] == "" for c in TEMPLATE_COLUMNS)  # fully blank row round-trips blank
    assert "nan" not in ",".join(b.values()).lower()


def test_filled_csv_only_changes_computed_columns_for_accepted_rows() -> None:
    text = _csv_text([_rectangle_row("acc", 200.0, 120.0, 2.5)])
    in_row = next(csv.DictReader(io.StringIO(text)))
    summary = compute_errors(parse_measurements_text(text), _calibration())
    out_row = next(csv.DictReader(io.StringIO(to_filled_csv_text(summary))))

    for column in INPUT_COLUMNS:
        assert out_row[column] == in_row[column]  # user columns byte-identical
    assert out_row["estimated_width_mm"] not in ("", in_row["estimated_width_mm"])
    assert float(out_row["width_absolute_error_mm"]) >= 0.0


def test_reanalysis_of_filled_csv_is_stable() -> None:
    rows = [
        _rectangle_row("1", 200.0, 120.0, 2.5),
        _rectangle_row("2", 200.0, 120.0, 1.5),  # rejected
        _rectangle_row("3", 250.0, 180.0, 3.0),
    ]
    calibration = _calibration()
    first = compute_errors(parse_measurements_text(_csv_text(rows)), calibration)
    csv_1 = to_filled_csv_text(first)
    second = compute_errors(parse_measurements_text(csv_1), calibration)
    csv_2 = to_filled_csv_text(second)

    assert [r.measurement_id for r in first.rows] == [r.measurement_id for r in second.rows]
    assert [(r.measurement_id, tuple(r.flags)) for r in first.rejected] == [
        (r.measurement_id, tuple(r.flags)) for r in second.rejected
    ]
    assert csv_1 == csv_2  # idempotent — the first pass did not mutate any source value


def test_shipped_template_is_plain_and_empty() -> None:
    from pathlib import Path

    template = Path(__file__).resolve().parents[1] / "results" / "measurements_template.csv"
    lines = template.read_text().splitlines()
    assert lines[0] == ",".join(TEMPLATE_COLUMNS)
    assert len(lines) == 21  # header + 20 rows
    assert all(not ln.lstrip().startswith("#") for ln in lines)
    assert all(set(ln) <= {","} for ln in lines[1:])  # every data row fully blank
