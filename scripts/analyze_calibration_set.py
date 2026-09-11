"""Non-destructive calibration-image analysis and calibration-set search.

This tool never edits, moves, resizes, or rewrites any photograph. It only *reads*
`data/calibration_images/` and `data/calibration_rejected/`, runs the **same production
corner detector** used by `module2.calibration`, and writes analysis artefacts under
`results/`.

Sub-commands
------------
``inventory``
    Scan every image in both folders. For each image record EXIF (camera / lens / focal
    length / aperture / ISO / shutter / orientation), the pixel size produced by the
    production loader, whether the full 9x6 inner-corner grid is detected, sharpness
    (variance of the Laplacian), board coverage of the frame, board centre in normalised
    image coordinates, and a `cv2.solvePnP` pose estimate (out-of-plane tilt, in-plane
    roll, yaw, pitch, distance). Writes `results/calibration_inventory.json` and
    `results/calibration_inventory.md`. Detected corners are cached (keyed by path + mtime)
    so later calibration experiments do not re-run the slow full-resolution detector.

``calibrate --set NAME --images "IMG_a IMG_b ..."``
    Run `cv2.calibrateCamera` on an explicit list of images (looked up in either folder),
    using cached corners. Reports RMS, per-view errors, K, fx/fy, cx/cy, distortion, and
    the implied field of view. Appends the result to `results/calibration_candidates.json`.
    Does **not** write `data/calibration.json` (that is what `scripts/run_calibration.py`
    does on the finally-chosen folder contents).

``loo --images "IMG_a IMG_b ..."``
    Leave-one-out stability check on a set: recalibrate with each image removed in turn and
    report the fx / fy / cx / cy / k1 / k2 / k3 / RMS ranges.

``holdout --train "..." --test "..."``
    Calibrate on the train set, then report reprojection error of the calibrated model on
    the held-out test views (pose solved per test view with `cv2.solvePnP`; intrinsics and
    distortion are *not* refit).

All numbers come from the real photographs. Nothing here fabricates calibration output.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from PIL.ExifTags import TAGS  # noqa: E402

from module2.calibration import (  # noqa: E402
    chessboard_object_points,
    compute_reprojection_error,
    find_chessboard_corners,
    parse_pattern_size,
)
from module2.io_utils import load_image_gray  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
IMAGES_DIR = REPO_ROOT / "data" / "calibration_images"
REJECTED_DIR = REPO_ROOT / "data" / "calibration_rejected"
RESULTS_DIR = REPO_ROOT / "results"
CACHE_PATH = RESULTS_DIR / "corner_cache.npz"  # git-ignored via results/*_cache*; kept local

PATTERN_SIZE = (9, 6)
SQUARE_MM = 25.0

# EXIF-derived provisional intrinsics for pose diagnostics ONLY (never written to
# calibration output). iPhone 15 Pro Max main camera: 35 mm-equivalent focal length 24 mm,
# sensor long axis 5712 px. fx_guess = 24 / 36 * 5712 ~= 3808 px (square pixels -> fy == fx).
_PROV_F_PX = 24.0 / 36.0 * 5712.0
_SENSOR_DIAG_MM = math.hypot(9.817, 7.36)  # 1/1.28" sensor, ~ iPhone 15 Pro Max main


def _batch_of(name: str) -> str:
    """Classify a filename into the OLD or NEW-RETAKE capture batch by IMG number."""
    stem = Path(name).stem.upper()
    if stem.startswith("IMG_"):
        try:
            n = int(stem.split("_")[1])
        except (IndexError, ValueError):
            return "UNKNOWN"
        if 7039 <= n <= 7060:
            return "NEW"
        if 6970 <= n <= 6994:
            return "OLD"
        if 6880 <= n <= 6905:
            return "OLD-6880s"
    return "UNKNOWN"


def _exif(path: Path) -> dict:
    """Return a flat dict of the EXIF fields we care about (missing -> None)."""
    out: dict[str, object] = {
        "pil_width": None,
        "pil_height": None,
        "orientation": None,
        "camera_model": None,
        "lens_model": None,
        "focal_length_mm": None,
        "focal_length_35mm": None,
        "f_number": None,
        "iso": None,
        "exposure_time_s": None,
        "datetime_original": None,
    }
    try:
        im = Image.open(path)
    except OSError:
        return out
    out["pil_width"], out["pil_height"] = im.size
    base = im.getexif()
    tag = {TAGS.get(k, k): v for k, v in base.items()}
    try:
        sub = {TAGS.get(k, k): v for k, v in base.get_ifd(0x8769).items()}
    except (KeyError, AttributeError):
        sub = {}

    def _f(x: object) -> float | None:
        try:
            return float(x)  # PIL IFDRational -> float
        except (TypeError, ValueError):
            return None

    out["orientation"] = tag.get("Orientation")
    out["camera_model"] = str(tag.get("Model")) if tag.get("Model") else None
    out["lens_model"] = str(sub.get("LensModel")) if sub.get("LensModel") else None
    out["focal_length_mm"] = _f(sub.get("FocalLength", tag.get("FocalLength")))
    out["focal_length_35mm"] = _f(
        sub.get("FocalLengthIn35mmFilm", tag.get("FocalLengthIn35mmFilm"))
    )
    out["f_number"] = _f(sub.get("FNumber"))
    iso = sub.get("ISOSpeedRatings") or sub.get("PhotographicSensitivity")
    out["iso"] = int(iso) if isinstance(iso, (int, float)) else None
    out["exposure_time_s"] = _f(sub.get("ExposureTime"))
    out["datetime_original"] = (
        str(sub.get("DateTimeOriginal")) if sub.get("DateTimeOriginal") else None
    )
    return out


@dataclass
class ImageRecord:
    name: str
    folder: str  # "calibration_images" | "calibration_rejected"
    batch: str
    cv_width: int | None = None
    cv_height: int | None = None
    exif: dict = field(default_factory=dict)
    detected: bool = False
    n_corners: int = 0
    sharpness_board: float | None = None  # var(Laplacian) over board bbox
    sharpness_global: float | None = None
    coverage_frac: float | None = None  # board polygon area / image area
    center_norm: list[float] | None = None  # [cx/W, cy/H]
    bbox_norm: list[float] | None = None  # [x0,y0,x1,y1] / (W or H)
    min_edge_margin_px: float | None = None  # nearest board-corner distance to any border
    min_spacing_px: float | None = None  # smallest neighbour spacing (distance proxy)
    glare_frac: float | None = None  # fraction >250 within board bbox
    pose_ok: bool = False
    tilt_deg: float | None = None  # angle(board normal, optical axis) -> out-of-plane
    roll_deg: float | None = None  # in-plane rotation about optical axis (does NOT help fx)
    yaw_deg: float | None = None
    pitch_deg: float | None = None
    distance_mm: float | None = None
    reproj_rms_prov_px: float | None = None  # with provisional K, diagnostic only
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------- corners cache


def _cache_load() -> dict:
    if not CACHE_PATH.is_file():
        return {}
    raw = np.load(CACHE_PATH, allow_pickle=True)
    return {k: raw[k] for k in raw.files}


def _cache_key(path: Path) -> str:
    return f"{path.name}|{int(path.stat().st_mtime)}"


def detect_corners_cached(path: Path, cache: dict) -> np.ndarray | None:
    """Return refined (N,2) corners via the production detector, memoised on disk."""
    key = _cache_key(path)
    if key in cache:
        arr = cache[key]
        return None if arr.size == 0 else arr.astype(np.float32)
    gray = load_image_gray(path)
    corners = find_chessboard_corners(gray, PATTERN_SIZE)
    cache[key] = np.empty((0, 2), np.float32) if corners is None else corners
    return corners


def _cache_save(cache: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE_PATH, **cache)


# ------------------------------------------------------------------------------- geometry


def _prov_K(w: int, h: int) -> np.ndarray:
    return np.array(
        [[_PROV_F_PX, 0.0, w / 2.0], [0.0, _PROV_F_PX, h / 2.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )


def _pose_descriptors(rvec: np.ndarray) -> tuple[float, float, float, float]:
    """(tilt, roll, yaw, pitch) in degrees from a board->camera rotation vector.

    tilt  = angle between the board-plane normal and the optical axis (0 = fronto-parallel,
            the pose that does NOT constrain focal length).
    roll  = rotation about the optical axis (in-plane; also does not constrain focal length).
    yaw/pitch = rotation about the camera Y / X axes.
    """
    R, _ = cv2.Rodrigues(rvec)
    normal_cam = R[:, 2]  # board +Z axis expressed in the camera frame
    cos_tilt = min(1.0, abs(float(normal_cam[2])))
    tilt = math.degrees(math.acos(cos_tilt))
    roll = math.degrees(math.atan2(float(R[1, 0]), float(R[0, 0])))
    yaw = math.degrees(math.atan2(float(-R[2, 0]), math.hypot(R[2, 1], R[2, 2])))
    pitch = math.degrees(math.atan2(float(R[2, 1]), float(R[2, 2])))
    return tilt, roll, yaw, pitch


def analyse_image(path: Path, folder: str, cache: dict) -> ImageRecord:
    rec = ImageRecord(name=path.name, folder=folder, batch=_batch_of(path.name))
    rec.exif = _exif(path)
    gray = load_image_gray(path)
    h, w = gray.shape
    rec.cv_height, rec.cv_width = int(h), int(w)

    corners = detect_corners_cached(path, cache)
    rec.sharpness_global = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if corners is None:
        rec.detected = False
        rec.notes.append("chessboard not detected by production detector")
        return rec

    rec.detected = True
    rec.n_corners = int(corners.shape[0])
    cols, rows = PATTERN_SIZE

    x0, y0 = float(corners[:, 0].min()), float(corners[:, 1].min())
    x1, y1 = float(corners[:, 0].max()), float(corners[:, 1].max())
    rec.bbox_norm = [x0 / w, y0 / h, x1 / w, y1 / h]
    rec.center_norm = [float(corners[:, 0].mean()) / w, float(corners[:, 1].mean()) / h]
    rec.min_edge_margin_px = float(
        min(x0, y0, w - x1, h - y1)
    )

    # board polygon = the four outer inner-corners, in grid order
    poly = corners.reshape(rows, cols, 2)
    quad = np.array(
        [poly[0, 0], poly[0, -1], poly[-1, -1], poly[-1, 0]], dtype=np.float32
    )
    rec.coverage_frac = float(cv2.contourArea(quad) / (w * h))

    # neighbour spacing (distance / board-size proxy): min over horizontal neighbours
    horiz = np.linalg.norm(np.diff(poly, axis=1), axis=2)
    rec.min_spacing_px = float(horiz.min())

    ix0, iy0 = max(0, int(x0)), max(0, int(y0))
    ix1, iy1 = min(w, int(x1) + 1), min(h, int(y1) + 1)
    board = gray[iy0:iy1, ix0:ix1]
    if board.size:
        rec.sharpness_board = float(cv2.Laplacian(board, cv2.CV_64F).var())
        rec.glare_frac = float((board > 250).mean())

    objp = chessboard_object_points(PATTERN_SIZE, SQUARE_MM)
    K = _prov_K(w, h)
    ok, rvec, tvec = cv2.solvePnP(
        objp.reshape(-1, 1, 3),
        corners.reshape(-1, 1, 2).astype(np.float32),
        K,
        None,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    rec.pose_ok = bool(ok)
    if ok:
        tilt, roll, yaw, pitch = _pose_descriptors(rvec)
        rec.tilt_deg, rec.roll_deg, rec.yaw_deg, rec.pitch_deg = (
            round(tilt, 2),
            round(roll, 2),
            round(yaw, 2),
            round(pitch, 2),
        )
        rec.distance_mm = round(float(np.asarray(tvec).ravel()[2]), 1)
        overall, _ = compute_reprojection_error(
            [objp.reshape(-1, 1, 3)],
            [corners.reshape(-1, 1, 2).astype(np.float32)],
            [rvec],
            [tvec],
            K,
            np.zeros(5),
        )
        rec.reproj_rms_prov_px = round(overall, 3)
        if tilt < 8.0:
            rec.notes.append(f"near fronto-parallel (tilt {tilt:.1f} deg) — weak for fx/fy")
    return rec


# ------------------------------------------------------------------------- calibration ops


def _collect(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)


def _resolve(names: list[str]) -> list[Path]:
    """Map bare IMG names (with or without extension) to a real file in either folder."""
    pool = {p.name: p for p in _collect(IMAGES_DIR)}
    for p in _collect(REJECTED_DIR):
        pool.setdefault(p.name, p)
    resolved: list[Path] = []
    for n in names:
        cand = [k for k in pool if k == n or Path(k).stem == Path(n).stem]
        if not cand:
            raise SystemExit(f"image not found in either folder: {n!r}")
        resolved.append(pool[cand[0]])
    return resolved


def _fov_deg(f_px: float, size_px: int) -> float:
    return math.degrees(2.0 * math.atan(size_px / (2.0 * f_px)))


def calibrate_set(names: list[str], cache: dict) -> dict:
    paths = _resolve(names)
    objp = chessboard_object_points(PATTERN_SIZE, SQUARE_MM)
    obj_pts, img_pts, used, failed = [], [], [], []
    size = None
    for p in paths:
        gray_shape = load_image_gray(p).shape
        s = (int(gray_shape[1]), int(gray_shape[0]))
        size = size or s
        if s != size:
            raise SystemExit(f"{p.name}: size {s} != {size}; mixed resolution")
        c = detect_corners_cached(p, cache)
        if c is None:
            failed.append(p.name)
            continue
        obj_pts.append(objp.reshape(-1, 1, 3).copy())
        img_pts.append(c.reshape(-1, 1, 2).astype(np.float32))
        used.append(p.name)
    if len(used) < 3:
        raise SystemExit(f"only {len(used)} detected views; need >= 3")
    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(obj_pts, img_pts, size, None, None)
    _, per_view = compute_reprojection_error(obj_pts, img_pts, rvecs, tvecs, K, dist)
    K = np.asarray(K, float)
    dist = np.asarray(dist, float).ravel()
    w, h = size
    return {
        "set_images": [p.name for p in paths],
        "used_images": used,
        "failed_images": failed,
        "num_used": len(used),
        "image_size": [w, h],
        "rms_reprojection_error": float(rms),
        "per_view_errors": [float(e) for e in per_view],
        "per_view_min": float(min(per_view)),
        "per_view_mean": float(sum(per_view) / len(per_view)),
        "per_view_max": float(max(per_view)),
        "K": K.tolist(),
        "fx": float(K[0, 0]),
        "fy": float(K[1, 1]),
        "cx": float(K[0, 2]),
        "cy": float(K[1, 2]),
        "dist_coeffs": dist.tolist(),
        "fov_h_deg": _fov_deg(float(K[0, 0]), w),
        "fov_v_deg": _fov_deg(float(K[1, 1]), h),
        "worst_view": used[int(np.argmax(per_view))],
    }


def leave_one_out(names: list[str], cache: dict) -> dict:
    base = calibrate_set(names, cache)
    used = base["used_images"]
    rows = []
    for drop in used:
        keep = [n for n in used if n != drop]
        r = calibrate_set(keep, cache)
        rows.append(
            {
                "dropped": drop,
                "num_used": r["num_used"],
                "rms": r["rms_reprojection_error"],
                "fx": r["fx"],
                "fy": r["fy"],
                "cx": r["cx"],
                "cy": r["cy"],
                "k1": r["dist_coeffs"][0],
                "k2": r["dist_coeffs"][1],
                "k3": r["dist_coeffs"][4] if len(r["dist_coeffs"]) > 4 else float("nan"),
            }
        )

    def _rng(key: str) -> list[float]:
        vals = [row[key] for row in rows]
        return [min(vals), max(vals), max(vals) - min(vals)]

    return {
        "base": base,
        "loo_rows": rows,
        "ranges": {k: _rng(k) for k in ["rms", "fx", "fy", "cx", "cy", "k1", "k2", "k3"]},
    }


def holdout(train: list[str], test: list[str], cache: dict) -> dict:
    fit = calibrate_set(train, cache)
    K = np.asarray(fit["K"], float)
    dist = np.asarray(fit["dist_coeffs"], float)
    objp = chessboard_object_points(PATTERN_SIZE, SQUARE_MM)
    rows = []
    for p in _resolve(test):
        c = detect_corners_cached(p, cache)
        if c is None:
            rows.append({"image": p.name, "detected": False})
            continue
        ok, rvec, tvec = cv2.solvePnP(
            objp.reshape(-1, 1, 3), c.reshape(-1, 1, 2).astype(np.float32), K, dist
        )
        overall, _ = compute_reprojection_error(
            [objp.reshape(-1, 1, 3)],
            [c.reshape(-1, 1, 2).astype(np.float32)],
            [rvec],
            [tvec],
            K,
            dist,
        )
        rows.append({"image": p.name, "detected": True, "reproj_rms_px": float(overall)})
    errs = [r["reproj_rms_px"] for r in rows if r.get("detected")]
    return {
        "train_summary": {k: fit[k] for k in ("num_used", "rms_reprojection_error", "fx", "fy", "cx", "cy", "dist_coeffs")},
        "holdout_rows": rows,
        "holdout_rms_mean": float(np.mean(errs)) if errs else None,
        "holdout_rms_max": float(np.max(errs)) if errs else None,
    }


# ----------------------------------------------------------------------------- reporting


def _inventory_md(records: list[ImageRecord]) -> str:
    lines = [
        "# Calibration image inventory (auto-generated)",
        "",
        f"*Generated by `scripts/analyze_calibration_set.py inventory` on "
        f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}. Read-only scan; no image "
        f"was modified.*",
        "",
        "`tilt` = angle between the board-plane normal and the optical axis "
        "(0 deg = fronto-parallel, which does **not** constrain focal length). "
        "`roll` = in-plane rotation about the optical axis (also does not help fx/fy). "
        "`cov` = board-polygon area / frame area. `centre` = board centroid in normalised "
        "(x, y). Pose from `cv2.solvePnP` with a provisional EXIF-based K "
        f"(f = {_PROV_F_PX:.0f} px) — diagnostic only.",
        "",
        "| image | batch | folder | det | corners | sharp(board) | cov | centre | "
        "tilt deg | roll deg | dist mm | prov RMS px | notes |",
        "| ----- | ----- | ------ | --- | ------- | ------------ | --- | ------ | "
        "-------- | -------- | ------- | ----------- | ----- |",
    ]
    for r in records:
        centre = (
            f"({r.center_norm[0]:.2f},{r.center_norm[1]:.2f})" if r.center_norm else "-"
        )
        lines.append(
            "| {name} | {batch} | {folder} | {det} | {nc} | {sb} | {cov} | {centre} | "
            "{tilt} | {roll} | {dist} | {prms} | {notes} |".format(
                name=r.name,
                batch=r.batch,
                folder="images" if r.folder == "calibration_images" else "rejected",
                det="Y" if r.detected else "N",
                nc=r.n_corners or "-",
                sb=f"{r.sharpness_board:.0f}" if r.sharpness_board is not None else "-",
                cov=f"{r.coverage_frac:.3f}" if r.coverage_frac is not None else "-",
                centre=centre,
                tilt=f"{r.tilt_deg:.1f}" if r.tilt_deg is not None else "-",
                roll=f"{r.roll_deg:.1f}" if r.roll_deg is not None else "-",
                dist=f"{r.distance_mm:.0f}" if r.distance_mm is not None else "-",
                prms=f"{r.reproj_rms_prov_px:.2f}"
                if r.reproj_rms_prov_px is not None
                else "-",
                notes="; ".join(r.notes) if r.notes else "",
            )
        )
    return "\n".join(lines) + "\n"


def cmd_inventory(args: argparse.Namespace) -> int:
    cache = _cache_load()
    records: list[ImageRecord] = []
    for folder, path in (
        ("calibration_images", IMAGES_DIR),
        ("calibration_rejected", REJECTED_DIR),
    ):
        for img in _collect(path):
            print(f"  analysing {folder}/{img.name} ...", flush=True)
            records.append(analyse_image(img, folder, cache))
    _cache_save(cache)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "calibration_inventory.json").write_text(
        json.dumps([asdict(r) for r in records], indent=2) + "\n"
    )
    (RESULTS_DIR / "calibration_inventory.md").write_text(_inventory_md(records))

    det = [r for r in records if r.detected]
    print(f"\n{len(records)} images, {len(det)} with a detected 9x6 grid")
    print(f"wrote {RESULTS_DIR / 'calibration_inventory.json'}")
    print(f"wrote {RESULTS_DIR / 'calibration_inventory.md'}")
    return 0


def _append_candidate(entry: dict) -> None:
    path = RESULTS_DIR / "calibration_candidates.json"
    data = json.loads(path.read_text()) if path.is_file() else []
    data.append(entry)
    path.write_text(json.dumps(data, indent=2) + "\n")


def cmd_calibrate(args: argparse.Namespace) -> int:
    cache = _cache_load()
    names = args.images.split()
    res = calibrate_set(names, cache)
    _cache_save(cache)
    res = {"set_name": args.set, "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **res}
    _append_candidate(res)
    print(json.dumps(res, indent=2))
    print(
        f"\n[{args.set}] n={res['num_used']}  RMS={res['rms_reprojection_error']:.4f}px  "
        f"fx={res['fx']:.1f} fy={res['fy']:.1f}  cx={res['cx']:.1f} cy={res['cy']:.1f}  "
        f"FoV={res['fov_h_deg']:.1f}x{res['fov_v_deg']:.1f} deg"
    )
    print(f"  dist = {['%.4f' % c for c in res['dist_coeffs']]}")
    print(f"  per-view min/mean/max = {res['per_view_min']:.3f}/{res['per_view_mean']:.3f}/{res['per_view_max']:.3f}")
    return 0


def cmd_loo(args: argparse.Namespace) -> int:
    cache = _cache_load()
    res = leave_one_out(args.images.split(), cache)
    _cache_save(cache)
    (RESULTS_DIR / "calibration_loo.json").write_text(json.dumps(res, indent=2) + "\n")
    b = res["base"]
    print(
        f"base: n={b['num_used']} RMS={b['rms_reprojection_error']:.4f} "
        f"fx={b['fx']:.1f} fy={b['fy']:.1f} cx={b['cx']:.1f} cy={b['cy']:.1f}"
    )
    print("\ndropped            RMS     fx       fy       cx       cy       k1      k2      k3")
    for row in res["loo_rows"]:
        print(
            f"{row['dropped']:<16} {row['rms']:6.4f} {row['fx']:8.1f} {row['fy']:8.1f} "
            f"{row['cx']:8.1f} {row['cy']:8.1f} {row['k1']:7.3f} {row['k2']:7.3f} {row['k3']:7.3f}"
        )
    print("\nranges [min, max, span]:")
    for k, v in res["ranges"].items():
        print(f"  {k:3} : [{v[0]:.4f}, {v[1]:.4f}]  span {v[2]:.4f}")
    print(f"\nwrote {RESULTS_DIR / 'calibration_loo.json'}")
    return 0


def cmd_holdout(args: argparse.Namespace) -> int:
    cache = _cache_load()
    res = holdout(args.train.split(), args.test.split(), cache)
    _cache_save(cache)
    (RESULTS_DIR / "calibration_holdout.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inventory", help="scan both folders and write the inventory")

    c = sub.add_parser("calibrate", help="calibrate one explicit image set")
    c.add_argument("--set", required=True, help="label for this candidate set")
    c.add_argument("--images", required=True, help="space-separated IMG names")

    lo = sub.add_parser("loo", help="leave-one-out stability check on a set")
    lo.add_argument("--images", required=True, help="space-separated IMG names")

    ho = sub.add_parser("holdout", help="train/test split reprojection check")
    ho.add_argument("--train", required=True)
    ho.add_argument("--test", required=True)

    args = ap.parse_args(argv)
    return {
        "inventory": cmd_inventory,
        "calibrate": cmd_calibrate,
        "loo": cmd_loo,
        "holdout": cmd_holdout,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
