"""CLI: estimate an object's real-world width and height from user pixel points.

Run from the repository root (or the ``Assignments/`` workspace root with ``Module_2/``
prefixes)::

    python scripts/estimate_dimensions.py \\
        --image data/experiments/img_01.jpg \\
        --calibration data/calibration.json \\
        --distance-m 2.6 \\
        --width-points "812,540 1244,548" \\
        --height-points "1020,300 1030,790"

Points are the raw-image pixel coordinates of the two endpoints spanning the object's
width and the two spanning its height. **No automatic object detection** — the points are
supplied by the user (see ``docs/assumptions.md``).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SRC = REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from module2.calibration import load_calibration  # noqa: E402
from module2.dimension_estimation import estimate_width_height  # noqa: E402
from module2.io_utils import load_image_bgr  # noqa: E402
from module2.units import metres_to_mm  # noqa: E402

Point = tuple[float, float]


def _parse_pair(spec: str) -> tuple[Point, Point]:
    """Parse ``"x1,y1 x2,y2"`` into two ``(x, y)`` points."""
    try:
        a, b = spec.split()
        (x1, y1), (x2, y2) = (a.split(",")), (b.split(","))
        return (float(x1), float(y1)), (float(x2), float(y2))
    except ValueError as exc:
        raise SystemExit(
            f"could not parse point pair {spec!r}; expected 'x1,y1 x2,y2'"
        ) from exc


def _check_in_bounds(name: str, pts: tuple[Point, Point], width: int, height: int) -> None:
    for x, y in pts:
        if not (0 <= x < width and 0 <= y < height):
            raise SystemExit(
                f"{name} point ({x}, {y}) is outside the image ({width}x{height})"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Estimate real-world object width and height from pixel points."
    )
    parser.add_argument("--image", type=Path, required=True, help="raw image the points were read from")
    parser.add_argument(
        "--calibration",
        type=Path,
        default=REPO_ROOT / "data" / "calibration.json",
        help="calibration JSON (default: data/calibration.json)",
    )
    parser.add_argument(
        "--distance-m",
        type=float,
        required=True,
        help="object-plane depth Z along the optical axis, in metres",
    )
    parser.add_argument(
        "--width-points", required=True, help='width endpoints: "x1,y1 x2,y2"'
    )
    parser.add_argument(
        "--height-points", required=True, help='height endpoints: "x1,y1 x2,y2"'
    )
    args = parser.parse_args(argv)

    if args.distance_m <= 0:
        raise SystemExit("--distance-m must be positive")
    if not args.calibration.is_file():
        raise SystemExit(
            f"calibration file not found: {args.calibration}\n"
            "Run scripts/run_calibration.py first (see docs/calibration_method.md)."
        )

    calib = load_calibration(args.calibration)
    image = load_image_bgr(args.image)
    height, width = image.shape[:2]

    width_pts = _parse_pair(args.width_points)
    height_pts = _parse_pair(args.height_points)
    _check_in_bounds("width", width_pts, width, height)
    _check_in_bounds("height", height_pts, width, height)

    z_mm = metres_to_mm(args.distance_m)
    dims = estimate_width_height(
        width_pts, height_pts, calib.camera_matrix, calib.dist_coeffs, z_mm
    )

    if args.distance_m <= 2.0:
        print(
            "note: distance <= 2 m. Step 3 validation requires the object-plane depth to "
            "exceed 2 m."
        )
    print(f"image:        {args.image}  ({width}x{height} px)")
    print(f"calibration:  {args.calibration}")
    print(f"distance Z:   {args.distance_m:.3f} m  ({z_mm:.1f} mm)")
    print(f"width:        {dims['width_mm']:.2f} mm  ({dims['width_mm'] / 10:.2f} cm)")
    print(f"height:       {dims['height_mm']:.2f} mm  ({dims['height_mm'] / 10:.2f} cm)")
    print("assumptions:  see docs/assumptions.md (pinhole model, fronto-parallel plane, "
          "Z along the optical axis, same camera config as calibration).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
