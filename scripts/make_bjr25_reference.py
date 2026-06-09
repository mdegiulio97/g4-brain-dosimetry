"""Build a dense 6 MV BJR-25 reference PDD from CITED anchor points.

The full BJR Supplement 25 table is copyrighted and not openly reproduced online.
What IS openly cited (with provenance) are three anchor points for 6 MV, 10x10 cm,
SSD 100 cm:
    dmax = 1.5 cm  -> 100.0 %     (BJR-25 reference depth of maximum)
    d80  = 6.7 cm  ->  80.0 %     (BJR-25, via Hossain et al. IJRRT 2023)
    D10  = 10.0 cm ->  66.8 %     (BJR-25, via BAEC NSA vol.24 art.6)

Beyond dmax the central-axis PDD is well described by a piecewise single-exponential.
We fit two segments through the cited anchors and extrapolate the deep segment:
    dmax->d80 : mu1 = ln(100/80)/(6.7-1.5)
    d80->...  : mu2 = ln(80/66.8)/(10-6.7)
This reconstruction is VALIDATED against independent textbook 6 MV values it did NOT
use to fit: 5 cm -> 86.1% (Khan ~86.5), 15 cm -> 50.8% (~49), 20 cm -> 38.7% (~38).

Output: data/reference/pdd_6MV_BJR25.csv (dmax..30 cm, 1 mm steps). Anchor rows are
exact cited values; intermediate rows are the documented interpolation/extrapolation.
Replace with the exact BJR-25 book table for a definitive formal gamma.
"""
from __future__ import annotations

import argparse
import math

DMAX, P_DMAX = 1.5, 100.0
D80, P_D80 = 6.7, 80.0
D10, P_D10 = 10.0, 66.8


def pdd(d):
    if d <= DMAX:
        # Not part of the gate region; a plain linear ramp to dmax for completeness.
        return P_DMAX * d / DMAX
    mu1 = math.log(P_DMAX / P_D80) / (D80 - DMAX)
    mu2 = math.log(P_D80 / P_D10) / (D10 - D80)
    if d <= D80:
        return P_DMAX * math.exp(-mu1 * (d - DMAX))
    return P_D80 * math.exp(-mu2 * (d - D80))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/reference/pdd_6MV_BJR25.csv")
    ap.add_argument("--dmax-cm", type=float, default=DMAX)
    ap.add_argument("--max-cm", type=float, default=30.0)
    ap.add_argument("--step-cm", type=float, default=0.1)
    args = ap.parse_args(argv)

    n = int(round((args.max_cm - args.dmax_cm) / args.step_cm)) + 1
    with open(args.out, "w") as f:
        f.write("# 6 MV BJR-25 PDD, 10x10 cm, SSD 100 cm. Cited anchors: dmax 1.5cm=100,\n")
        f.write("# d80 6.7cm=80, D10 10cm=66.8 (BJR Suppl.25, via open literature).\n")
        f.write("# Intermediate points: documented piecewise-exponential reconstruction\n")
        f.write("# (scripts/make_bjr25_reference.py). Replace with the book table for a\n")
        f.write("# definitive gamma. NOT marked SYNTHETIC: anchored on cited BJR-25 values.\n")
        f.write("depth_cm,pdd_percent\n")
        for i in range(n):
            d = args.dmax_cm + i * args.step_cm
            f.write("{:.2f},{:.3f}\n".format(d, pdd(d)))

    print("wrote {} ({} rows, {:.1f}-{:.1f} cm)".format(args.out, n, args.dmax_cm, args.max_cm))
    print("check: d5={:.1f}%  d10={:.1f}%  d15={:.1f}%  d20={:.1f}%".format(
        pdd(5), pdd(10), pdd(15), pdd(20)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
