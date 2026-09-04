# Module 2 report — section manifest

`scripts/build_report.py` concatenates the section files listed below, **in order**, into a
single Markdown document (`results/module2_report.md`) and renders it to
`results/module2_report.pdf` with pandoc. The report has **no prose of its own** — each
section lives in exactly one canonical file, so nothing is duplicated.

A section file that has not been generated yet (for example `results/calibration_report.md`
before calibration is run) is replaced by a short *pending* note; no placeholder values are
invented.

## Section order

```text
docs/report/_overview.md
docs/calibration_method.md
results/calibration_report.md
docs/assumptions.md
results/validation_summary.md
docs/theory_two_camera_projection.md
```

## Notes

| Section source | Content | Produced by |
| -------------- | ------- | ----------- |
| `docs/report/_overview.md` | problem statement, workflow overview, GitHub link | authored (Phase 5) |
| `docs/calibration_method.md` | calibration method + `data/calibration.json` schema | authored (Phase 1) |
| `results/calibration_report.md` | measured `K`, distortion, RMS reprojection error | `scripts/run_calibration.py` on real photos |
| `docs/assumptions.md` | dimension-estimation assumptions and method | authored (Phase 2) |
| `results/validation_summary.md` | 20-trial table + width / height / combined statistics | `scripts/analyze_validation.py` on real data |
| `docs/theory_two_camera_projection.md` | two-camera projection derivation | authored (Phase 4) |

`scripts/analyze_validation.py` writes the error plots to `docs/report/figures/` and appends
`![caption](figures/<name>.png)` links to `results/validation_summary.md`. `build_report.py`
puts `docs/report/` on pandoc's `--resource-path`, so those links resolve to the plot files
when the PDF is rendered. If validation has not been run, the section is *pending* and no
figures are referenced.
