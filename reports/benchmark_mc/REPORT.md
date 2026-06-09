# Stage-1 water PDD benchmark — run report (2026-06-09)

## What ran

- Binary: `build/geant4/g4brainatlasdose` (conda-forge Geant4 11.2.2, WSL Ubuntu-22.04).
- Geometry: **pure water cube** via `geant4/run.config.benchmark` (`geometry = water_box`).
  NB: this *fixes a gate bug* — `run.config.example` declares `water_with_insert`
  (a bone insert at 10 cm) which would corrupt the central-axis PDD. The benchmark
  must run in pure water.
- Beam: mono-energetic **6 MeV** photons, 10×10 cm plane source, normal incidence.
- Statistics: 2,000,000 primaries (`benchmark_water.mac`). A 5k smoke
  (`benchmark_water_smoke.mac`) was run first to validate the chain.
- Scoring: command-based `doseDeposit`, 1×1×300 box mesh, 0.5×0.5×15 cm half-size
  → 1 mm depth bins over 30 cm. Dump: `pdd_6MeV.txt`. Curve: `pdd_6MeV_mc.csv`.

## Dump format (TODO closed)

Header `# iX, iY, iZ, total(value) [Gy], total(val^2), entry`; rows
`ix,iy,iz,value,val2,entry`. `g4score_io.read_score_dump` reads column 3 (dose, Gy)
— **confirmed correct** against the first real dump.

## Result of the synthetic gamma gate

`analyze_pdd.py` vs the bundled `pdd_6MV_reference.csv`: **FAIL (13%)** — *expected
and not a physics failure*. The reference is marked `# SYNTHETIC` and has a clinical
**6 MV** shape (dmax 1.5 cm), whereas the beam is mono **6 MeV**. Apples to oranges,
exactly as `data/reference/README.md` warns.

## Independent physics cross-check (no external data) — CONSISTENT

`scripts/independent_pdd_check.py`, anchored on NIST water coefficients at 6 MeV
(`mu/rho = 2.770e-2`, `mu_en/rho = 1.790e-2` cm²/g — *verify vs NIST XAAMDI before
publication*):

| Quantity | MC | Expectation |
|---|---|---|
| dmax depth | **3.35 cm** | mono-6 MeV → deeper than 6 MV (~1.5 cm); e⁻ range ~3 cm → ~2–3.5 cm ✓ |
| tail attenuation `mu_eff` [5,20] cm | **0.0223 /cm** | between `mu_en`=0.0179 (broad limit) and `mu`=0.0277 (narrow) ✓ |

- **Anchor 1** (MC falls no faster than primary attenuation): PASS.
- **Anchor 2** (broad-beam dose attenuation in the `mu_en … mu` band): PASS.

Conclusion: the Geant4 EM transport is behaving correctly — build-up depth and
deep-dose attenuation both match first-principles photon physics for a 10×10 cm
mono-6 MeV beam in water.

## Caveats / next

- The per-bin curve is noisy (1×1 cm scoring column = a single lateral voxel; e.g. a
  statistical dip at 8 cm). For the *official* gate, widen the lateral scoring window
  or raise N so the point-wise gamma is statistics-limited, not noise-limited.
- This consistency check is **not** a substitute for a cited reference PDD. Decide
  the official reference: (A) an independent mono-6 MeV table, or (B) switch to a
  realistic 6 MV spectrum + clinical 6 MV PDD. See `docs/STADIO1_GEANT4_CORE.md`.
