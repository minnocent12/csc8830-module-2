# Module 2 — Smartphone Camera Calibration and Real-World 2D Object Dimension Estimation

**GitHub repository:** <https://github.com/minnocent12/csc8830-module-2>

## Problem

Estimate the real-world width and height of a planar object from a single smartphone
photograph, using a calibrated camera model and perspective back-projection, and characterise
the method's accuracy over 20 controlled measurements.

## Workflow (completed in order)

1. **Camera calibration** — calibrate the smartphone with an OpenCV chessboard workflow;
   record the intrinsic matrix `K`, the distortion coefficients, and the RMS reprojection
   error. See *Camera calibration — method* and *Camera calibration — results*.
2. **Dimension estimation** — undistort the user-selected pixel points with
   `cv2.undistortPoints(..., P=None)`, form calibrated rays, and scale them by the measured
   object-plane depth `Z` to recover width and height in millimetres. Assumptions and method
   in *Dimension estimation — assumptions & method*.
3. **Experimental validation** — 20 trials at object-plane depth `> 2 m`; per-trial and
   aggregate (width / height / combined) error statistics in *Experimental validation*.
4. **Two-camera projection theory** — a full derivation of how one 3D point's image
   coordinates relate across two differently-posed cameras (essential and fundamental
   matrices). See *Two-camera projection*.

## Implementation

Python 3 + OpenCV. The computer-vision core (`src/module2/`) is independent of the Streamlit
UI (`src/module2/webapp/`, entry point `app.py`). Deterministic logic is covered by an
automated test suite. Calibration output and the 20-measurement dataset come from real
experiments; nothing in the repository fabricates them. Setup and run instructions are in
`README.md`.
