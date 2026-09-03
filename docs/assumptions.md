# Dimension-estimation assumptions

These assumptions apply to `module2.dimension_estimation` and the Step 2 / Step 3 workflow.
They are stated so the reported errors can be interpreted honestly.

## Camera model

- **Pinhole camera model.** The calibrated intrinsic matrix `K` and distortion coefficients
  come from `module2.calibration` on the user's real photographs.
- **Lens distortion is removed exactly once**, by `cv2.undistortPoints(pts, K, dist, P=None)`
  on the raw-image pixel points. The raw image itself is *not* separately undistorted on the
  estimation path — undistorting both the image and the points would double-correct.

## Scene geometry

- **The object is planar** (or the two measured points lie on one plane) and that plane is
  **parallel to the camera sensor plane** (fronto-parallel), so every measured point shares
  a single depth `Z`.
- **`Z` is the perpendicular depth of the object plane along the optical axis** — not the
  slant range to an off-axis point. The camera projection centre is not physically
  accessible, so in the field `Z` is approximated by the **smartphone camera-body /
  lens position**. Mitigations: keep the measured feature near the image centre, and hold
  the phone so its back is parallel to the object plane.
- Pixel points are **user-supplied**. Their localisation error (a few pixels) propagates
  into the dimension estimate and is part of the reported error budget.

## Capture

- The **same camera, lens, and fixed focus / zoom / resolution** as calibration (see
  `calibration_capture_protocol.md`). If the phone re-focuses or switches lens between
  calibration and measurement, the intrinsics no longer apply.
- **Negligible motion blur**; rolling-shutter effects are ignored.

## Units

- Millimetre (mm) is the single internal length unit. A distance the user enters in metres
  is converted to millimetres once, at the IO boundary (`module2.units.metres_to_mm`).

## Method

For each measured segment with endpoints `p1`, `p2` (raw pixels):

1. `n = cv2.undistortPoints([p1, p2], K, dist, P=None)` → normalized coordinates on the
   `z = 1` plane.
2. Rays `r_i = [n_i_x, n_i_y, 1]`.
3. `Xc_i = Z_mm * r_i` — points on the object plane, in camera-frame millimetres.
4. `length_mm = ‖Xc_1 − Xc_2‖`.

Width and height are each measured from their own endpoint pair on the same image at the
same `Z`.
