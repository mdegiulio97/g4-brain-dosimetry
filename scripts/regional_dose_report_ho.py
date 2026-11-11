"""Regional dose report on the real MNI152 dose, by
Harvard-Oxford atlas region.

Glues the already-validated pieces together:
  * reports/mni152_mc/dose.txt  -- Geant4 command-based-scoring dump, indexed
    [ix,iy,iz] in the .mha copy-number order (X-fastest). Because the numpy
    RAS->LPS conversion in build_tissue_labels_mha.py preserves voxel INDICES
    (only the header world coords flip), dose[i,j,k] aligns index-for-index
    with tissue_labels.nii.gz[i,j,k]. Verified again here by a brain-mask guard.
  * data/derived/mni152/tissue_labels.nii.gz -- the reference RAS grid + affine
    (ICBM152 2009c, 65x77x63 @ 3 mm) the phantom was built on.
  * Harvard-Oxford cortical + subcortical maxprob atlases (nilearn, no FSL
    needed), resampled nearest-neighbour onto the reference grid.
  * g4brainatlasdose.analytics.compute_regional_dose -- the tested aggregator.

Writes one CSV per atlas + a combined markdown report.

Caveat (documented, not hidden): the phantom template is ICBM152 2009c
(MNI152NLin2009c) while Harvard-Oxford ships in FSL MNI152 (MNI152NLin6). The two
"MNI" spaces differ by ~1-2 mm; resample_to_img aligns them by world affine, good
enough for a 3 mm-voxel population-level report, not for paient-specific work.

Usage:
  python scripts/regional_dose_report_ho.py
  python scripts/regional_dose_report_ho.py --thr 25 --out-dir reports/mni152_regional
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from g4brainatlasdose.analytics import compute_regional_dose_mc  # noqa: E402
from g4score_io import read_score_dump_full  # noqa: E402

# Subcortical HO labels that are generic tissue envelopes (they blanket the whole
# hemisphere and would swamp the specific deep-gray structures we care about).
SUBCORTICAL_SKIP = {
    "Left Cerebral White Matter", "Right Cerebral White Matter",
    "Left Cerebral Cortex", "Right Cerebral Cortex",
    "Left Lateral Ventricle", "Right Lateral Ventricle",
}


def load_reference_grid(ref_nii):
    import nibabel as nib
    img = nib.load(str(ref_nii))
    labels = np.rint(np.asarray(img.dataobj)).astype(np.int16)
    return img, labels


def load_dose_aligned(dose_path, ref_shape):
    dump = read_score_dump_full(dose_path)
    if tuple(dump.shape) != tuple(ref_shape):
        raise SystemExit(
            "dose grid {} != reference grid {}: orientation/scoring mismatch, "
            "refusing to report".format(dump.shape, ref_shape))
    return dump


def fetch_ho(which, thr, ref_img):
    """Return (labels_on_ref_grid[i,j,k], {label:int -> name})."""
    from nilearn.datasets import fetch_atlas_harvard_oxford
    from nilearn.image import resample_to_img
    import nibabel as nib

    name = "{}-maxprob-thr{}-1mm".format(which, thr)
    atlas = fetch_atlas_harvard_oxford(name)
    maps = atlas.maps if hasattr(atlas.maps, "get_fdata") else nib.load(atlas.maps)
    res = resample_to_img(maps, ref_img, interpolation="nearest")
    arr = np.rint(np.asarray(res.dataobj)).astype(np.int32)

    labels_list = list(atlas.labels)  # index 0 == 'Background'
    names = {}
    for v in np.unique(arr):
        v = int(v)
        if v <= 0 or v >= len(labels_list):
            continue
        nm = labels_list[v]
        if which == "sub" and nm in SUBCORTICAL_SKIP:
            arr[arr == v] = 0  # drop generic envelopes
            continue
        names[v] = nm
    return arr, names


def alignment_guard(dose, brain_mask, atlas_arr, tag):
    """Sanity: atlas regions must sit inside the brain, and brain dose >> air."""
    d_brain = dose[brain_mask]
    d_air = dose[~brain_mask]
    mean_brain = float(d_brain.mean()) if d_brain.size else float("nan")
    mean_air = float(d_air.mean()) if d_air.size else float("nan")
    atlas_vox = atlas_arr > 0
    n_atlas = int(atlas_vox.sum())
    inside = int((atlas_vox & brain_mask).sum())
    frac_inside = inside / n_atlas if n_atlas else float("nan")
    print("  [{}] brain mean {:.3e} Gy vs air mean {:.3e} Gy (ratio {:.1f}x)".format(
        tag, mean_brain, mean_air, mean_brain / mean_air if mean_air else float("nan")))
    print("  [{}] atlas voxels inside brain mask: {}/{} = {:.1%}".format(
        tag, inside, n_atlas, frac_inside))
    if frac_inside < 0.7:
        print("  [{}] WARNING: <70% of atlas voxels fall in the brain -> possible "
              "misalignment / template mismatch".format(tag))
    return dict(mean_brain=mean_brain, mean_air=mean_air, frac_inside=frac_inside,
                ratio=mean_brain / mean_air if mean_air else float("nan"))


def region_table(dump, atlas_arr, names):
    df = compute_regional_dose_mc(dump.dose, dump.sumsq, dump.n, atlas_arr,
                                  region_names=names)
    return df.sort_values("mean_dose_Gy", ascending=False).reset_index(drop=True)


def write_markdown(path, ctx):
    lines = []
    lines.append("# Regional dose report — MNI152 anatomy, Harvard-Oxford atlas\n")
    lines.append("Regional aggregation of the validated real-"
                 "MNI152 6 MeV dose (`reports/mni152_mc/dose.txt`, "
                 "{}) by Harvard-Oxford atlas region.\n".format(ctx["grid"]))
    lines.append("Pipeline: dose dump → align to `tissue_labels.nii.gz` grid → "
                 "resample HO (nilearn, nearest-neighbour) → "
                 "`compute_regional_dose_mc`. Each region mean carries its Monte "
                 "Carlo statistical uncertainty (± 1σ, from the per-voxel Sum(x²)/N "
                 "in the dump); `spatial std` is the separate biological spread "
                 "across the region's voxels.\n")
    for tag, title in (("cort", "Cortical (Harvard-Oxford cortical)"),
                       ("sub", "Subcortical / deep gray (Harvard-Oxford subcortical)")):
        g = ctx["guards"][tag]
        df = ctx["tables"][tag]
        lines.append("\n## {}\n".format(title))
        lines.append("Alignment guard: brain mean {:.3e} Gy vs air {:.3e} Gy "
                     "({:.1f}× ), {:.1%} of atlas voxels inside the brain mask.\n".format(
                         g["mean_brain"], g["mean_air"], g["ratio"], g["frac_inside"]))
        lines.append("{} regions scored. Top by mean dose "
                     "(mean ± MC stat. σ):\n".format(len(df)))
        lines.append("| region | mean (Gy) | MC σ (Gy) | MC rel σ | spatial std (Gy) | max (Gy) | n_vox |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for _, r in df.head(12).iterrows():
            std = "" if not np.isfinite(r["std_dose_Gy"]) else "{:.2e}".format(r["std_dose_Gy"])
            rel = "" if not np.isfinite(r["mc_rel_unc"]) else "{:.1%}".format(r["mc_rel_unc"])
            lines.append("| {} | {:.2e} | {:.2e} | {} | {} | {:.2e} | {} |".format(
                r["region_name"] or r["region_label"], r["mean_dose_Gy"],
                r["mc_unc_Gy"], rel, std, r["max_dose_Gy"], int(r["n_voxels"])))
    lines.append("\n## Caveats\n")
    lines.append("- **Template mismatch**: phantom is ICBM152 2009c "
                 "(MNI152NLin2009c); Harvard-Oxford is FSL MNI152 (MNI152NLin6). "
                 "Aligned by world affine (~1-2 mm residual). Population-level, not "
                 "patient-specific.")
    lines.append("- **Resolution**: 3 mm phantom voxels; small nuclei are a few "
                 "voxels. `spatial std` is NaN for single-voxel regions.")
    lines.append("- **MC σ vs spatial std**: `MC σ` is the statistical error on the "
                 "region-mean dose (shrinks as 1/√histories); `spatial std` is the "
                 "biological dose spread across the region (does not). They are "
                 "distinct — do not read `spatial std` as an error bar.")
    lines.append("- **Dose model**: relative regional dose from the 6 MeV run; "
                 "absolute Gy is per simulated primary, not calibrated MU.")
    lines.append("- Generic subcortical envelopes (cerebral WM/cortex, ventricles) "
                 "are dropped so deep-gray nuclei are not swamped.")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dose", default="reports/mni152_mc/dose.txt")
    ap.add_argument("--ref-nii", default="data/derived/mni152/tissue_labels.nii.gz")
    ap.add_argument("--thr", type=int, default=25)
    ap.add_argument("--out-dir", default="reports/mni152_regional")
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    ref_img, ref_labels = load_reference_grid(args.ref_nii)
    ref_shape = ref_labels.shape
    dump = load_dose_aligned(args.dose, ref_shape)
    brain_mask = ref_labels > 0
    print("reference grid {} | brain voxels {}".format(ref_shape, int(brain_mask.sum())))

    tables, guards = {}, {}
    for which in ("cort", "sub"):
        print("--- Harvard-Oxford {} (thr {}) ---".format(which, args.thr))
        atlas_arr, names = fetch_ho(which, args.thr, ref_img)
        guards[which] = alignment_guard(dump.dose, brain_mask, atlas_arr, which)
        df = region_table(dump, atlas_arr, names)
        tables[which] = df
        csv_path = os.path.join(args.out_dir, "regional_dose_{}.csv".format(which))
        df.to_csv(csv_path, index=False)
        print("  wrote {} ({} regions)".format(csv_path, len(df)))

    grid = "{}x{}x{} @ 3 mm".format(*ref_shape)
    md_path = os.path.join(args.out_dir, "REPORT.md")
    write_markdown(md_path, dict(tables=tables, guards=guards, grid=grid))
    print("wrote {}".format(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
