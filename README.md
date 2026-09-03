# CSc 8830 — Module 2: Camera Calibration & 2D Object Dimension Estimation

Smartphone camera calibration (OpenCV) and real-world 2D object dimension estimation by
perspective back-projection, with a Streamlit app, a 20-trial experimental-validation
workflow, and a two-camera projection theory write-up.

> **Status: scaffold (Phase 0).** Core functionality is stubbed and lands phase by phase
> (see the table below). Calibration and every measured result are **pending real
> smartphone data** — nothing in this repository fabricates experimental values.

## Requirements

- Python 3.10+
- `pip install -e ".[dev]"` — installs `module2` plus `pytest`
- For the report PDF only: `pandoc` and a LaTeX engine (installed separately)

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

## Layout

```
app.py                     standalone Streamlit submission app (thin shell)
src/module2/               core CV/math — never imports Streamlit
  units.py  io_utils.py    unit conversions; image IO helpers
  geometry.py              the single canonical undistort + back-projection pipeline
  calibration.py           chessboard detection + OpenCV calibration
  dimension_estimation.py  object width/height from user pixel points + object-plane depth
  metrics.py               validation error definitions & statistics
  validation.py            20-trial CSV -> per-row errors + summary
  webapp/                  Streamlit pages + the PageSpec / get_pages provider contract
scripts/                   run_calibration, estimate_dimensions, analyze_validation, build_report
tests/                     deterministic unit tests
data/                      calibration_images/ and experiments/ (your photos; git-ignored)
results/                   generated calibration_report.md, validation_summary.md, measurements_template.csv
docs/                      architecture, capture protocol, assumptions, validation protocol, theory, report/
```

## Workflow (phases)

| Phase | Branch | Deliverable |
| ----- | ------ | ----------- |
| 0 | `task/module-2-scaffold` | packaging, app shell, stubs, page-contract tests |
| 1 | `task/module-2-camera-calibration` | chessboard calibration + capture protocol |
| 2 | `task/module-2-object-dimension-estimation` | back-projection estimation |
| 3 | `task/module-2-validation-analysis` | 20-trial validation tooling + template |
| 4 | `task/module-2-two-camera-theory` | two-camera projection derivation |
| 5 | `task/module-2-webapp-and-docs` | integration, report assembly, run/deploy |

## Reproducing results (once implemented)

1. Follow `docs/calibration_capture_protocol.md`; measure the printed chessboard square.
2. `python scripts/run_calibration.py --images-dir data/calibration_images --pattern 9x6 --square-size-mm <measured>`
3. `python scripts/estimate_dimensions.py --image <img> --calibration data/calibration.json --distance-m <z> --width-points "x1,y1 x2,y2" --height-points "x1,y1 x2,y2"`
4. Collect 20 trials at object-plane depth > 2 m per `docs/validation_protocol.md`; fill `results/measurements_template.csv`.
5. `python scripts/analyze_validation.py --measurements results/measurements_template.csv --calibration data/calibration.json`
6. `python scripts/build_report.py --out results/module2_report.pdf`

## Constraints

- No machine-learning / deep-learning methods.
- Manual pixel-point selection only — automatic object detection is out of scope.
- Everything under `data/` and every generated experimental value is the user's real
  measurement.
