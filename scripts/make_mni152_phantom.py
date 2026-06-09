"""Build a REAL MNI152 brain tissue-label phantom from ICBM152 tissue priors.

Fetches the ICBM152 2009 GM/WM/CSF probability maps via nilearn (cached under the
nilearn data dir), block-downsamples to a tractable voxel size, assigns each voxel
to the dominant tissue, and writes a tissue-label NIfTI (RAS) + a matching
material_map.csv. Then run build_tissue_labels_mha.py on the NIfTI to get the LPS
.mha the Geant4 voxel_phantom reads.

Labels: 0 air/background, 1 CSF, 2 gray matter, 3 white matter. (No skull bone:
the ICBM152 tissue priors are brain GM/WM/CSF; a bone class needs a separate skull
segmentation.)

Usage:
  python scripts/make_mni152_phantom.py --factor 3 --out-dir data/derived/mni152
  python scripts/build_tissue_labels_mha.py \
      --labels data/derived/mni152/tissue_labels.nii.gz \
      --material-map data/derived/mni152/material_map.csv \
      --out data/derived/mni152/tissue_labels.mha
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import nibabel as nib


def block_reduce_mean(a, f):
    nx, ny, nz = (s - s % f for s in a.shape)
    a = a[:nx, :ny, :nz]
    return a.reshape(nx // f, f, ny // f, f, nz // f, f).mean(axis=(1, 3, 5))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--factor", type=int, default=3, help="downsample factor")
    ap.add_argument("--bg-thresh", type=float, default=0.5,
                    help="min summed tissue prob to count as brain (else air)")
    ap.add_argument("--out-dir", default="data/derived/mni152")
    args = ap.parse_args(argv)

    from nilearn.datasets import fetch_icbm152_2009
    print("fetching ICBM152 2009 tissue priors (cached after first run)...")
    icbm = fetch_icbm152_2009()

    csf_img = nib.load(icbm["csf"])
    gm = nib.load(icbm["gm"]).get_fdata()
    wm = nib.load(icbm["wm"]).get_fdata()
    csf = csf_img.get_fdata()
    affine = csf_img.affine
    print("native grid {}, spacing {} mm".format(
        csf.shape, np.round(np.abs(np.diag(affine))[:3], 2)))

    f = args.factor
    csf, gm, wm = (block_reduce_mean(x, f) for x in (csf, gm, wm))
    stack = np.stack([csf, gm, wm], axis=-1)        # index 0,1,2 -> labels 1,2,3
    total = stack.sum(axis=-1)
    labels = np.where(total >= args.bg_thresh, stack.argmax(axis=-1) + 1, 0)
    labels = labels.astype(np.int16)

    # Downsampled affine: scale the direction/scale block by f (origin kept).
    new_affine = affine.copy()
    new_affine[:3, :3] = affine[:3, :3] * f

    os.makedirs(args.out_dir, exist_ok=True)
    nii_path = os.path.join(args.out_dir, "tissue_labels.nii.gz")
    nib.save(nib.Nifti1Image(labels, new_affine), nii_path)

    mat_path = os.path.join(args.out_dir, "material_map.csv")
    with open(mat_path, "w") as fh:
        fh.write("label,material_id,density_g_cm3,description\n")
        fh.write("0,G4_AIR,0.001205,Background air; NIST / ICRU-44\n")
        fh.write("1,G4_CSF,1.007,Cerebrospinal fluid; Woodard and White 1986\n")
        fh.write("2,G4_GRAY_MATTER,1.045,Gray matter; Woodard and White 1986\n")
        fh.write("3,G4_WHITE_MATTER,1.041,White matter; Woodard and White 1986\n")

    counts = {int(l): int((labels == l).sum()) for l in np.unique(labels)}
    print("downsampled grid {}, spacing {} mm".format(
        labels.shape, np.round(np.abs(np.diag(new_affine))[:3], 2)))
    print("label voxel counts:", counts)
    print("wrote", nii_path)
    print("wrote", mat_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
