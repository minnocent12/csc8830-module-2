# Module 2 report — section manifest

`scripts/build_report.py` assembles the final PDF by concatenating the canonical source
files below **in order**. Each section's text lives in exactly one place; nothing here is a
copy.

| Order | Section | Canonical source | Filled in |
| ----- | ------- | ---------------- | --------- |
| 1 | Problem & overview | `docs/report/_overview.md` | Phase 5 |
| 2 | Camera calibration — method | `docs/calibration_method.md` | Phase 1 |
| 3 | Camera calibration — results | `results/calibration_report.md` | Phase 1 (real run) |
| 4 | Dimension estimation — assumptions & method | `docs/assumptions.md` | Phase 2 |
| 5 | Experimental validation | `results/validation_summary.md` | Phase 3 (real data) |
| 6 | Two-camera projection theory | `docs/theory_two_camera_projection.md` | Phase 4 |

Figures are inserted from `docs/report/figures/` as referenced by the section files.
