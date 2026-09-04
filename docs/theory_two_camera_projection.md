# Two-camera projection — relationship between the image coordinates of one 3D point

## 0. Problem statement

A static 3D point $P$ lies in the field of view of two cameras. **Camera 1** is fixed.
**Camera 2** is displaced from Camera 1 by a known translation and rotated to an *oblique*
orientation. $P$ projects to $(u_1, v_1)$ in Camera 1 and $(u_2, v_2)$ in Camera 2. We
derive how the two image points are related, define every parameter, and state the
assumptions.

---

## 1. Coordinate systems

| Frame | Origin | Axes | World point in this frame |
| ----- | ------ | ---- | ------------------------- |
| World $\{W\}$ | arbitrary fixed point | right-handed | $P = (X, Y, Z)^\top$, homogeneous $\tilde P = (X, Y, Z, 1)^\top$ |
| Camera 1 $\{C_1\}$ | Camera 1 optical centre | $z$ along the optical axis into the scene, $x$ right, $y$ down (OpenCV) | $P_1 = R_1 P + t_1$ |
| Camera 2 $\{C_2\}$ | Camera 2 optical centre | same conventions | $P_2 = R_2 P + t_2$ |
| Image $i$ | top-left pixel | $u$ right, $v$ down | $(u_i, v_i)$ — ordinary pixel coordinates |

$(u_i, v_i)$ are **ordinary image pixel coordinates**: the origin is the **image origin
(top-left pixel)** and $v$ increases downward. The principal point $(c_x, c_y)$ is **not the
coordinate origin** — it enters only as the offset added by $K$ (§2).

$(R_i, t_i)$ are the **extrinsics** of camera $i$ — the pose of the world frame expressed in
that camera's frame. The *normalized image plane* of a camera is the plane $z = 1$ in its
own frame; the intrinsic matrix $K$ (next section) maps normalized coordinates to pixels.

We attach the world frame to Camera 1, $\{W\} \equiv \{C_1\}$, so $R_1 = I$, $t_1 = 0$
(justified in §3).

---

## 2. Camera intrinsic parameters

For each camera the pinhole intrinsic matrix is

$$
K = \begin{bmatrix} f_x & s & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}.
$$

* $f_x = f\,m_x$ and $f_y = f\,m_y$ — the focal length $f$ (in mm) times the pixel density
  $m_x, m_y$ (px/mm) along each sensor axis, i.e. **focal length in pixels**. $f_x \neq f_y$
  when the pixels are not square.
* $(c_x, c_y)$ — the **principal point**: the pixel where the optical axis pierces the
  sensor, nominally the image centre.
* $s$ — **skew**, non-zero only if the sensor axes are not perpendicular; $s \approx 0$ for
  modern cameras.

A normalized camera-frame point $\hat x = (X_c/Z_c,\ Y_c/Z_c,\ 1)^\top$ maps to the ordinary
pixel coordinates $(u, v)$ by $(u, v, 1)^\top = K\,\hat x$, that is
$u = f_x x + s y + c_x$, $v = f_y y + c_y$. The additive $c_x, c_y$ are exactly what moves
the origin from the principal point to the top-left pixel.

**How calibration yields $K$.** Photograph a planar chessboard of *measured* square size
from many poses. Each view gives 3D→2D correspondences and a homography
$H = K\,[\,r_1\ r_2\ t\,]$; the orthonormality of $r_1, r_2$ gives two linear constraints per
view on $\omega = K^{-\top}K^{-1}$. Stacking $\ge 3$ views solves for $\omega$, hence $K$ by
Cholesky factorization; a non-linear refinement (Levenberg–Marquardt) then minimizes the
total reprojection error over $K$, the distortion coefficients, and every per-view
$(R, t)$. This is precisely `cv2.calibrateCamera` (Module 2, Step 1), which also reports the
RMS reprojection error as the accuracy figure.

---

## 3. Camera 1 projection

The full perspective model for Camera 1:

$$
\lambda_1 \begin{bmatrix} u_1 \\ v_1 \\ 1 \end{bmatrix}
= K_1\,[\,R_1 \mid t_1\,]\begin{bmatrix} X \\ Y \\ Z \\ 1 \end{bmatrix},
\qquad \lambda_1 = (R_1 P + t_1)_z .
$$

$\lambda_1$ is the **depth** of $P$ along Camera 1's optical axis — the scale discarded by
the perspective division $x = X_c/Z_c$.

**Reference-frame choice — why $R_1 = I$, $t_1 = 0$ is free.** The world frame is arbitrary,
so we may *define* it to coincide with $\{C_1\}$. Then the pose of the world in Camera 1 is
the identity. This is a choice of coordinates, not a claim about the scene, and it loses no
generality: any other world frame differs from $\{C_1\}$ by a fixed rigid transform that is
simply absorbed into Camera 2's extrinsics. With it,

