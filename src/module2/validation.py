"""20-trial experimental validation: measurement CSV -> per-row errors + summary tables.

Column definitions, units and the acceptance rules are documented canonically in
``docs/validation_protocol.md``. In brief, a row is **rejected** (excluded from the
aggregate statistics, listed separately) when:

* ``object_plane_depth_z_m`` is not a finite number greater than 2.0;
* ``actual_width_mm`` or ``actual_height_mm`` is not a finite number greater than 0;
* any of the eight pixel coordinates is missing or non-numeric.

A missing ``image_path`` is flagged (``no_image_path``) but does not block the estimate:
the estimate needs only the points, the depth, and the calibration.
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from module2.calibration import CalibrationResult
from module2.dimension_estimation import Point, estimate_width_height
from module2.metrics import ErrorStatistics, compute_error_statistics
from module2.units import metres_to_mm

#: Minimum permitted object-plane depth, in metres (assignment requirement).
MIN_OBJECT_PLANE_DEPTH_M: float = 2.0

#: Fields the user fills in.
INPUT_COLUMNS: tuple[str, ...] = (
    "measurement_id",
    "object_name",
    "object_plane_depth_z_m",
    "image_path",
    "w_p1_x", "w_p1_y", "w_p2_x", "w_p2_y",
    "h_p1_x", "h_p1_y", "h_p2_x", "h_p2_y",
    "actual_width_mm", "actual_height_mm",
)

#: Fields ``analyze_validation`` computes and overwrites.
COMPUTED_COLUMNS: tuple[str, ...] = (
    "estimated_width_mm", "estimated_height_mm",
    "width_signed_error_mm", "width_absolute_error_mm", "width_percentage_error",
    "height_signed_error_mm", "height_absolute_error_mm", "height_percentage_error",
)

#: Full template header (user columns then computed columns).
TEMPLATE_COLUMNS: tuple[str, ...] = INPUT_COLUMNS + COMPUTED_COLUMNS


@dataclass
class MeasurementRow:
    """One row of the validation template: user-entered fields plus computed estimates.

    ``source`` is the row's raw string cells exactly as read from the CSV (nothing parsed or
    normalised); ``index`` is its 0-based position in the input file. Both are used to write
    the filled CSV back in the original order without rewriting any user-entered value.
    """

    measurement_id: str
    object_name: str
    object_plane_depth_z_m: float
    image_path: str
    width_points: tuple[Point, Point]
    height_points: tuple[Point, Point]
    actual_width_mm: float
    actual_height_mm: float
    estimated_width_mm: float | None = None
    estimated_height_mm: float | None = None
    flags: list[str] = field(default_factory=list)
    index: int = -1
    source: dict[str, str] = field(default_factory=dict)


@dataclass
class ValidationSummary:
    """Full validation outcome: accepted rows plus width/height/combined statistics.

    ``width_stats`` / ``height_stats`` / ``combined_stats`` are ``None`` when no row was
    accepted (e.g. the template is still empty).
    """

    rows: list[MeasurementRow]
    width_stats: ErrorStatistics | None
    height_stats: ErrorStatistics | None
    combined_stats: ErrorStatistics | None
    rejected: list[MeasurementRow] = field(default_factory=list)


def _num(raw: dict[str, str], column: str, flags: list[str]) -> float:
    value = (raw.get(column) or "").strip()
    if value == "":
        flags.append(f"missing:{column}")
        return math.nan
    try:
        return float(value)
    except ValueError:
        flags.append(f"invalid:{column}")
        return math.nan


def parse_measurements(dict_rows: Iterable[dict[str, str]]) -> list[MeasurementRow]:
    """Parse CSV ``DictReader`` rows into :class:`MeasurementRow` objects (no computation)."""
    out: list[MeasurementRow] = []
    for i, raw in enumerate(dict_rows):
        flags: list[str] = []
        image_path = (raw.get("image_path") or "").strip()
        if not image_path:
            flags.append("no_image_path")
        source = {c: ("" if raw.get(c) is None else raw[c]) for c in TEMPLATE_COLUMNS}
        row = MeasurementRow(
            measurement_id=(raw.get("measurement_id") or "").strip() or f"row{i + 1}",
            object_name=(raw.get("object_name") or "").strip(),
            object_plane_depth_z_m=_num(raw, "object_plane_depth_z_m", flags),
            image_path=image_path,
            width_points=(
                (_num(raw, "w_p1_x", flags), _num(raw, "w_p1_y", flags)),
                (_num(raw, "w_p2_x", flags), _num(raw, "w_p2_y", flags)),
            ),
            height_points=(
                (_num(raw, "h_p1_x", flags), _num(raw, "h_p1_y", flags)),
                (_num(raw, "h_p2_x", flags), _num(raw, "h_p2_y", flags)),
            ),
            actual_width_mm=_num(raw, "actual_width_mm", flags),
            actual_height_mm=_num(raw, "actual_height_mm", flags),
            flags=flags,
            index=i,
            source=source,
        )
        out.append(row)
    return out


def parse_measurements_text(text: str) -> list[MeasurementRow]:
    """Parse CSV text. Raises ``ValueError`` if the header lacks a required column."""
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    missing = [c for c in INPUT_COLUMNS if c not in header]
    if missing:
        raise ValueError(
            f"measurement CSV is missing required column(s): {', '.join(missing)}"
        )
    return parse_measurements(list(reader))


def load_measurements(csv_path: str | Path) -> list[MeasurementRow]:
    """Read the measurement CSV from disk (see :func:`parse_measurements_text`)."""
    return parse_measurements_text(Path(csv_path).read_text(encoding="utf-8"))


_BLOCKING_PREFIXES = (
    "missing:", "invalid:", "z_not_above_",
    "actual_width_not_positive", "actual_height_not_positive", "missing_points",
)


def _is_blocking(flags: list[str]) -> bool:
    return any(f.startswith(_BLOCKING_PREFIXES) for f in flags)


def compute_errors(
    rows: list[MeasurementRow], calibration: CalibrationResult
) -> ValidationSummary:
    """Estimate dimensions per row, apply the acceptance gates, and aggregate statistics."""
    K = calibration.camera_matrix
    dist = calibration.dist_coeffs
    accepted: list[MeasurementRow] = []
    rejected: list[MeasurementRow] = []

    for row in rows:
        flags = list(row.flags)
        z = row.object_plane_depth_z_m
        if not math.isfinite(z) or z <= MIN_OBJECT_PLANE_DEPTH_M:
            flags.append(f"z_not_above_{MIN_OBJECT_PLANE_DEPTH_M:g}m")
        if not math.isfinite(row.actual_width_mm) or row.actual_width_mm <= 0.0:
            flags.append("actual_width_not_positive")
        if not math.isfinite(row.actual_height_mm) or row.actual_height_mm <= 0.0:
            flags.append("actual_height_not_positive")
        coords = (
            *row.width_points[0], *row.width_points[1],
            *row.height_points[0], *row.height_points[1],
        )
        if not all(math.isfinite(c) for c in coords):
            flags.append("missing_points")

        row.flags = flags
        if _is_blocking(flags):
            rejected.append(row)
            continue

        dims = estimate_width_height(
            row.width_points, row.height_points, K, dist, metres_to_mm(z)
        )
        row.estimated_width_mm = dims["width_mm"]
        row.estimated_height_mm = dims["height_mm"]
        accepted.append(row)

    if accepted:
        aw = [r.actual_width_mm for r in accepted]
        ew = [r.estimated_width_mm for r in accepted]
        ah = [r.actual_height_mm for r in accepted]
        eh = [r.estimated_height_mm for r in accepted]
        width_stats = compute_error_statistics(aw, ew)
        height_stats = compute_error_statistics(ah, eh)
        combined_stats = compute_error_statistics(aw + ah, ew + eh)
    else:
        width_stats = height_stats = combined_stats = None

    return ValidationSummary(
        rows=accepted,
        width_stats=width_stats,
        height_stats=height_stats,
        combined_stats=combined_stats,
        rejected=rejected,
    )


def row_error_columns(row: MeasurementRow) -> dict[str, float]:
    """The eight computed columns for an accepted row (estimates must already be filled)."""
    assert row.estimated_width_mm is not None and row.estimated_height_mm is not None
    w_sig = row.estimated_width_mm - row.actual_width_mm
    h_sig = row.estimated_height_mm - row.actual_height_mm
    return {
        "estimated_width_mm": row.estimated_width_mm,
        "estimated_height_mm": row.estimated_height_mm,
        "width_signed_error_mm": w_sig,
        "width_absolute_error_mm": abs(w_sig),
        "width_percentage_error": abs(w_sig) / row.actual_width_mm * 100.0,
        "height_signed_error_mm": h_sig,
        "height_absolute_error_mm": abs(h_sig),
        "height_percentage_error": abs(h_sig) / row.actual_height_mm * 100.0,
    }


def to_filled_csv_text(summary: ValidationSummary) -> str:
    """Serialize the analysed rows back to CSV.

    Guarantees:

    * rows keep their **original input order** (accepted and rejected interleaved as in the
      source file);
    * every user-entered column is copied **verbatim** from the source row — blank stays
      blank, invalid text stays exactly as entered, nothing is normalised to ``nan``;
    * only :data:`COMPUTED_COLUMNS` are written, and only for accepted rows.

    Re-running the analysis on the output therefore produces identical validation behaviour.
    """
    ordered = sorted([*summary.rows, *summary.rejected], key=lambda r: r.index)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(TEMPLATE_COLUMNS))
    writer.writeheader()
    for row in ordered:
        record: dict[str, object] = {c: row.source.get(c, "") for c in TEMPLATE_COLUMNS}
        if row.estimated_width_mm is not None and row.estimated_height_mm is not None:
            for column, value in row_error_columns(row).items():
                record[column] = value
        writer.writerow(record)
    return buffer.getvalue()


def _stats_block(title: str, stats: ErrorStatistics) -> list[str]:
    return [
        f"### {title}",
        "",
        "| statistic | value |",
        "| --------- | ----: |",
        f"| n | {stats.n} |",
        f"| mean error (signed) | {stats.mean_signed_error_mm:.3f} mm |",
        f"| mean absolute error | {stats.mae_mm:.3f} mm |",
        f"| mean percentage error | {stats.mape_pct:.3f} % |",
        f"| standard deviation (signed, n-1) | {stats.sample_std_mm:.3f} mm |",
        f"| minimum error | {stats.min_error_mm:.3f} mm |",
        f"| maximum error | {stats.max_error_mm:.3f} mm |",
        "",
    ]


def to_markdown_table(
    summary: ValidationSummary,
    *,
    figures: Sequence[tuple[str, str]] | None = None,
) -> str:
    """Render a :class:`ValidationSummary` as the Markdown body of ``validation_summary.md``.

    ``figures`` is an optional list of ``(caption, path)`` pairs appended as a *Figures*
    section (``![caption](path)``) when at least one measurement was accepted. ``path`` is
    written verbatim, so the caller is responsible for making it resolve where the Markdown
    is rendered — ``scripts/analyze_validation.py`` passes ``figures/<name>.png`` links that
    ``scripts/build_report.py`` resolves via pandoc ``--resource-path=docs/report``. When
    ``figures`` is omitted (e.g. the Streamlit preview) no image links are emitted.
    """
    lines: list[str] = ["# Experimental validation — results", ""]

    if not summary.rows:
        lines += [
            "**No valid measurements.** Every row was rejected or the template is still "
            "empty. Collect real data per `docs/validation_protocol.md` (object-plane depth "
            "> 2 m, actual width/height > 0, all pixel points filled).",
            "",
        ]
    else:
        lines += [
            f"{len(summary.rows)} accepted measurement(s).",
            "",
            "| id | object | Z (m) | actual W (mm) | est W (mm) | W abs err (mm) | W % | "
            "actual H (mm) | est H (mm) | H abs err (mm) | H % |",
            "| -- | ------ | ----: | -----------: | --------: | -------------: | --: | "
            "-----------: | --------: | -------------: | --: |",
        ]
        for r in summary.rows:
            e = row_error_columns(r)
            lines.append(
                f"| {r.measurement_id} | {r.object_name} | {r.object_plane_depth_z_m:.3f} | "
                f"{r.actual_width_mm:.2f} | {e['estimated_width_mm']:.2f} | "
                f"{e['width_absolute_error_mm']:.2f} | {e['width_percentage_error']:.2f} | "
                f"{r.actual_height_mm:.2f} | {e['estimated_height_mm']:.2f} | "
                f"{e['height_absolute_error_mm']:.2f} | {e['height_percentage_error']:.2f} |"
            )
        lines += ["", "## Error statistics", ""]
        lines += _stats_block("Width", summary.width_stats)  # type: ignore[arg-type]
        lines += _stats_block("Height", summary.height_stats)  # type: ignore[arg-type]
        lines += _stats_block("Combined (width + height)", summary.combined_stats)  # type: ignore[arg-type]

        if figures:
            lines += ["## Figures", ""]
            for caption, path in figures:
                lines += [f"![{caption}]({path})", ""]

    if summary.rejected:
        lines += ["## Rejected rows", "", "| id | reason(s) |", "| -- | --------- |"]
        for r in summary.rejected:
            reasons = ", ".join(f for f in r.flags if f != "no_image_path") or "—"
            lines.append(f"| {r.measurement_id} | {reasons} |")
        lines.append("")

    return "\n".join(lines)
