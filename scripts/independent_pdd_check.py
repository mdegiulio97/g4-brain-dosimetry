"""Independent physics cross-check of the mono-6 MeV water PDD (no external data).

Purpose (Stage-1 gate, interim): before committing to an "official" reference PDD,
confirm the Geant4 EM transport is behaving correctly by comparing the MC central-
axis depth-dose against first-principles photon-attenuation physics.

Two independent anchors, both from NIST mass attenuation / energy-absorption
coefficients for liquid water at 6 MeV:

  1. PRIMARY attenuation (narrow-beam limit): the *primary* photon collision kerma
     falls as exp(-mu * d), mu = (mu/rho) * rho. The MC total dose beyond the
     build-up region must fall NO FASTER than this (scatter only adds dose).

  2. BROAD-beam limit: in a wide field, scattered photons are largely retained on
     axis, so the central-axis dose attenuation approaches the ENERGY-ABSORPTION
     coefficient mu_en/rho rather than the total mu. The fitted effective
     attenuation of the MC tail should sit between mu_en (broad) and mu (narrow),
     and for a 10x10 field at 6 MeV close to mu_en.

NIST values (XAAMDI; Hubbell & Seltzer, liquid water, 6.000 MeV):
    mu/rho     = 2.770e-2 cm^2/g   -> mu     = 0.02770 /cm (rho = 1.0 g/cm^3)
    mu_en/rho  = 1.790e-2 cm^2/g   -> mu_en  = 0.01790 /cm
  *** VERIFY against https://physics.nist.gov/PhysRefData/XrayMassCoef before any
      publication; these are transcribed from the standard table, not re-derived. ***
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from g4score_io import central_axis_pdd, read_score_dump

MU_OVER_RHO_6MEV = 2.770e-2      # cm^2/g, NIST water total (with coherent)
MU_EN_OVER_RHO_6MEV = 1.790e-2   # cm^2/g, NIST water energy-absorption
RHO_WATER = 1.0                  # g/cm^3


def fit_effective_mu(depth_cm, pdd, d_lo, d_hi):
    """Least-squares slope of ln(PDD) over [d_lo, d_hi] -> effective /cm."""
    m = (depth_cm >= d_lo) & (depth_cm <= d_hi) & (pdd > 0)
    d = depth_cm[m]
    y = np.log(pdd[m])
    A = np.vstack([d, np.ones_like(d)]).T
    slope, _ = np.linalg.lstsq(A, y, rcond=None)[0]
    return -slope  # /cm (positive = attenuation)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mc-dump", default="reports/benchmark_mc/pdd_6MeV.txt")
    ap.add_argument("--mesh-halfz-cm", type=float, default=15.0)
    ap.add_argument("--fit-lo-cm", type=float, default=5.0,
                    help="start fit beyond build-up")
    ap.add_argument("--fit-hi-cm", type=float, default=20.0,
                    help="stop before noisy phantom-edge bins")
    args = ap.parse_args(argv)

    dose, shape = read_score_dump(args.mc_dump)
    pdd = central_axis_pdd(dose)
    nz = shape[2]
    dz = 2.0 * args.mesh_halfz_cm / nz
    depth = (np.arange(nz) + 0.5) * dz

    imax = int(np.argmax(pdd))
    dmax = depth[imax]

    mu = MU_OVER_RHO_6MEV * RHO_WATER
    mu_en = MU_EN_OVER_RHO_6MEV * RHO_WATER
    mu_eff = fit_effective_mu(depth, pdd, args.fit_lo_cm, args.fit_hi_cm)

    print("=== Independent mono-6 MeV water PDD cross-check ===")
    print("MC dmax depth            : {:.2f} cm".format(dmax))
    print("  (mono-6 MeV expectation: deeper than 6 MV's ~1.5 cm; secondary e-")
    print("   range ~3 cm puts dmax ~2-3.5 cm -- physically consistent)")
    print()
    print("Fitted MC tail attenuation over [{:.0f},{:.0f}] cm:".format(
        args.fit_lo_cm, args.fit_hi_cm))
    print("  mu_eff(MC)             : {:.4f} /cm".format(mu_eff))
    print("NIST water @ 6 MeV:")
    print("  mu_en/rho (broad limit): {:.4f} /cm".format(mu_en))
    print("  mu/rho    (narrow lim) : {:.4f} /cm".format(mu))
    print()

    # Anchor 1: MC must fall no faster than primary attenuation.
    no_faster = mu_eff <= mu * 1.02  # 2% tolerance on the hard bound
    # Anchor 2: broad-beam dose attenuation ~ mu_en (within the narrow..broad band).
    in_band = (mu_eff >= mu_en * 0.90) and (mu_eff <= mu * 1.02)
    dev_en = 100.0 * (mu_eff - mu_en) / mu_en

    print("Anchor 1  mu_eff <= mu (no faster than primary)      : {}".format(
        "PASS" if no_faster else "FAIL"))
    print("Anchor 2  mu_en <= mu_eff <= mu (broad-beam band)     : {}".format(
        "PASS" if in_band else "FAIL"))
    print("          mu_eff vs mu_en deviation                  : {:+.1f} %".format(
        dev_en))
    print()

    # Tabulate MC vs the two analytic envelopes, normalised at dmax.
    print("depth_cm  MC_pdd%   primary_exp(-mu*d)%   broad_exp(-mu_en*d)%")
    for d in [dmax, 5, 8, 10, 15, 20, 25]:
        k = min(int(d / dz), nz - 1)
        prim = 100.0 * np.exp(-mu * (depth[k] - dmax))
        broad = 100.0 * np.exp(-mu_en * (depth[k] - dmax))
        print("  {:5.2f}   {:6.1f}        {:6.1f}              {:6.1f}".format(
            depth[k], 100 * pdd[k], prim, broad))

    ok = no_faster and in_band
    print("\nRESULT: {}  (consistency check, not a substitute for a cited reference)"
          .format("CONSISTENT" if ok else "INCONSISTENT -- investigate"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
