"""Generate a CITED kVp bremsstrahlung spectrum with
SpekPy and write it in the EGSnrc .spectrum format already parsed by
scripts/egsnrc_spectrum_to_macro.py (parse_egsnrc_spectrum).

The result is a reproducible, citable, polyenergetic kV source:


  SpekPy v2.0 -- Poludniowski, Omar, Bujila, Andreo, "Technical Note: SpekPy
  v2.0 -- a software toolkit for modeling x-ray tube spectra", Medical Physics
  48(7):3630-3637, 2021. DOI 10.1002/mp.14945.

If SpekPy is not installed the script exits with install instructions rather
than fabricating a spectrum (the documented fallback is a citable tabulated
model such as TASMICS -- never a hand-digitised curve).

EGSnrc .spectrum format written here:
  line 1: title (carries the citation)
  line 2: NBIN  ENMIN(MeV)  IMODE
  next NBIN lines: E_upper_i(MeV)  prob_i   (E_upper_0 edge = ENMIN)

Usage:
  python scripts/make_kvp_spectrum.py --kvp 120 --out data/reference/kvp120.spectrum
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def build_spectrum(kvp, anode_angle_deg, filter_al_mm, dk_kev):
    """Return (centres_MeV, fluence, meanE_keV, hvl_al_mm) from SpekPy, or raise
    ImportError if SpekPy is unavailable."""
    try:
        import spekpy as sp
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "SpekPy not installed. Install with `pip install spekpy` (or "
            "`uv pip install spekpy`) in the Geant4 env. If it cannot be "
            "installed, fall back to a citable tabulated model (TASMICS, "
            "Hernandez & Boone, Med Phys 41(4):042101, 2014) -- do NOT "
            "hand-digitise a curve.") from exc

    s = sp.Spek(kvp=kvp, th=anode_angle_deg, dk=dk_kev)
    s.filter("Al", filter_al_mm)
    k_kev, fluence = s.get_spectrum(edges=False)  # bin-centre energies (keV)
    mean_e = float(s.get_emean())
    try:
        hvl = float(s.get_hvl1())  # 1st HVL in mm Al (provenance only)
    except Exception:  # pragma: no cover
        hvl = float("nan")
    return np.asarray(k_kev), np.asarray(fluence), mean_e, hvl


def write_egsnrc_spectrum(path, title, centres_mev, weights):
    """Write the EGSnrc .spectrum format from bin-centre energies (MeV)."""
    centres = np.asarray(centres_mev, dtype=float)
    w = np.asarray(weights, dtype=float)
    if centres.size < 2:
        raise SystemExit("spectrum has < 2 bins; check SpekPy output")
    dk = float(np.median(np.diff(centres)))
    enmin = float(centres[0] - dk / 2.0)
    edges_up = centres + dk / 2.0
    w = w / w.sum()  # normalise the histogram
    lines = [title, "{:d}  {:.6f}  0".format(len(centres), max(enmin, 0.0))]
    for eu, p in zip(edges_up, w):
        lines.append("{:.6f}  {:.6e}".format(eu, p))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kvp", type=float, default=120.0)
    ap.add_argument("--anode-angle-deg", type=float, default=12.0)
    ap.add_argument("--filter-al-mm", type=float, default=2.5,
                    help="inherent Al filtration (mm); declared modelling choice")
    ap.add_argument("--dk-kev", type=float, default=1.0, help="bin width (keV)")
    ap.add_argument("--out", default="data/reference/kvp120.spectrum")
    args = ap.parse_args(argv)

    cite = ("SpekPy v2.0 (Poludniowski et al., Med Phys 48(7):3630-3637, 2021, "
            "DOI 10.1002/mp.14945)")
    try:
        k_kev, fluence, mean_e, hvl = build_spectrum(
            args.kvp, args.anode_angle_deg, args.filter_al_mm, args.dk_kev)
    except ImportError as exc:
        print(exc, file=sys.stderr)
        return 2

    title = ("{:g} kVp W-anode {:g} deg, {:g} mm Al | {}".format(
        args.kvp, args.anode_angle_deg, args.filter_al_mm, cite))
    centres_mev = k_kev / 1000.0
    write_egsnrc_spectrum(args.out, title, centres_mev, fluence)

    # Provenance manifest (full modelling choices + citation).
    manifest = Path(str(args.out) + ".manifest.txt")
    manifest.write_text(
        "kVp spectrum provenance\n"
        "=======================\n"
        "generator      : scripts/make_kvp_spectrum.py\n"
        "toolkit        : {}\n".format(cite) +
        "tube potential : {:g} kVp\n".format(args.kvp) +
        "anode angle    : {:g} deg (tungsten)\n".format(args.anode_angle_deg) +
        "inherent filter: {:g} mm Al\n".format(args.filter_al_mm) +
        "bin width       : {:g} keV\n".format(args.dk_kev) +
        "mean energy     : {:.3f} keV\n".format(mean_e) +
        "1st HVL (Al)    : {:.3f} mm\n".format(hvl) +
        "spectrum file   : {}\n".format(args.out),
        encoding="utf-8")

    print("Wrote {} ({} bins), mean E = {:.2f} keV, HVL1 = {:.2f} mm Al".format(
        args.out, len(k_kev), mean_e, hvl))
    print("Manifest -> {}".format(manifest))
    print("Next: python scripts/make_kv_spectrum_macro.py --spectrum {}".format(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
