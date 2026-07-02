"""Embed a heterogeneity insert inside the REAL MNI152
anatomy, not a bare water box.

Takes the MNI152 tissue-label .mha + material_map.csv, relabels a small box of
brain PARENCHYMA (GM/WM, optionally CSF) to a new label, and writes an extended
.mha + material_map.csv. The grid (DimSize/spacing/offset/direction) is
unchanged -- only voxel labels change -- so the existing run_mni152 scoring
macro (mesh 65x77x63) and run.config apply verbatim; only material_map + .mha
paths differ.

This places a heterogeneity inside real anatomy, with the surrounding
scatter and heterogeneity, instead of in a bare water box.




Materials (CSV density is authoritative -- MaterialMap passes it as an override):
  air cavity     -> G4_AIR 0.001205 g/cm3
  calcification  -> G4_BONE_CORTICAL_ICRP 1.850 g/cm3

Usage:
  python scripts/add_insert_to_mni152.py --preset air   --out-dir data/derived/mni152_insert_air
  python scripts/add_insert_to_mni152.py --preset calc  --out-dir data/derived/mni152_insert_calc
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from g4brainatlasdose.metaimage_io import read_metaimage, write_metaimage  # noqa: E402
from g4brainatlasdose.contracts import load_material_map_csv  # noqa: E402

PRESETS = {
    "air":  dict(material="G4_AIR", density=0.001205,
                 desc="Air cavity insert"),
    "calc": dict(material="G4_BONE_CORTICAL_ICRP", density=1.850,
                 desc="Calcification insert; ICRU-44 cortical bone proxy"),
}
PARENCHYMA_DEFAULT = (2, 3)  # GM, WM


def parse_header_geometry(hdr):
    nx, ny, nz = (int(v) for v in hdr["DimSize"].split())
    spacing = tuple(float(v) for v in hdr["ElementSpacing"].split())
    offset = tuple(float(v) for v in hdr["Offset"].split())
    direction = np.array([float(v) for v in hdr["TransformMatrix"].split()]).reshape(3, 3)
    return (nx, ny, nz), spacing, offset, direction


def box_slices(shape, center, half):
    sl = []
    for c, h, n in zip(center, half, shape):
        sl.append(slice(max(c - h, 0), min(c + h + 1, n)))
    return tuple(sl)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-mha", default="data/derived/mni152/tissue_labels.mha")
    ap.add_argument("--in-csv", default="data/derived/mni152/material_map.csv")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="air")
    ap.add_argument("--label", type=int, default=None,
                    help="new label value (default: max existing + 1)")
    ap.add_argument("--center", type=int, nargs=3, default=None,
                    help="insert centre voxel i j k (default: grid centre)")
    ap.add_argument("--half", type=int, nargs=3, default=(2, 2, 2),
                    help="insert half-size in voxels (i j k); default 2 -> ~15 mm cube")
    ap.add_argument("--in-tissues", type=int, nargs="+", default=list(PARENCHYMA_DEFAULT),
                    help="only relabel voxels currently in these labels (embed in tissue)")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)

    labels, hdr = read_metaimage(args.in_mha)
    labels = labels.astype(np.int16)
    shape, spacing, offset, direction = parse_header_geometry(hdr)
    if labels.shape != shape:
        raise SystemExit("array shape {} != header DimSize {}".format(labels.shape, shape))

    center = tuple(args.center) if args.center else tuple(n // 2 for n in shape)
    new_label = args.label if args.label is not None else int(labels.max()) + 1
    preset = PRESETS[args.preset]

    sl = box_slices(shape, center, tuple(args.half))
    box = labels[sl]
    embed = np.isin(box, args.in_tissues)  # only carve into real tissue
    n_relabel = int(embed.sum())
    if n_relabel == 0:
        raise SystemExit("insert box at {} contains no target tissue {}; move --center"
                         .format(center, args.in_tissues))
    box[embed] = new_label
    labels[sl] = box

    os.makedirs(args.out_dir, exist_ok=True)
    out_mha = os.path.join(args.out_dir, "tissue_labels.mha")
    out_csv = os.path.join(args.out_dir, "material_map.csv")
    write_metaimage(out_mha, labels, spacing, offset, direction)

    # Extend the material map: copy the existing rows, append the insert row.
    rows = load_material_map_csv(args.in_csv)
    declared = {int(r["label"]) for r in rows}
    if new_label in declared:
        raise SystemExit("label {} already declared; choose another --label".format(new_label))
    shutil.copyfile(args.in_csv, out_csv)
    with open(out_csv, "a", encoding="utf-8") as fh:
        if not open(args.in_csv).read().endswith("\n"):
            fh.write("\n")
        fh.write("{},{},{:.6g},{}\n".format(
            new_label, preset["material"], preset["density"], preset["desc"]))

    # Validate: every present label is now declared.
    present = set(int(v) for v in np.unique(labels))
    missing = present - (declared | {new_label})
    if missing:
        raise SystemExit("labels present but undeclared after insert: {}".format(sorted(missing)))

    ci, cj, ck = center
    print("insert preset '{}' -> label {} ({} @ {} g/cm3)".format(
        args.preset, new_label, preset["material"], preset["density"]))
    print("  centre voxel {} half {} -> {} voxels relabelled (embedded in {})".format(
        center, tuple(args.half), n_relabel, args.in_tissues))
    print("  depth of centre along beam (k): {} voxels = {:.1f} mm".format(ck, ck * spacing[2]))
    print("  wrote {}".format(out_mha))
    print("  wrote {}".format(out_csv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
