"""Parse Geant4 command-based-scoring dumps into numpy arrays.

The dump has 5 data columns per voxel (verified against real dumps):
``ix iy iz  Sum(value)[Gy]  Sum(value^2)  entry(N)``. ``read_score_dump`` returns
just ``(dose, shape)`` for the many callers that only need dose;
``read_score_dump_full`` additionally returns the ``Sum(value^2)`` and ``N``
arrays needed for Monte Carlo statistical uncertainty.

MC uncertainty (history-by-history estimator; N = number of scoring events, NOT
hits -- verified empirically: doubling primaries doubles N and Sum(value), and the
relative error scales as 1/sqrt(N)). Per voxel the relative standard error of the
accumulated dose ``s = Sum(x)`` is

    sigma_s / s = sqrt( (N*Sum(x^2) - s^2) / (N-1) ) / s        (N >= 2, s > 0)

Older 4-column dumps (dose only) are tolerated: ``sumsq``/``n`` come back as NaN,
and the uncertainty helpers then yield NaN.

Pure-numpy; usable both inside the Docker image and in the repo env.
"""
from __future__ import annotations

from collections import namedtuple

import numpy as np

# dose[i,j,k]=Sum(x); sumsq[i,j,k]=Sum(x^2); n[i,j,k]=entry count. Backward note:
# callers that do `dose, shape = read_score_dump(...)` are unaffected -- that
# function still returns a 2-tuple; the full parser is a separate entry point.
ScoreDump = namedtuple("ScoreDump", ["dose", "shape", "sumsq", "n"])


def _parse_rows(path):
    """Return index lists + (dose, sumsq, n) value lists. sumsq/n hold NaN/-1
    for 4-column dumps that lack them."""
    idx_i, idx_j, idx_k = [], [], []
    vals, sqs, ns = [], [], []
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").split()
            if len(parts) < 4:
                continue
            try:
                i, j, k = int(parts[0]), int(parts[1]), int(parts[2])
                v = float(parts[3])
            except ValueError:
                continue
            q = float(parts[4]) if len(parts) > 4 else float("nan")
            nn = int(float(parts[5])) if len(parts) > 5 else -1
            idx_i.append(i); idx_j.append(j); idx_k.append(k)
            vals.append(v); sqs.append(q); ns.append(nn)
    if not vals:
        raise ValueError("no data rows parsed from {}".format(path))
    return idx_i, idx_j, idx_k, vals, sqs, ns


def read_score_dump(path):
    """Return (dose, shape) with dose a float64 array indexed [ix, iy, iz].

    Missing voxels (not present in the dump) are left as 0.0. Kept as a 2-tuple
    for backward compatibility with all existing callers.
    """
    ii, jj, kk, vals, _sqs, _ns = _parse_rows(path)
    nx, ny, nz = max(ii) + 1, max(jj) + 1, max(kk) + 1
    dose = np.zeros((nx, ny, nz), dtype=np.float64)
    dose[np.array(ii), np.array(jj), np.array(kk)] = np.array(vals)
    return dose, (nx, ny, nz)


def read_score_dump_full(path):
    """Return ScoreDump(dose, shape, sumsq, n).

    ``sumsq`` is Sum(value^2) per voxel (NaN where absent), ``n`` the entry count
    per voxel (float array; NaN where absent) -- both needed for MC uncertainty.
    """
    ii, jj, kk, vals, sqs, ns = _parse_rows(path)
    ai, aj, ak = np.array(ii), np.array(jj), np.array(kk)
    nx, ny, nz = ai.max() + 1, aj.max() + 1, ak.max() + 1
    dose = np.zeros((nx, ny, nz), dtype=np.float64)
    sumsq = np.full((nx, ny, nz), np.nan, dtype=np.float64)
    n = np.full((nx, ny, nz), np.nan, dtype=np.float64)
    dose[ai, aj, ak] = np.array(vals)
    sumsq[ai, aj, ak] = np.array(sqs)
    nvals = np.array(ns, dtype=float)
    nvals[nvals < 0] = np.nan
    n[ai, aj, ak] = nvals
    return ScoreDump(dose, (nx, ny, nz), sumsq, n)


