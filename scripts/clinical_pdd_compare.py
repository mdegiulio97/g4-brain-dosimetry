"""Clinical 6 MV PDD check: cited Mohan6 spectrum + inverse-square -> BJR-25.

Two findings this script demonstrates:

1. SPECTRUM is not the problem. The cited Mohan6 spectrum (mean ~1.9 MeV) and the
   analytic make_6mv_spectrum.py beam give nearly the same depth-dose in our
   geometry -> the +8..12 pp excess at depth vs clinical BJR-25 is NOT a spectrum
   artefact.

2. GEOMETRY is. Our source is a PARALLEL plane beam (no divergence); clinical PDD
   is from a DIVERGENT point source at SSD 100 cm. The inverse-square factor
       ISF(d) = ((SSD + dmax) / (SSD + d))^2
   steepens the clinical curve. Applying it to the parallel-beam MC reproduces the
   cited BJR-25 landmarks (esp. D10).

Reference: data/reference/pdd_6MV_BJR25_landmarks.csv (cited BJR-25 landmark values).
"""
from __future__ import annotations

import numpy as np

from g4score_io import central_axis_pdd, read_score_dump

MESH_HALFZ_CM = 15.0
NZ = 300
DZ = 2.0 * MESH_HALFZ_CM / NZ
SSD_CM = 100.0


def load_pdd(path):
    dose, shape = read_score_dump(path)
    pdd = central_axis_pdd(dose)
    depth = (np.arange(shape[2]) + 0.5) * DZ
    return depth, pdd


def smooth(y, w=5):
    return np.convolve(y, np.ones(w) / w, mode="same")


def at(depth, y, d):
    return float(y[min(int(d / DZ), len(y) - 1)])


def load_landmarks(path):
    d, p = [], []
    with open(path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#") or ln.lower().startswith("depth"):
                continue
            parts = ln.split(",")
            d.append(float(parts[0]))
            p.append(float(parts[1]))
    return np.array(d), np.array(p)


def main():
    base = "reports/benchmark_mc"
    depth, moh = load_pdd(base + "/pdd_mohan6.txt")
    moh_s = smooth(moh)
    dmax = depth[int(np.argmax(moh_s))]

    # Finding 1: cited Mohan6 vs analytic, both parallel beam.
    print("=== Finding 1: spectrum is not the cause (parallel-beam PDD) ===")
    try:
        _, ana = load_pdd(base + "/pdd_6MV.txt")
        ana_s = smooth(ana)
        print("{:>7} {:>12} {:>12} {:>10}".format("depth", "Mohan6%", "analytic%", "diff_pp"))
        for d in [5, 10, 15, 20]:
            a = 100 * at(depth, moh_s, d) / moh_s.max()
            b = 100 * at(depth, ana_s, d) / ana_s.max()
            print("{:>6.0f}c {:>12.1f} {:>12.1f} {:>+10.1f}".format(d, a, b, a - b))
    except Exception as e:
        print("  (analytic curve unavailable: {})".format(e))

    # Finding 2: apply inverse-square to get the clinical SSD-100 PDD.
    isf = ((SSD_CM + dmax) / (SSD_CM + depth)) ** 2
    clin = moh_s * isf
    clin = clin / clin[int(np.argmax(clin))]  # renormalise to its own dmax

    ref_d, ref_p = load_landmarks("data/reference/pdd_6MV_BJR25_landmarks.csv")
    print("\n=== Finding 2: Mohan6 + inverse-square (SSD 100) vs cited BJR-25 ===")
    print("dmax = {:.2f} cm".format(dmax))
    print("{:>7} {:>14} {:>14} {:>12} {:>10}".format(
        "depth", "parallel%", "clinical%", "BJR-25%", "diff_pp"))
    for d, rp in zip(ref_d, ref_p):
        par = 100 * at(depth, moh_s, d) / moh_s.max()
        cl = 100 * at(depth, clin, d)
        print("{:>6.1f}c {:>14.1f} {:>14.1f} {:>12.1f} {:>+10.1f}".format(
            d, par, cl, rp, cl - rp))

    # Headline number: D10 clinical vs cited BJR-25 66.8%.
    d10 = 100 * at(depth, clin, 10.0)
    print("\nD10 clinical = {:.1f}%  vs BJR-25 66.8%  (diff {:+.1f} pp)".format(
        d10, d10 - 66.8))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
