"""Parse Geant4 command-based-scoring dumps into numpy arrays.

PENDING VERIFICATION: the exact column layout of /score/dumpQuantityToFile is
checked defensively but has not been exercised against a real Geant4 build on
this machine. The reader tolerates comma- or space-separated `ix iy iz value`
rows and `#`-prefixed header lines, and infers the grid shape from the maximum
indices. Confirm against the first real dump and tighten if needed.

Pure-numpy; usable both inside the Docker image and in the repo env.
"""
from __future__ import annotations

import numpy as np


def read_score_dump(path):
    """Return (dose, shape) with dose a float64 array indexed [ix, iy, iz].

    Missing voxels (not present in the dump) are left as 0.0.
    """
    idx_i, idx_j, idx_k, vals = [], [], [], []
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
            idx_i.append(i)
            idx_j.append(j)
            idx_k.append(k)
            vals.append(v)

    if not vals:
        raise ValueError("no data rows parsed from {}".format(path))

    nx = max(idx_i) + 1
    ny = max(idx_j) + 1
    nz = max(idx_k) + 1
    dose = np.zeros((nx, ny, nz), dtype=np.float64)
    dose[np.array(idx_i), np.array(idx_j), np.array(idx_k)] = np.array(vals)
    return dose, (nx, ny, nz)


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
