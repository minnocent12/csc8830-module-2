# Experimental validation protocol (Step 3)

Twenty measurements of real objects, used to characterise the accuracy of the
dimension-estimation method. This file is the single source of truth for the CSV columns,
units, and acceptance rules; `results/measurements_template.csv` is a plain machine-readable
CSV with no comment lines.

## Experiment

For each of the 20 trials:

1. Choose an object with a clearly measurable width and height (a box, a book, a monitor…).
2. Measure its **true width and height** with a tape measure / ruler, in **millimetres**.
3. Place it so its face is parallel to the phone's back, at an **object-plane depth greater
   than 2 metres** along the optical axis. Measure that depth as accurately as you can (the
   camera projection centre is inside the phone, so use the phone body as the reference
   point) and record it in **metres**.
4. Photograph it with the **same phone / lens / focus / zoom / resolution** used for
   calibration (see `calibration_capture_protocol.md`). Save the image under
   `data/experiments/` and note the path.
5. Open the image in any viewer and read off four pixel coordinates:
   - **width**: the two endpoints spanning the object's width (`w_p1`, `w_p2`);
   - **height**: the two endpoints spanning its height (`h_p1`, `h_p2`).
   Pick well-separated points near the image centre where possible.

Then run `scripts/analyze_validation.py` (or the Validation Analysis page) to fill in the
estimates and errors and produce `results/validation_summary.md`.

## CSV columns

### You fill these in

| Column | Unit | Meaning |
| ------ | ---- | ------- |
| `measurement_id` | — | any label, e.g. `1`…`20` |
| `object_name` | — | short description |
| `object_plane_depth_z_m` | metres | perpendicular depth of the object plane along the optical axis; **must be > 2.0** |
| `image_path` | — | path to the saved photo (e.g. `data/experiments/img_03.jpg`) |
| `w_p1_x`, `w_p1_y`, `w_p2_x`, `w_p2_y` | pixels | width endpoints in the raw image |
| `h_p1_x`, `h_p1_y`, `h_p2_x`, `h_p2_y` | pixels | height endpoints in the raw image |
| `actual_width_mm` | mm | measured true width; **must be > 0** |
| `actual_height_mm` | mm | measured true height; **must be > 0** |

### The tool computes and overwrites these

| Column | Unit | Meaning |
| ------ | ---- | ------- |
| `estimated_width_mm`, `estimated_height_mm` | mm | back-projection estimate |
| `width_signed_error_mm`, `height_signed_error_mm` | mm | `estimated − actual` |
| `width_absolute_error_mm`, `height_absolute_error_mm` | mm | `\|estimated − actual\|` |
| `width_percentage_error`, `height_percentage_error` | % | `absolute_error / actual × 100` |

## Acceptance rules

A row is **rejected** (kept out of the aggregate statistics and listed separately) when:

- `object_plane_depth_z_m` is not a finite number **> 2.0**;
- `actual_width_mm` or `actual_height_mm` is not a finite number **> 0**;
- any of the eight pixel coordinates is missing or non-numeric.

A missing `image_path` is flagged (`no_image_path`) but does **not** reject the row — the
estimate needs only the points, the depth, and the calibration.

## Reported statistics

Computed separately for **width**, for **height**, and for the two **combined**:

- mean error (signed), mean absolute error, mean percentage error,
- sample standard deviation of the signed error (`n − 1`),
- minimum and maximum absolute error.
