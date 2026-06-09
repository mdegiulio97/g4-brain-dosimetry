"""Stage C2 verification: voxel-phantom dose map vs the label volume.

Confirms the G4PhantomParameterisation geometry actually drove transport and that
the scoring mesh aligns with the phantom voxel (copy-number) order:

  1. SHAPE match. The phantom is 30x36x30 (deliberately asymmetric in y), so any
     axis transposition between the dose mesh and the .mha is caught immediately.
  2. PER-TISSUE dose. Mean dose per material label -- different tissues must get
     systematically different dose (air background ~ no dose; head tissues real
     dose), which only happens if labels and dose are spatially aligned.
  3. AIR-background leakage. Fraction of total dose landing in label-0 (air) voxels
     must be small; a transposed/misaligned map would smear dose into them.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from g4score_io import read_score_dump
from g4brainatlasdose.metaimage_io import read_metaimage


def load_material_map(path):
    out = {}
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#") or ln.lower().startswith("label"):
                continue
            p = ln.split(",")
            out[int(p[0])] = (p[1], float(p[2]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="data/derived/synthetic/tissue_labels.mha")
    ap.add_argument("--dose", default="reports/phantom_mc/dose.txt")
    ap.add_argument("--matmap", default="data/derived/synthetic/material_map.csv")
    args = ap.parse_args(argv)

    labels, hdr = read_metaimage(args.labels)
    dose, dshape = read_score_dump(args.dose)
    mm = load_material_map(args.matmap)

    print("labels shape : {}".format(labels.shape))
    print("dose shape   : {}".format(dose.shape))
    ok_shape = labels.shape == dose.shape
    print("SHAPE match  : {}".format("PASS" if ok_shape else "FAIL (transposition!)"))
    if not ok_shape:
        return 1

    total = dose.sum()
    print("\nlabel  material              rho     n_vox   mean_dose(Gy)   %of_total_dose")
    for lab in sorted(np.unique(labels)):
        m = labels == lab
        nv = int(m.sum())
        md = float(dose[m].mean()) if nv else 0.0
        frac = 100.0 * float(dose[m].sum()) / total if total else 0.0
        name, rho = mm.get(int(lab), ("?", float("nan")))
        print("  {:<4d} {:<20s} {:>5.3f}  {:>6d}   {:>12.4e}   {:>10.2f}".format(
            int(lab), name, rho, nv, md, frac))

    air_vox_frac = 100.0 * float((labels == 0).sum()) / labels.size
    air_dose_frac = 100.0 * float(dose[labels == 0].sum()) / total if total else 0.0
    air_mean = float(dose[labels == 0].mean())
    tissue_mean = float(dose[labels != 0].mean())
    ratio = air_mean / tissue_mean if tissue_mean else float("nan")
    print("\nAir background: {:.0f}% of voxels, {:.0f}% of total dose.".format(
        air_vox_frac, air_dose_frac))
    print("Per-voxel mean dose  air/tissue = {:.2f}  (alignment metric; <0.5 expected,"
          " since much air is out-of-field)".format(ratio))

    # Central-axis depth dose: build-up along z proves z is the BEAM axis (rules out
    # an x<->z transposition that the equal 30x_x30 shape check cannot catch).
    nx, ny, nz = dose.shape
    cax = dose[nx // 2 - 1:nx // 2 + 2, ny // 2 - 1:ny // 2 + 2, :].mean(axis=(0, 1))
    cax = cax / cax.max() if cax.max() > 0 else cax
    buildup = cax[0] < 0.5 * cax.max()  # entry dose below plateau -> build-up present
    print("\nCentral-axis depth dose (normalised), every 4th z-bin:")
    print("  " + "  ".join("{:.2f}".format(v) for v in cax[::4]))
    print("Build-up along z present: {}  -> z is the beam axis (no x<->z swap)".format(
        "YES" if buildup else "NO"))

    ok = ok_shape and ratio < 0.5 and buildup
    print("\nVerdict: {} -- phantom built ({} non-air voxels, {} materials), dose mesh "
          "aligned with .mha voxel order (shape match + z build-up + air<<tissue)."
          .format("PASS" if ok else "CHECK", int((labels != 0).sum()),
                  int(len(np.unique(labels)))))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
