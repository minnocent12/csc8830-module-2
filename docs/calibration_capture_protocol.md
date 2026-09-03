# Reproducible smartphone calibration capture protocol

Follow this once, before collecting any calibration images. The goal is a set of sharp,
well-varied chessboard photographs taken under the **same camera configuration** you will
use for the dimension-estimation experiments, so the intrinsics stay valid across both.

## 1. Print and mount the target

- Print a **9 × 6 inner-corner** chessboard (a 10 × 7 grid of squares) at **100 % / "actual
  size"** — disable "fit to page" / "shrink to fit".
- Use **matte** paper; glossy paper causes glare that breaks corner detection.
- Mount it **flat** on a rigid backing (foam board, clipboard, stiff cardboard). Any curl or
  ripple biases the calibration.

## 2. Measure the printed square

- With a ruler or calipers, measure across **several** squares at once (for example the full
  width of 8 squares) and divide, to average out print error.
- Record the single-square edge length to **0.1 mm**. This value is `--square-size-mm`.
- Do **not** assume the nominal size — consumer printers commonly rescale by 1–3 %.

## 3. Fix the camera configuration

- Use the **single rear lens** you will use for the experiments (not an ultra-wide or tele
  lens; do not let the camera switch lenses mid-session).
- **Lock focus and exposure (AE/AF lock) when your camera app supports it** — on iPhone,
  tap and hold until "AE/AF LOCK" appears; on many Android camera apps, tap and hold the
  subject.
- If your app has no AE/AF lock, instead keep the capture conditions constant: even, diffuse
  lighting; a fixed subject-distance range; **no digital zoom**; and the **same photo
  resolution and aspect ratio** throughout — the same ones you will use for the experiment
  photos.
- Turn **HDR off**. Turn off any "AI scene" / "beautify" enhancement.

## 4. Capture the set

Take **15–25** photos of the mounted board:

- **Cover the whole frame:** board near each of the four corners, and centred.
- **Vary orientation:** tilt roughly **20°–45°** about both the horizontal and vertical
  axes.
- **Vary distance:** some near (board fills ≳ ⅓ of the frame), some farther.
- Keep every shot **sharp** — brace the phone or use a short self-timer; discard anything
  with motion blur.
- Keep the **whole board visible** in every shot.

## 5. Load and check

- Put the images in `data/calibration_images/` (this folder is git-ignored).
- Run the calibration (see `calibration_method.md`):

  ```
  python scripts/run_calibration.py --images-dir data/calibration_images \
      --pattern 9x6 --square-size-mm <your measured value>
  ```

- The script reports which images the detector rejected — re-shoot those and re-run.
- Aim for an overall RMS reprojection error well under ~1 px. Much higher usually means a
  bad square measurement, a non-flat board, motion blur, or an inconsistent resolution.

## 6. Re-calibrate if the camera changes

Re-run calibration if, between calibrating and the experiments, the phone changes lens,
the autofocus shifts, you switch resolution/aspect ratio, or a software update alters the
camera pipeline.
