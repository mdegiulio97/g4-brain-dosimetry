"""Water-phantom PDD benchmark: 1-D gamma(2%/2mm) of MC vs reference.

The water benchmark gate (reports/benchmark_mc/REPORT.md): the Monte Carlo central-axis
percent depth dose must agree with an independent reference within
gamma(2%/2mm) >= 95% over [dmax, 25 cm]. This script computes that pass rate.

Inputs:
  --mc-dump    Geant4 scoring dump from benchmark_water.mac (1x1xNz mesh).
  --reference  data/reference/pdd_6MV_reference.csv (see that folder's README).

Both curves are normalised to their own maximum before comparison, so only the
shape matters. A reference file whose first line is "# SYNTHETIC" triggers a
loud warning that the result is illustrative, not a valid acceptance test.

Pure-numpy. Reuses g4score_io for the MC side.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from g4score_io import central_axis_pdd, read_score_dump


def load_reference_pdd(path):
    """Return (depth_cm, pdd_norm, is_synthetic)."""
    is_synthetic = False
    depths, doses = [], []
    with open(path, "r") as f:
        first = True
        for raw in f:
            line = raw.strip()
            if first and line.upper().startswith("# SYNTHETIC"):
                is_synthetic = True
            first = False
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("depth"):
                continue  # header
            parts = line.replace(",", " ").split()
            if len(parts) < 2:
                continue
            try:
                depths.append(float(parts[0]))
                doses.append(float(parts[1]))
            except ValueError:
                continue
    d = np.asarray(depths, dtype=float)
    p = np.asarray(doses, dtype=float)
    order = np.argsort(d)
    d, p = d[order], p[order]
    m = p.max()
    return d, (p / m if m > 0 else p), is_synthetic


def mc_pdd_axis(dump_path, mesh_halfz_cm, mesh_nz):
    """Return (depth_cm, pdd_norm) for the MC central-axis PDD."""
    dose, shape = read_score_dump(dump_path)
    if shape[2] != mesh_nz:
        print("WARNING: dump nz={} != --mesh-nz {}".format(shape[2], mesh_nz))
    pdd = central_axis_pdd(dose)  # normalised to its own max, indexed by z bin
    dz = 2.0 * mesh_halfz_cm / mesh_nz
    depth = (np.arange(shape[2]) + 0.5) * dz  # cm from entrance face
    return depth, pdd


def gamma_1d(ref_d, ref_D, mc_d, mc_D, dta_cm, dose_tol):
    """Per-reference-point 1-D gamma, searching over all MC samples.

    ref_D, mc_D normalised to global max = 1. dose_tol is a fraction of max.
    """
    gammas = np.empty_like(ref_d)
    for n, (d, D) in enumerate(zip(ref_d, ref_D)):
        dd = (mc_d - d) / dta_cm
        dD = (mc_D - D) / dose_tol
        gammas[n] = np.sqrt(dd * dd + dD * dD).min()
    return gammas


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mc-dump", required=True)
    ap.add_argument("--reference", default="data/reference/pdd_6MV_reference.csv")
    ap.add_argument("--mesh-halfz-cm", type=float, default=15.0)
    ap.add_argument("--mesh-nz", type=int, default=300)
    ap.add_argument("--dta-mm", type=float, default=2.0)
    ap.add_argument("--dose-tol", type=float, default=0.02, help="fraction of max")
    ap.add_argument("--range-cm", type=float, default=25.0)
    ap.add_argument("--threshold", type=float, default=0.95)
    args = ap.parse_args(argv)

    ref_d, ref_D, synthetic = load_reference_pdd(args.reference)
    mc_d, mc_D = mc_pdd_axis(args.mc_dump, args.mesh_halfz_cm, args.mesh_nz)

    dmax_cm = float(ref_d[int(np.argmax(ref_D))])
    mask = (ref_d >= dmax_cm) & (ref_d <= args.range_cm)
    g = gamma_1d(ref_d[mask], ref_D[mask], mc_d, mc_D,
                 args.dta_mm / 10.0, args.dose_tol)
    pass_rate = float((g <= 1.0).mean())

    print("PDD benchmark gamma({:.0f}%/{:.0f}mm) over [{:.1f}, {:.1f}] cm"
          .format(args.dose_tol * 100, args.dta_mm, dmax_cm, args.range_cm))
    print("  evaluated points: {}".format(int(mask.sum())))
    print("  pass rate       : {:.1%}  (threshold {:.0%})"
          .format(pass_rate, args.threshold))
    print("  gamma mean/max  : {:.3f} / {:.3f}".format(g.mean(), g.max()))

    if synthetic:
        print("\n*** WARNING: reference is marked SYNTHETIC -- this is a pipeline "
              "self-test, NOT a valid physics acceptance. Replace with real data. ***")

    passed = pass_rate >= args.threshold
    print("\nRESULT: {}".format("PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
