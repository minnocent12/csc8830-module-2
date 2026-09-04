# CSc 8830 — Module 2: Camera Calibration & 2D Object Dimension Estimation

Smartphone camera calibration (OpenCV) and real-world 2D object dimension estimation by
perspective back-projection, with a Streamlit app, a 20-trial experimental-validation
workflow, and a two-camera projection theory write-up.

> Calibration output and all measured results come from **your** real experiments. Nothing
> in this repository fabricates calibration values, measurements, or statistics — the
> template ships empty and un-run sections of the report are marked *pending*.

## Requirements

- Python 3.10+
- `pip install -e ".[dev]"` — installs `module2` plus `pytest`
- For the report **PDF** only: `pandoc` **and** a LaTeX engine supported by pandoc, both
  installed separately. `results/module2_report.md` is produced without them.

## Install & run (from this repository root)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
streamlit run app.py
```

Working from the `Assignments/` workspace root instead? Prefix paths with `Module_2/`:
`pip install -e "./Module_2[dev]"`, `streamlit run Module_2/app.py`,
`pytest -q Module_2/tests`.

`app.py` and the `scripts/` entry points add `src/` to the path themselves, so they run from
a clone even if the editable install is skipped or its `.pth` is not honoured (seen on some
Python 3.14 builds); only the third-party packages in `pyproject.toml` are strictly
required. `pytest` finds the package via `pythonpath = ["src"]` in `pyproject.toml`.

## Web application

`streamlit run app.py` opens all four assignment components in one app:

| Page | Purpose |
| ---- | ------- |
| Calibration | run the chessboard calibration, view `K` / distortion / reprojection error, download `calibration.json` |
| Dimension Estimation | back-project user-selected pixel points to real-world width/height at a measured depth |
| Validation Analysis | load the 20-trial CSV; per-row and width / height / combined error statistics |
| Theory | the two-camera projection derivation |

Deploy for the instructor: a hosted Streamlit URL is preferred if available (e.g. Streamlit
Community Cloud pointed at `app.py`); otherwise the exact local steps above plus the demo
video are sufficient. Record the URL or steps in the final PDF.

## Layout

```
app.py                     standalone Streamlit app (thin shell)
src/module2/               core CV/math — never imports Streamlit
  units.py  io_utils.py    unit conversions; image IO helpers
  geometry.py              the single canonical undistort + back-projection pipeline
  calibration.py           chessboard detection + OpenCV calibration
  dimension_estimation.py  object width/height from user pixel points + object-plane depth
  metrics.py               validation error definitions & statistics
  validation.py            20-trial CSV -> per-row errors + summary
  report.py                assemble the report from its canonical section files
  webapp/                  Streamlit pages + the PageSpec / get_pages provider contract
scripts/                   run_calibration, estimate_dimensions, analyze_validation, build_report
tests/                     deterministic unit tests
data/                      calibration_images/ and experiments/ (your photos; git-ignored)
results/                   measurements_template.csv (tracked); generated reports/plots (git-ignored)
docs/                      capture protocol, calibration method, assumptions, validation protocol,
                           two-camera theory, report/ (manifest + overview + figures)
```

## Reproducing the results

Run from this repository root (prefix scripts with `Module_2/` from the workspace root).

1. **Calibrate.** Follow `docs/calibration_capture_protocol.md` — print the 9×6 chessboard at
   100 %, **measure the printed square** with calipers, lock AE/AF when supported, take
   15–25 sharp varied-pose photos into `data/calibration_images/`. Then:
   ```bash
   python scripts/run_calibration.py --images-dir data/calibration_images \
       --pattern 9x6 --square-size-mm <your measured value>
   ```
   → `data/calibration.json` + `results/calibration_report.md`.
2. **Estimate a dimension** (sanity check):
   ```bash
   python scripts/estimate_dimensions.py --image data/experiments/img.jpg \
       --calibration data/calibration.json --distance-m 2.6 \
       --width-points "x1,y1 x2,y2" --height-points "x1,y1 x2,y2"
   ```
3. **Collect 20 trials.** Per `docs/validation_protocol.md`: real objects, object-plane
   depth `> 2 m`, measured width/height, four pixel points each. Fill
   `results/measurements_template.csv` (a plain CSV — one header + 20 rows).
4. **Analyse:**
   ```bash
   python scripts/analyze_validation.py \
       --measurements results/measurements_template.csv \
       --calibration data/calibration.json
   ```
   → `results/validation_summary.md`, a `*_filled.csv`, and error plots in
   `docs/report/figures/`.
5. **Build the report:**
   ```bash
   python scripts/build_report.py
   ```
   `results/module2_report.md` is **always** written. `results/module2_report.pdf` is
   produced only when **both `pandoc` and a LaTeX engine supported by pandoc** are
   installed; if either is missing the script leaves the Markdown report intact and prints
   the exact `pandoc` command to run later. Sections you have not generated yet appear as
   *pending* notes.

## Known limitations

- **Fronto-parallel assumption** — the object plane must be roughly parallel to the sensor;
  tilt introduces perspective error.
- **`Z` is optical-axis depth** — the camera projection centre is inside the phone, so the
  field measurement uses the phone body as a proxy; keep the feature near the image centre.
- **Autofocus** — if the phone re-focuses or switches lens between calibration and capture,
  the intrinsics no longer apply; re-calibrate.
- **Manual point selection** — pixel-point localisation error propagates into the estimate
  (part of the reported error budget). No automatic object detection is in scope.
- **No machine-learning / deep-learning methods** are used anywhere.
