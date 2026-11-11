# Reference PDD data for the water-phantom benchmark

The water benchmark (see `reports/benchmark_mc/REPORT.md`) requires the Monte Carlo central-
axis percent depth dose (PDD) to agree with an **independent reference** within
gamma(2 %/2 mm) ≥ 95 % over `[dmax, 25 cm]`. This folder holds that reference.

## Format

A CSV with two columns and a header:

```
depth_cm,pdd_percent
0.0,30.0
1.5,100.0
...
```

- `depth_cm` — depth along the central axis, measured from the phantom entrance
  face (0 cm = surface). Strictly increasing.
- `pdd_percent` — percent depth dose, normalised so the maximum (at dmax) is
  100.0. `analyze_pdd.py` re-normalises both curves to their own maximum, so the
  absolute scale does not matter, only the shape.

An optional first line `# SYNTHETIC` marks a placeholder curve; `analyze_pdd.py`
then prints a warning that the result is illustrative and **not** a valid
acceptance test.

## What to put here (in order of preference)

1. **Measured commissioning PDD** for your 6 MV beam (10×10 cm², SSD 100 cm) — the
   gold standard if you have access to a linac's beam data.
2. **Published reference tables** — BJR Supplement 25 (Aird et al. 1996) 6 MV PDD,
   or AAPM TG-51 era reference data. Digitise and cite the exact source in a
   sibling `pdd_6MV_reference.SOURCE.txt`. **Do not** treat digitised values as
   exact without recording provenance (see citation discipline).
3. **An independent Monte Carlo** (e.g. a published Geant4/EGSnrc 6 MV PDD) as a
   cross-check, clearly labelled.

> NOTE: the geometry in `geant4/macros/benchmark_water.mac` uses a **mono-energetic
> 6 MeV** photon beam (MVP-2 simplification), whose PDD differs from a real **6 MV
> bremsstrahlung spectrum** (mean ~2 MeV). For a fair benchmark either (a) compare
> against a mono-energetic 6 MeV reference, or (b) switch the beam to an IAEA 6 MV
> phase-space and compare against clinical 6 MV PDD. State which in the SOURCE file.

## Files

- `pdd_6MV_reference.csv` — the curve `analyze_pdd.py` reads by default. Currently
  a **SYNTHETIC placeholder**; replace with real data per above.
- `pdd_6MV_reference.SOURCE.txt` — provenance of the data (you create this when you
  add real data).

Real measured/large data files dropped here that match the global ignore patterns
(`*.nii.gz`, `*.npy`, …) will be gitignored; the CSV reference and this README are
tracked.
