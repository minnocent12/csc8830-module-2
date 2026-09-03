"""20-trial experimental validation: measurement CSV -> per-row errors + summary tables.

Enforced gates (canonical text in ``docs/validation_protocol.md``):

* ``object_plane_depth_z_m`` must be greater than 2.0;
* ``actual_width_mm`` and ``actual_height_mm`` must be greater than 0;
* every pixel-point and ground-truth field must be present.

Rows that fail a gate are flagged and excluded from the aggregate statistics.

Status: stub — implemented in Phase 3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from module2.calibration import CalibrationResult
from module2.dimension_estimation import Point
from module2.metrics import ErrorStatistics

#: Minimum permitted object-plane depth, in metres (assignment requirement).
MIN_OBJECT_PLANE_DEPTH_M: float = 2.0


@dataclass
class MeasurementRow:
    """One row of the validation template: user-entered fields plus computed results."""

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


@dataclass
class ValidationSummary:
    """Full validation outcome: accepted rows plus width/height/combined statistics."""

    rows: list[MeasurementRow]
    width_stats: ErrorStatistics
    height_stats: ErrorStatistics
    combined_stats: ErrorStatistics
    rejected: list[MeasurementRow] = field(default_factory=list)


def load_measurements(csv_path: str | Path) -> list[MeasurementRow]:
    """Parse the measurement CSV into :class:`MeasurementRow` objects (no computation)."""
    raise NotImplementedError("Implemented in Phase 3.")


def compute_errors(
    rows: list[MeasurementRow], calibration: CalibrationResult
) -> ValidationSummary:
    """Estimate dimensions per row, apply the gates, and aggregate the statistics."""
    raise NotImplementedError("Implemented in Phase 3.")


def to_markdown_table(summary: ValidationSummary) -> str:
    """Render a :class:`ValidationSummary` as the Markdown body of ``validation_summary.md``."""
    raise NotImplementedError("Implemented in Phase 3.")
