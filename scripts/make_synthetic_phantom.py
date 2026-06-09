"""Generate a small synthetic voxel phantom for offline testing of the Geant4
voxel-phantom path, without needing MNI152 or nibabel.

Writes:
  * tissue_labels.mha  (LPS, X-fastest) via metaimage_io
  * material_map.csv   (the frozen 5-class brain map)
  * tissue_labels.nii.gz (only if nibabel is importable)

Anatomy: an ellipsoidal head -- background air (0), a cortical-bone shell (4),
and CSF (1) / gray matter (2) / white matter (3) nested inside. This mirrors the
real 5-class MNI152 assignment so the C++ G4PhantomParameterisation path can be
exercised end-to-end once built.

Usage:
  python scripts/make_synthetic_phantom.py --out-dir data/derived/synthetic
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from g4brainatlasdose.metaimage_io import write_metaimage  # noqa: E402

# label -> (material_id, density_g_cm3). Unique material_id per row (contract).
MATERIAL_MAP = [
    (0, "G4_AIR", 0.001205, "Background air; NIST / ICRU-44"),
    (1, "G4_CSF", 1.007, "Cerebrospinal fluid; Woodard and White 1986"),
    (2, "G4_GRAY_MATTER", 1.045, "Gray matter; Woodard and White 1986"),
    (3, "G4_WHITE_MATTER", 1.041, "White matter; Woodard and White 1986"),
    (4, "G4_BONE_CORTICAL_ICRP", 1.850, "Cortical bone; ICRU-44 / ICRP-89"),
]


def build_labels(nx, ny, nz):
    """Nested ellipsoids -> labels [ix, iy, iz]."""
    labels = np.zeros((nx, ny, nz), dtype=np.int16)
    ci, cj, ck = (nx - 1) / 2, (ny - 1) / 2, (nz - 1) / 2
    ii, jj, kk = np.meshgrid(
        np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    # normalized radius
    r = np.sqrt(((ii - ci) / (0.48 * nx)) ** 2
                + ((jj - cj) / (0.48 * ny)) ** 2
                + ((kk - ck) / (0.48 * nz)) ** 2)
    labels[r <= 1.00] = 4          # bone shell (outermost)
    labels[r <= 0.90] = 1          # CSF just inside skull
    labels[r <= 0.85] = 2          # gray matter
    labels[r <= 0.65] = 3          # white matter core
    # everything with r > 1 stays 0 (air)
    return labels


def write_material_map(path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["label", "material_id", "density_g_cm3", "description"])
        for row in MATERIAL_MAP:
            w.writerow(row)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data/derived/synthetic")
    ap.add_argument("--dims", type=int, nargs=3, default=[30, 36, 30])
    ap.add_argument("--spacing-mm", type=float, default=2.0)
    args = ap.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    nx, ny, nz = args.dims
    s = args.spacing_mm
    labels = build_labels(nx, ny, nz)

    # Centre the phantom at the world origin (LPS): offset of voxel (0,0,0).
    offset = (-(nx - 1) / 2 * s, -(ny - 1) / 2 * s, -(nz - 1) / 2 * s)
    write_metaimage(out / "tissue_labels.mha", labels,
                    (s, s, s), offset, np.diag([-1.0, -1.0, 1.0]))
    write_material_map(out / "material_map.csv")

    try:
        import nibabel as nib
        # RAS affine: flip LPS->RAS for the NIfTI sibling.
        aff = np.diag([s, s, s, 1.0])
        aff[0, 0], aff[1, 1] = -s, -s  # store as a plausible RAS-ish affine
        nib.save(nib.Nifti1Image(labels, np.diag([s, s, s, 1.0])),
                 str(out / "tissue_labels.nii.gz"))
        nii = "tissue_labels.nii.gz"
    except ImportError:
        nii = "(skipped: nibabel not installed)"

    present = sorted(int(v) for v in np.unique(labels))
    print("wrote:")
    print("  ", out / "tissue_labels.mha", "dims", (nx, ny, nz), "labels", present)
    print("  ", out / "material_map.csv")
    print("  ", nii)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
