"""CLI: turn a filled 20-trial measurement CSV into error statistics and plots.

Run from the repository root (or the ``Assignments/`` workspace root with ``Module_2/``
prefixes)::

    python scripts/analyze_validation.py \\
        --measurements results/measurements_template.csv \\
        --calibration data/calibration.json

Writes ``results/validation_summary.md`` (per-row table + width / height / combined
statistics), a filled CSV next to the input, and error plots under
``docs/report/figures/``. Rows that fail the acceptance rules
(``docs/validation_protocol.md``) are listed but excluded from the statistics.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SRC = REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from module2.calibration import load_calibration  # noqa: E402
from module2.validation import (  # noqa: E402
    TEMPLATE_COLUMNS,
    ValidationSummary,
    compute_errors,
    load_measurements,
    row_error_columns,
    to_markdown_table,
)


def _write_filled_csv(summary: ValidationSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TEMPLATE_COLUMNS))
        writer.writeheader()
        for row in [*summary.rows, *summary.rejected]:
            record = {
                "measurement_id": row.measurement_id,
                "object_name": row.object_name,
                "object_plane_depth_z_m": row.object_plane_depth_z_m,
                "image_path": row.image_path,
                "w_p1_x": row.width_points[0][0], "w_p1_y": row.width_points[0][1],
                "w_p2_x": row.width_points[1][0], "w_p2_y": row.width_points[1][1],
                "h_p1_x": row.height_points[0][0], "h_p1_y": row.height_points[0][1],
                "h_p2_x": row.height_points[1][0], "h_p2_y": row.height_points[1][1],
                "actual_width_mm": row.actual_width_mm,
                "actual_height_mm": row.actual_height_mm,
            }
            if row.estimated_width_mm is not None:
                record.update(row_error_columns(row))
            writer.writerow(record)


def _write_plots(summary: ValidationSummary, figures_dir: Path) -> list[Path]:
    if not summary.rows:
        return []
    figures_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    errs = list(summary.combined_stats.absolute_error_mm)  # type: ignore[union-attr]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(errs, bins=min(10, max(3, len(errs))))
    ax.set_xlabel("absolute error (mm)")
    ax.set_ylabel("count")
    ax.set_title("Dimension estimation — combined absolute error")
    fig.tight_layout()
    hist_path = figures_dir / "validation_error_hist.png"
    fig.savefig(hist_path, dpi=120)
    plt.close(fig)
    written.append(hist_path)

    actual, estimated = [], []
    for r in summary.rows:
        e = row_error_columns(r)
        actual += [r.actual_width_mm, r.actual_height_mm]
        estimated += [e["estimated_width_mm"], e["estimated_height_mm"]]
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(actual, estimated, s=25)
    lo, hi = min(actual + estimated), max(actual + estimated)
    ax.plot([lo, hi], [lo, hi], "--", linewidth=1)
    ax.set_xlabel("actual (mm)")
    ax.set_ylabel("estimated (mm)")
    ax.set_title("Estimated vs. actual (width + height)")
    fig.tight_layout()
    scatter_path = figures_dir / "validation_estimated_vs_actual.png"
    fig.savefig(scatter_path, dpi=120)
    plt.close(fig)
    written.append(scatter_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyse a filled 20-trial measurement CSV."
    )
    parser.add_argument(
        "--measurements",
        type=Path,
        default=REPO_ROOT / "results" / "measurements_template.csv",
        help="filled measurement CSV (default: results/measurements_template.csv)",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=REPO_ROOT / "data" / "calibration.json",
        help="calibration JSON (default: data/calibration.json)",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=REPO_ROOT / "results" / "validation_summary.md",
        help="output Markdown summary (default: results/validation_summary.md)",
    )
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=REPO_ROOT / "docs" / "report" / "figures",
        help="directory for error plots (default: docs/report/figures)",
    )
    args = parser.parse_args(argv)

    if not args.calibration.is_file():
        raise SystemExit(
            f"calibration file not found: {args.calibration}\n"
            "Run scripts/run_calibration.py first (see docs/calibration_method.md)."
        )
    if not args.measurements.is_file():
        raise SystemExit(f"measurements file not found: {args.measurements}")

    calibration = load_calibration(args.calibration)
    rows = load_measurements(args.measurements)
    summary = compute_errors(rows, calibration)

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(to_markdown_table(summary) + "\n")
    filled_csv = args.measurements.with_name(args.measurements.stem + "_filled.csv")
    _write_filled_csv(summary, filled_csv)
    figures = _write_plots(summary, args.figures_dir)

    print(f"accepted: {len(summary.rows)}   rejected: {len(summary.rejected)}")
    if summary.combined_stats is not None:
        s = summary.combined_stats
        print(
            f"combined  MAE {s.mae_mm:.2f} mm   MAPE {s.mape_pct:.2f} %   "
            f"std(signed, n-1) {s.sample_std_mm:.2f} mm   "
            f"min {s.min_error_mm:.2f}   max {s.max_error_mm:.2f}"
        )
    for r in summary.rejected:
        reasons = ", ".join(f for f in r.flags if f != "no_image_path") or "—"
        print(f"  rejected {r.measurement_id}: {reasons}")
    print(f"wrote {args.summary}")
    print(f"wrote {filled_csv}")
    for fig in figures:
        print(f"wrote {fig}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