$$
\lambda_1 \begin{bmatrix} u_1 \\ v_1 \\ 1 \end{bmatrix} = K_1 \begin{bmatrix} X \\ Y \\ Z \end{bmatrix},
\qquad P_1 \equiv P = (X, Y, Z)^\top,
\qquad \hat x_1 = K_1^{-1}(u_1, v_1, 1)^\top = \frac{P_1}{Z}.
$$

In code, $\hat x_1$ is produced **directly** by `cv2.undistortPoints(pts, K, dist, P=None)`;
its output is already $K_1^{-1}$-applied (and distortion-corrected), so $K_1^{-1}$ must not
be applied to it again — see assumption 2.

---

## 4. Camera 2 pose relative to Camera 1

Let $(R, t)$ be the rigid transform taking a point from $\{C_1\}$ to $\{C_2\}$:

$$
\boxed{\,P_2 = R\,P_1 + t\,}.
$$

* $R \in SO(3)$ is the **relative rotation** — it encodes Camera 2's oblique orientation
  (yaw / pitch / roll away from Camera 1's axes). The columns of $R^\top$ are Camera 1's
  axes as seen from Camera 2.
* $t \in \mathbb{R}^3$ is the origin of $\{C_1\}$ expressed in $\{C_2\}$. The Camera 2 →
  Camera 1 baseline vector is $-R^\top t$ and $\lVert t \rVert$ is the **baseline length**
  (the known distance between the two optical centres).

Because $\{W\} \equiv \{C_1\}$, Camera 2's world extrinsics are exactly $R_2 = R$, $t_2 = t$.

---

## 5. Camera 2 projection

$$
\lambda_2 \begin{bmatrix} u_2 \\ v_2 \\ 1 \end{bmatrix}
= K_2\,[\,R \mid t\,]\begin{bmatrix} X \\ Y \\ Z \\ 1 \end{bmatrix}
= K_2\,(R\,P_1 + t),
\qquad \lambda_2 = (R\,P_1 + t)_z ,
\qquad \hat x_2 = K_2^{-1}(u_2, v_2, 1)^\top = \frac{P_2}{\lambda_2}.
$$

---

## 6. Relationship between $(u_1, v_1)$ and $(u_2, v_2)$

### 6.1 There is no point-to-point map without depth

From §3, $P_1 = Z\,\hat x_1$ with $Z$ unknown from Camera 1 alone. Substituting into §4–5:

$$
\lambda_2\,\hat x_2 = R\,(Z\,\hat x_1) + t = Z\,R\,\hat x_1 + t .
$$

For a fixed $(u_1, v_1)$ the world point may lie anywhere on the ray
$\{Z\,\hat x_1 : Z > 0\}$; its image in Camera 2 sweeps a **line** — the *epipolar line* —
not a single point. Pinning down $(u_2, v_2)$ needs the extra scalar $Z$.

### 6.2 Epipolar constraint → essential matrix (calibrated cameras)

The vectors $\hat x_2 \ (\propto P_2)$, $t$, and $R\,\hat x_1 \ (\propto R P_1)$ are
**coplanar**: from $\lambda_2 \hat x_2 = Z\,R\,\hat x_1 + t$, the vector
$\lambda_2 \hat x_2 - t = Z\,R\,\hat x_1$ lies in $\mathrm{span}\{t,\ R\,\hat x_1\}$. Its
scalar triple product with $t \times (R\,\hat x_1)$ therefore vanishes:

$$
\hat x_2^\top \big( t \times (R\,\hat x_1) \big) = 0
\;\Longleftrightarrow\;
\hat x_2^\top\, [t]_\times R\,\hat x_1 = 0 ,
\qquad
[t]_\times = \begin{bmatrix} 0 & -t_z & t_y \\ t_z & 0 & -t_x \\ -t_y & t_x & 0 \end{bmatrix}.
$$

Define the **essential matrix**

$$
\boxed{\,E = [t]_\times R\,}, \qquad \hat x_2^\top E\,\hat x_1 = 0 .
$$

$E$ has rank 2, its two non-zero singular values are equal, and it has 5 degrees of freedom
(3 for $R$, 2 for the *direction* of $t$ — the overall scale of $t$ is unobservable from
images).

### 6.3 Pixel form → fundamental matrix

Substitute $\hat x_1 = K_1^{-1} x_1$ and $\hat x_2 = K_2^{-1} x_2$ with
$x_1 = (u_1, v_1, 1)^\top$, $x_2 = (u_2, v_2, 1)^\top$:

$$
(K_2^{-1} x_2)^\top E\,(K_1^{-1} x_1) = 0
\;\Longrightarrow\;
x_2^\top \underbrace{K_2^{-\top} E\,K_1^{-1}}_{F}\, x_1 = 0 .
$$

The **fundamental matrix**

$$
\boxed{\,F = K_2^{-\top} [t]_\times R\, K_1^{-1}\,}, \qquad x_2^\top F\,x_1 = 0 .
$$

$F$ sends a point in image 1 to its **epipolar line** in image 2, $\ell_2 = F x_1$ (with
$x_2^\top \ell_2 = 0$), and $\ell_1 = F^\top x_2$ in the other direction. $F$ has rank 2 and
7 DoF (9 entries, minus scale, minus $\det F = 0$). The **epipoles** — the image of each
camera's centre in the other view — satisfy $F e_1 = 0$ and $F^\top e_2 = 0$, with
$e_1 \simeq K_1(-R^\top t)$ and $e_2 \simeq K_2\, t$.

### 6.4 Recovering the actual corresponding point (supply the depth)

1. **Known depth $Z$** (e.g. the measured camera-to-plane distance from Step 3):
   $P_1 = Z\,\hat x_1$, then
   $(u_2, v_2, 1)^\top = \tfrac{1}{\lambda_2} K_2 (R P_1 + t)$, $\lambda_2 = (R P_1 + t)_z$.
2. **Triangulation:** solve the 3 equations $\lambda_2 \hat x_2 = Z\,R\,\hat x_1 + t$ for the
   2 unknowns $Z, \lambda_2$ in least squares, then project as in (1).
3. **Plane-induced homography:** if $P$ lies on a known plane $\hat n^\top P_1 = d$ in
   $\{C_1\}$, then $x_2 \simeq H x_1$ with
   $H = K_2\big(R + t\,\hat n^\top/d\big) K_1^{-1}$ — a true point-to-point map, valid only
   for points on that plane.

### 6.5 How $R$ and $t$ govern the relationship

* **Pure rotation** $(t = 0)$: $E = 0$, the epipolar constraint is vacuous, and
  $x_2 \simeq K_2 R K_1^{-1} x_1$ is an *exact, depth-independent homography* (rotating about
  a single centre does not change which ray a point is on).
* **Pure translation** $(R = I)$: $E = [t]_\times$; every epipolar line passes through
  $e_2 \simeq K_2 t$. If further $t = (b, 0, 0)$ then, under our convention
  $P_2 = R\,P_1 + t = P_1 + (b, 0, 0)^\top$, so $Z_2 = Z$ and $X_2 = X_1 + b$. With equal
  intrinsics ($K_1 = K_2 = K$, $f \equiv f_x = f_y$) and zero skew this gives horizontal
  epipolar lines and

  $$
  u_2 = u_1 + f\,b/Z, \qquad v_2 = v_1 .
  $$

  The sign is **positive**: adding $b$ to the point's $x$-coordinate in Camera 2's frame
  shifts its image to the right. The textbook "disparity $= f\,b/Z$" with a *minus* sign
  uses the opposite convention in which $t$ is Camera 2's *centre position*
  ($P_2 = R(P_1 - C_2)$, giving $X_2 = X_1 - b$); the two conventions must not be mixed. The
  only residual unknown is the single scalar $Z$.
* **General oblique $(R, t)$:** $R$ rotates each back-projected ray and $t$ offsets the
  centre; together they fix the epipolar geometry ($E$, $F$) — hence the epipolar line each
  point is confined to — while $\lVert t \rVert$ sets the metric scale of any triangulated
  depth.

---

## 7. Parameters and variables

| Symbol | Description | Classification | How determined |
| ------ | ----------- | -------------- | -------------- |
| $X, Y, Z$ | 3D coordinates of $P$ in $\{C_1\}$ | **variable** (unknown from one view) | measured, or triangulated from both views |
| $u_1, v_1$ | image coordinates of $P$ in Camera 1 | **measured variable** | detected in image 1 |
| $u_2, v_2$ | image coordinates of $P$ in Camera 2 | **measured variable** | detected in image 2 |
| $K_1, K_2$ | intrinsic matrices | **known / static** (per camera) | camera calibration (Step 1) |
| $f_x, f_y$ | focal lengths in pixels | known / static | entries of $K$, from calibration |
| $c_x, c_y$ | principal point | known / static | entries of $K$, from calibration |
| $s$ | skew ($\approx 0$) | known / static | from calibration |
| $R$ | relative rotation $\{C_1\}\to\{C_2\}$ | **known / measured**, static per setup | measured rig geometry, or estimated from $\ge 5$ correspondences via $E$ |
| $t$ | relative translation $\{C_1\}\to\{C_2\}$ | **known / measured**, static per setup | measured baseline, or up to scale from $E$ |
| $[t]_\times$ | skew-symmetric matrix of $t$ | derived | from $t$ |
| $E = [t]_\times R$ | essential matrix | derived | from $R, t$ |
| $F = K_2^{-\top} E\,K_1^{-1}$ | fundamental matrix | derived | from $E, K_1, K_2$; or directly from $\ge 8$ correspondences |
| $\lambda_1, \lambda_2$ | projective depth scales | derived | $\lambda_1 = Z$, $\lambda_2 = (R P_1 + t)_z$ |
| $e_1, e_2$ | epipoles | derived | $e_1 \simeq K_1(-R^\top t)$, $e_2 \simeq K_2 t$ |

---

## 8. Assumptions (with justification)

1. **Pinhole projection.** Each camera is an ideal central projection; finite-aperture /
   defocus effects are negligible for in-focus captures.
2. **Lens distortion removed.** The linear model $\hat x = K^{-1}(u, v, 1)^\top$ holds
   exactly because lens distortion has been removed with the calibrated coefficients. In
   Module 2 the normalized calibrated point $\hat x$ is obtained **directly** from
   `cv2.undistortPoints(pts, K, dist, P=None)`: with **`P=None` this call returns normalized
   camera coordinates** on the $z = 1$ plane — distortion is already removed *and* $K^{-1}$
   has effectively already been applied, so **$K^{-1}$ must not be applied again** to its
   output (this matches `src/module2/geometry.py`). The alternative form
   `cv2.undistortPoints(pts, K, dist, P=K)` instead returns *undistorted pixel* coordinates
   $(u, v)$ — to which $K^{-1}$ would still have to be applied — and is **not the canonical
   Module 2 path**.
3. **Camera 1 is the reference frame** ($R_1 = I$, $t_1 = 0$) — a coordinate choice, fully
   general (§3).
4. **Intrinsics constant.** $K_1, K_2$ and the distortion do not change between calibration
   and capture: same lens, fixed focus and zoom, same resolution (Module 2 capture
   protocol).
5. **Rigid, known relative pose.** $(R, t)$ is fixed during the experiment and is measured
   from the rig or estimated; $\lVert t \rVert > 0$ so a genuine two-view (epipolar)
   geometry exists.
6. **$P$ is static and visible in both images**, so $(u_1, v_1)$ and $(u_2, v_2)$ are images
   of the *same* world point.
7. **Negligible motion blur.** If the two exposures are not simultaneous, the scene is
   stationary — equivalent for a static point.
8. **Consistent metric scale.** Both cameras are calibrated in the same physical units
   (mm), so lengths and $\lVert t \rVert$ are comparable.

---

## 9. Illustrative numerical example (synthetic — *not* measured data)

*Chosen to make the algebra concrete; these are not experimental values.*

Let
$K_1 = K_2 = \begin{bmatrix} 800 & 0 & 320 \\ 0 & 800 & 240 \\ 0 & 0 & 1 \end{bmatrix}$,
$R = R_y(10^\circ) = \begin{bmatrix} 0.98481 & 0 & 0.17365 \\ 0 & 1 & 0 \\ -0.17365 & 0 & 0.98481 \end{bmatrix}$,
$t = (-120,\ 0,\ -15)^\top$ mm, and the point $P_1 = (40,\ 30,\ 1000)^\top$ mm.

**Camera 1.** $\hat x_1 = P_1 / 1000 = (0.040,\ 0.030,\ 1)$, so

$$
(u_1, v_1) = (800\cdot 0.040 + 320,\ \ 800\cdot 0.030 + 240) = (352.000,\ 264.000).
$$

**Camera 2.** $P_2 = R P_1 + t = (93.0405,\ 30.0000,\ 962.8618)^\top$ mm,
$\lambda_2 = 962.8618$, so

$$
(u_2, v_2) = K_2\,P_2/\lambda_2 = (397.3033,\ 264.9257).
$$

**Essential matrix.**

$$
[t]_\times = \begin{bmatrix} 0 & 15 & 0 \\ -15 & 0 & 120 \\ 0 & -120 & 0 \end{bmatrix},
\qquad
E = [t]_\times R = \begin{bmatrix} 0 & 15 & 0 \\ -35.6099 & 0 & 115.5722 \\ 0 & -120 & 0 \end{bmatrix}.
$$

**Check.** With $\hat x_2 = P_2/\lambda_2$ and $F = K_2^{-\top} E\,K_1^{-1}$,

$$
\hat x_2^\top E\,\hat x_1 = 0 \quad(\text{exact}), \qquad
x_2^\top F\,x_1 \approx 7\times 10^{-15}\ (\text{machine zero}),
$$

confirming $(u_2, v_2)$ lies on the epipolar line $F x_1$ of $(u_1, v_1)$.
