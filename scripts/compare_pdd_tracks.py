"""Compare Stage-1 PDD tracks A and B.

Track A (mono-6 MeV, independent-MC cross-check): the same pure-water benchmark
run with three independent EM physics models (option4, Livermore, Penelope). They
use different cross-section datasets/algorithms, so agreement is strong evidence
the transport is correct -- an independent MC "reference" with no external data.

Track B (representative 6 MV spectrum): the clinically-shaped beam. Compared against
TEXTBOOK 6 MV PDD landmarks (10x10 cm, SSD 100 cm; e.g. Khan, The Physics of
Radiation Therapy) -- representative, NOT a cited commissioning table. A formal
gate still needs a measured/BJR-25 PDD.

Robust readouts: the 1x1 cm scoring column is noisy per bin, so depth landmarks are
read off a 5-bin moving average; the tail attenuation uses a least-squares slope.
"""
from __future__ import annotations

import os

import numpy as np

from g4score_io import central_axis_pdd, read_score_dump

MESH_HALFZ_CM = 15.0
NZ = 300
DZ = 2.0 * MESH_HALFZ_CM / NZ  # 0.1 cm

# Representative textbook 6 MV PDD landmarks (10x10, SSD 100). Not a cited table.
CLINICAL_6MV = {1.5: 100.0, 5.0: 86.5, 10.0: 66.5, 15.0: 49.0, 20.0: 38.0}


def load_pdd(path):
    dose, shape = read_score_dump(path)
    pdd = central_axis_pdd(dose)
    depth = (np.arange(shape[2]) + 0.5) * DZ
    return depth, pdd


def smooth(y, w=5):
    k = np.ones(w) / w
    return np.convolve(y, k, mode="same")


def at_depth(depth, pdd_s, d):
    k = min(int(d / DZ), len(pdd_s) - 1)
    return 100.0 * pdd_s[k]


def fit_mu_eff(depth, pdd, d_lo=5.0, d_hi=20.0):
    m = (depth >= d_lo) & (depth <= d_hi) & (pdd > 0)
    A = np.vstack([depth[m], np.ones(m.sum())]).T
    slope, _ = np.linalg.lstsq(A, np.log(pdd[m]), rcond=None)[0]
    return -slope


def dmax_of(depth, pdd_s):
    return depth[int(np.argmax(pdd_s))]


def main():
    base = "reports/benchmark_mc"
    print("=" * 70)
    print("TRACK A -- mono-6 MeV cross-physics-list (independent MC reference)")
    print("=" * 70)
    a_files = [("option4", "pdd_6MeV_option4.txt"),
               ("livermore", "pdd_6MeV_livermore.txt"),
               ("penelope", "pdd_6MeV_penelope.txt")]
    curves = {}
    print("{:<10} {:>10} {:>14}".format("physics", "dmax_cm", "mu_eff_/cm"))
    for name, fn in a_files:
        p = os.path.join(base, fn)
        if not os.path.exists(p):
            print("{:<10} {:>10}".format(name, "(missing)"))
            continue
        depth, pdd = load_pdd(p)
        pdd_s = smooth(pdd)
        curves[name] = pdd_s
        print("{:<10} {:>10.2f} {:>14.4f}".format(
            name, dmax_of(depth, pdd_s), fit_mu_eff(depth, pdd)))
    if len(curves) >= 2:
        ref = curves["option4"] if "option4" in curves else list(curves.values())[0]
        print("\nMax |Delta PDD| vs option4 over [2,25] cm (smoothed):")
        lo, hi = int(2 / DZ), int(25 / DZ)
        for name, c in curves.items():
            if name == "option4":
                continue
            d = 100.0 * np.max(np.abs(c[lo:hi] - ref[lo:hi]))
            print("  {:<10}: {:.2f} %  ->  {}".format(
                name, d, "AGREE (<2%)" if d < 2.0 else "CHECK"))

    print()
    print("=" * 70)
    print("TRACK B -- representative 6 MV spectrum vs textbook 6 MV landmarks")
    print("=" * 70)
    p = os.path.join(base, "pdd_6MV.txt")
    if not os.path.exists(p):
        print("(pdd_6MV.txt missing)")
        return 0
    depth, pdd = load_pdd(p)
    pdd_s = smooth(pdd)
    print("MC dmax depth: {:.2f} cm   (clinical 6 MV ~1.5 cm)".format(
        dmax_of(depth, pdd_s)))
    print("{:>8} {:>12} {:>14} {:>10}".format(
        "depth", "MC_pdd%", "textbook%", "diff_pp"))
    for d in sorted(CLINICAL_6MV):
        mc = at_depth(depth, pdd_s, d)
        ref = CLINICAL_6MV[d]
        # renormalise MC to its own dmax already done; compare shape
        print("{:>7.1f}c {:>12.1f} {:>14.1f} {:>+10.1f}".format(
            d, mc, ref, mc - ref))
    print("\n(Track B difference vs textbook indicates how clinical the synthetic")
    print(" spectrum is; a cited PDD is still required for formal acceptance.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