def voxel_rel_unc(sumx, sumx2, n):
    """Per-voxel relative statistical uncertainty sigma_s/s (elementwise).

    Returns NaN where n < 2, sumx <= 0, or sumsq/n are NaN. Accepts scalars or
    arrays. Uses sigma_s = sqrt((n*Sum(x^2) - sumx^2)/(n-1)); rel = sigma_s/sumx.
    """
    sumx = np.asarray(sumx, dtype=float)
    sumx2 = np.asarray(sumx2, dtype=float)
    n = np.asarray(n, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        var_s = (n * sumx2 - sumx * sumx) / (n - 1.0)
        var_s = np.where(var_s < 0, 0.0, var_s)  # guard tiny negative from rounding
        rel = np.sqrt(var_s) / sumx
    bad = ~np.isfinite(n) | (n < 2) | ~np.isfinite(sumx2) | (sumx <= 0)
    return np.where(bad, np.nan, rel)


def central_axis_pdd(dose):
    """Central-axis depth-dose: average over the central lateral voxels per depth.

    Returns a 1-D array over the last axis (beam direction z), normalised to its
    maximum (percent depth dose / 100).
    """
    nx, ny, nz = dose.shape
    cx, cy = nx // 2, ny // 2
    # average a small 2x2-ish central window to reduce noise
    x0, x1 = max(cx - 1, 0), min(cx + 2, nx)
    y0, y1 = max(cy - 1, 0), min(cy + 2, ny)
    pdd = dose[x0:x1, y0:y1, :].mean(axis=(0, 1))
    m = pdd.max()
    return pdd / m if m > 0 else pdd


def mean_dose_in_box(dose, i0, i1, j0, j1, k0, k1):
    """Mean dose over a voxel-index box [i0:i1, j0:j1, k0:k1]."""
    region = dose[i0:i1, j0:j1, k0:k1]
    return float(region.mean()) if region.size else float("nan")


def mean_dose_in_mask(dose, mask):
    """Mean dose over a boolean voxel mask."""
    vals = dose[mask]
    return float(vals.mean()) if vals.size else float("nan")


def _region_mean_and_sigma(dose, sumsq, n, sel):
    """Region mean of the accumulated dose + its MC statistical sigma (absolute),
    given a boolean/index selection. Voxels treated as independent:
        D_R = mean_v s_v ;  sigma(D_R) = (1/M) sqrt( sum_v sigma_s_v^2 )
    where sigma_s_v^2 = (n*Sum(x^2) - s^2)/(n-1). NaN-sigma voxels drop from the
    variance sum (still counted in the mean).
    """
    s = dose[sel]
    q = sumsq[sel]
    nn = n[sel]
    m = s.size
    if m == 0:
        return float("nan"), float("nan")
    mean = float(s.mean())
    with np.errstate(invalid="ignore", divide="ignore"):
        var_s = (nn * q - s * s) / (nn - 1.0)
    var_s = np.where(np.isfinite(var_s) & (var_s > 0), var_s, 0.0)
    sigma = float(np.sqrt(var_s.sum()) / m)
    return mean, sigma


def mean_dose_in_box_with_unc(dump, i0, i1, j0, j1, k0, k1):
    """(mean_Gy, sigma_Gy) over a voxel box, from a ScoreDump (MC uncertainty)."""
    sel = np.zeros(dump.dose.shape, dtype=bool)
    sel[i0:i1, j0:j1, k0:k1] = True
    return _region_mean_and_sigma(dump.dose, dump.sumsq, dump.n, sel)


def mean_dose_in_mask_with_unc(dump, mask):
    """(mean_Gy, sigma_Gy) over a boolean voxel mask, from a ScoreDump."""
    return _region_mean_and_sigma(dump.dose, dump.sumsq, dump.n, mask)


def ratio_with_unc(a_mean, a_sig, b_mean, b_sig):
    """Ratio R=a/b and its sigma from two INDEPENDENT runs (no covariance):
        sigma_R/R = sqrt( (a_sig/a_mean)^2 + (b_sig/b_mean)^2 ).
    Returns (R, sigma_R)."""
    if b_mean == 0 or not np.isfinite(b_mean):
        return float("nan"), float("nan")
    r = a_mean / b_mean
    ra = a_sig / a_mean if a_mean else float("nan")
    rb = b_sig / b_mean if b_mean else float("nan")
    rel = float(np.sqrt(ra * ra + rb * rb))
    return float(r), float(abs(r) * rel)
