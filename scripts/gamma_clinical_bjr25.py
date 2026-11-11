"""Formal full-curve gamma(2%/2mm): clinical 6 MV MC vs dense BJR-25 reference.

Pipeline:
  Mohan6 cited-spectrum dump (parallel beam)
    -> central-axis PDD
    -> inverse-square to SSD 100 cm  (ISF = ((SSD+dmax)/(SSD+d))^2)
    -> light smoothing (1x1->4x4 wide column still has per-bin noise)
  vs data/reference/pdd_6MV_BJR25.csv (dense BJR-25 reconstruction, cited anchors).

Reports the gamma(2%/2mm) pass rate over [dmax, 25 cm] -- the Stage-1 acceptance
criterion. Both curves normalised to their own maximum.
"""
from __future__ import annotations

import argparse

import numpy as np

from g4score_io import central_axis_pdd, read_score_dump

MESH_HALFZ_CM = 15.0
NZ = 300
DZ = 2.0 * MESH_HALFZ_CM / NZ
SSD_CM = 100.0


def load_reference(path):
    d, p = [], []
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#") or ln.lower().startswith("depth"):
                continue
            a, b = ln.split(",")[:2]
            d.append(float(a))
            p.append(float(b))
    d = np.array(d)
    p = np.array(p)
    return d, p / p.max()


def gamma_1d(ref_d, ref_D, mc_d, mc_D, dta_cm, dose_tol):
    g = np.empty_like(ref_d)
    for n, (d, D) in enumerate(zip(ref_d, ref_D)):
        dd = (mc_d - d) / dta_cm
        dD = (mc_D - D) / dose_tol
        g[n] = np.sqrt(dd * dd + dD * dD).min()
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mc-dump", default="reports/benchmark_mc/pdd_mohan6.txt")
    ap.add_argument("--reference", default="data/reference/pdd_6MV_BJR25.csv")
    ap.add_argument("--dta-mm", type=float, default=2.0)
    ap.add_argument("--dose-tol", type=float, default=0.02)
    ap.add_argument("--range-cm", type=float, default=25.0)
    ap.add_argument("--threshold", type=float, default=0.95)
    ap.add_argument("--smooth", type=int, default=5)
    ap.add_argument("--no-isf", action="store_true",
                    help="beam already divergent (SSD modelled): skip post-hoc "
                         "inverse-square so divergence is not double-counted")
    args = ap.parse_args(argv)

    dose, shape = read_score_dump(args.mc_dump)
    pdd = central_axis_pdd(dose)
    if args.smooth > 1:
        pdd = np.convolve(pdd, np.ones(args.smooth) / args.smooth, mode="same")
    depth = (np.arange(shape[2]) + 0.5) * DZ
    dmax = depth[int(np.argmax(pdd))]
    if args.no_isf:
        clin = pdd / pdd.max()
    else:
        isf = ((SSD_CM + dmax) / (SSD_CM + depth)) ** 2
        clin = pdd * isf
        clin = clin / clin.max()

    ref_d, ref_D = load_reference(args.reference)

    # Evaluate gamma at each reference point over [dmax, range], searching all MC.
    mask = (ref_d >= dmax) & (ref_d <= args.range_cm)
    g = gamma_1d(ref_d[mask], ref_D[mask], depth, clin,
                 args.dta_mm / 10.0, args.dose_tol)
    pass_rate = float((g <= 1.0).mean())

    print("Clinical 6 MV gamma({:.0f}%/{:.0f}mm) over [{:.2f}, {:.1f}] cm".format(
        args.dose_tol * 100, args.dta_mm, dmax, args.range_cm))
    print("  MC: Mohan6 cited spectrum, {}".format(
        "divergent point source (SSD {:.0f}, modelled)".format(SSD_CM)
        if args.no_isf else
        "parallel beam + post-hoc inverse-square (SSD {:.0f})".format(SSD_CM)))
    print("  reference points: {}".format(int(mask.sum())))
    print("  pass rate       : {:.1%}  (threshold {:.0%})".format(
        pass_rate, args.threshold))
    print("  gamma mean/max  : {:.3f} / {:.3f}".format(g.mean(), g.max()))
    print("\nRESULT: {}".format("PASS" if pass_rate >= args.threshold else "FAIL"))
    return 0 if pass_rate >= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
