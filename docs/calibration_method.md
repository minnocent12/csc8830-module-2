# Camera calibration — method

> **PENDING USER CALIBRATION RUN — NOT MEASURED.** No calibration has been run yet. The
> numerical results (camera matrix `K`, distortion coefficients, reprojection error) are
> written to `results/calibration_report.md` and `data/calibration.json` by
> `scripts/run_calibration.py` once it is run on real smartphone photographs. Nothing in
> this repository fabricates those values.

## Approach

Standard OpenCV pinhole-model calibration:

1. Print and mount a chessboard and **physically measure** the printed square edge length
   (see `calibration_capture_protocol.md`).
2. Photograph the board in 15–25 poses with the same smartphone, lens, focus, zoom, and
   resolution that will be used for the dimension-estimation experiments.
3. For each image, detect the inner-corner grid with `cv2.findChessboardCorners`
   (`CALIB_CB_ADAPTIVE_THRESH | CALIB_CB_NORMALIZE_IMAGE`) and refine it to sub-pixel
   accuracy with `cv2.cornerSubPix` (11×11 window; 30 iterations / ε = 1e-3).
4. Pair each detected grid with a metric object-point grid (`Z = 0`, spacing = the measured
   square size) and solve for the intrinsics and lens distortion with `cv2.calibrateCamera`.
   Using the measured square size makes the model metric (millimetres).
5. Report the RMS reprojection error — overall and per view — as the accuracy indicator.

## Target

- Pattern: **9 × 6 inner corners** (a 10 × 7 square board).
- Square edge length: **measured** with a ruler/calipers and passed as `--square-size-mm`;
  never assumed from the nominal print size.

## What is recorded

`data/calibration.json`:

| Field | Meaning |
| ----- | ------- |
| `camera_matrix` | 3×3 intrinsic matrix `K` (pixels) |
| `dist_coeffs` | distortion coefficients `(k1, k2, p1, p2, k3, ...)` |
| `image_size` | `[width, height]` in pixels |
| `pattern_size` | `[cols, rows]` inner corners |
| `square_size_mm` | measured square edge length |
| `num_images` | images with a detected chessboard, used in the solve |
| `rms_reprojection_error` | overall RMS reprojection error (pixels) |
| `per_view_errors` | per-image RMS reprojection error (pixels) |
| `used_images` / `failed_images` | image paths, detected vs not |

## Run

```
python scripts/run_calibration.py \
    --images-dir data/calibration_images \
    --pattern 9x6 \
    --square-size-mm <your measured value> \
    --out data/calibration.json \
    --report results/calibration_report.md
```
