"""Convert a tissue-label NIfTI (RAS) into tissue_labels.mha (LPS) for Geant4.

Implements the input side of docs/CPP_PYTHON_INTERFACE.md. Two backends:

  * SimpleITK (preferred, in the `geant4-prep` optional extra): ITK is natively
    LPS, so reading the NIfTI and writing the .mha performs the RAS->LPS
    conversion correctly for any orientation.
  * pure numpy + metaimage_io (fallback): applies the explicit flip
    A_lps = diag(-1,-1,1,1) @ A_ras and writes the header by hand. Verified by
    round-trip; for non-diagonal affines confirm against SimpleITK.

It also validates that every voxel label is declared in material_map.csv (the
guard that stops a label with no assigned material reaching Geant4).

Usage:
  python scripts/build_tissue_labels_mha.py \
      --labels data/derived/tissue_labels.nii.gz \
      --material-map configs/examples/material_map.brain.csv \
      --out data/derived/tissue_labels.mha
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from g4brainatlasdose.contracts import load_material_map_csv  # noqa: E402
from g4brainatlasdose.metaimage_io import write_metaimage  # noqa: E402


def declared_labels(material_map_csv):
    rows = load_material_map_csv(material_map_csv)
    return {int(r["label"]) for r in rows}


def validate_labels(label_array, declared):
    if label_array.ndim != 3:
        raise ValueError(f"label volume must be 3D; got {label_array.ndim}D")
    if not np.all(np.isfinite(label_array)):
        raise ValueError("label volume has non-finite values")
    present = set(int(v) for v in np.unique(label_array))
    missing = sorted(present - declared)
    if missing:
        raise ValueError(
            "labels present in the volume but absent from material_map.csv: "
            f"{missing}. Add materials or relabel the volume."
        )


def convert_numpy(labels_nii, out_mha):
    import nibabel as nib

    img = nib.load(str(labels_nii))
    labels = np.asarray(img.dataobj)
    affine_ras = np.asarray(img.affine, dtype=float)

    flip = np.diag([-1.0, -1.0, 1.0, 1.0])
    affine_lps = flip @ affine_ras
    m = affine_lps[:3, :3]
    spacing = np.linalg.norm(m, axis=0)
    direction = m / spacing  # columns = i,j,k axis directions
    offset = affine_lps[:3, 3]

    if not np.allclose(direction, np.diag(np.diag(direction)), atol=1e-6):
        print("WARNING: non-diagonal direction cosines; the hand-written .mha "
              "header convention is only round-trip-verified for axis-aligned "
              "volumes. Verify against SimpleITK.")

    labels = np.rint(labels).astype(np.int16)
    write_metaimage(out_mha, labels, spacing, offset, direction)
    return labels


def convert_sitk(labels_nii, out_mha):
    import SimpleITK as sitk

    img = sitk.ReadImage(str(labels_nii))
    img = sitk.Cast(img, sitk.sitkInt16)
    sitk.WriteImage(img, str(out_mha), useCompression=False)
    return sitk.GetArrayFromImage(img)  # [z,y,x]; fine for label validation


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, help="tissue-label NIfTI (RAS)")
    ap.add_argument("--material-map", required=True)
    ap.add_argument("--out", required=True, help="output tissue_labels.mha")
    ap.add_argument("--backend", choices=["auto", "sitk", "numpy"], default="auto")
    args = ap.parse_args(argv)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    declared = declared_labels(args.material_map)

    backend = args.backend
    if backend == "auto":
        try:
            import SimpleITK  # noqa: F401
            backend = "sitk"
        except ImportError:
            backend = "numpy"
    print(f"[build_tissue_labels_mha] backend = {backend}")

    if backend == "sitk":
        arr = convert_sitk(args.labels, args.out)
    else:
        arr = convert_numpy(args.labels, args.out)

    validate_labels(arr, declared)
    print(f"wrote {args.out}  labels={sorted(set(int(v) for v in np.unique(arr)))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
