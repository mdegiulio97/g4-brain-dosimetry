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

## Track A — mono-6 MeV cross-physics-list (independent MC reference)

Same pure-water mono-6 MeV benchmark run with three independent EM physics models.
Different cross-section datasets/algorithms → convergence is strong, external-data-
free evidence the transport is correct. Wide 4×4 cm scoring column, 4M primaries
(the earlier 1×1 cm / 2M comparison was noise-dominated: ΔPDD 8–11%, non-physical
Livermore dmax 6.55 cm — both artefacts of statistics, now gone).

| Physics list | dmax (cm) | μ_eff tail [5,20] (/cm) | max \|ΔPDD\| vs option4 |
|---|---|---|---|
| option4   | 3.55 | 0.0214 | — |
| Livermore | 2.95 | 0.0216 | 2.8 % |
| Penelope  | 2.75 | 0.0217 | 2.7 % |

μ_eff agrees to <1.5 %; point-wise curves agree to ~2.7 %. **Three independent EM
models converge → EM transport is model-robust and correct.** Tighten to <2 % with
more primaries if a stricter statement is wanted.

## Track B — representative 6 MV spectrum (clinical beam)

`scripts/make_6mv_spectrum.py` builds a filtered thick-target bremsstrahlung spectrum
(mean 1.90 MeV, peak 0.93 MeV, endpoint 6 MeV — *representative analytic, NOT a cited
phase-space*). Run in pure water, wide scoring, 4M primaries. vs textbook 6 MV PDD
landmarks (10×10, SSD 100; representative, not a cited table):

| depth | MC 6 MV % | textbook % | Δ (pp) |
|---|---|---|---|
| dmax | 1.65 cm | ~1.5 cm | — |
| 5 cm  | 87.9 | 86.5 | +1.4 |
| 10 cm | 74.4 | 66.5 | +7.9 |
| 15 cm | 61.4 | 49.0 | +12.4 |
| 20 cm | 50.0 | 38.0 | +12.0 |

The spectrum reproduces the **clinical build-up and dmax** (1.65 cm, vs 3.35 cm for
mono-6 MeV) and matches near the surface, but is **too penetrating beyond 10 cm** —
the analytic spectrum carries too much high-energy fluence. Quantified, honest result:
for a formal clinical gate, replace with a cited 6 MV spectrum (Mohan et al. 1985) or
an IAEA phase-space, plus a measured / BJR-25 PDD.

## Track B closed with CITED data — Mohan6 spectrum + inverse-square vs BJR-25

The +8..12 pp deep-dose excess in the analytic-spectrum run was diagnosed and
resolved with cited reference data (`scripts/clinical_pdd_compare.py`):

- **Cited spectrum**: `data/reference/mohan6.spectrum` — Mohan, Chui & Lidofsky,
  Med Phys 12(5):592–597 (1985), as distributed with EGSnrc (24 bins, 0–6 MeV).
  Macro via `scripts/egsnrc_spectrum_to_macro.py`.
- **Finding 1 — spectrum was NOT the cause.** Mohan6 and the analytic
  `make_6mv_spectrum.py` beam give the same parallel-beam PDD (<1 pp at 5/10/15/20
  cm). The deep excess is not a spectrum artefact.
- **Finding 2 — geometry was.** Our source is a *parallel plane* beam; clinical PDD
  is a *divergent point source at SSD 100 cm*. Applying the inverse-square factor
  `ISF(d) = ((SSD+dmax)/(SSD+d))^2` to the MC reproduces the cited BJR-25 landmarks:

  | depth | MC parallel % | MC + ISF (clinical) % | BJR-25 % | Δ (pp) |
  |---|---|---|---|---|
  | dmax (1.75 cm) | 99.1 | 99.5 | 100.0 | −0.5 |
  | 5 cm  | 90.3 | 84.7 | 86.5 | −1.8 |
  | 6.7 cm (d80) | 85.4 | 77.6 | 80.0 | −2.4 |
  | 10 cm (D10) | 76.8 | **65.7** | **66.8** | **−1.1** |
  | 15 cm | 62.4 | 48.8 | 49.0 | −0.2 |
  | 20 cm | 51.2 | 36.8 | 38.0 | −1.2 |

  BJR-25 landmarks: `data/reference/pdd_6MV_BJR25_landmarks.csv` (cited values).

**Clinical 6 MV PDD now matches cited BJR-25 landmarks to ~1–2 pp.**

### Formal full-curve gamma — PASS

`scripts/make_bjr25_reference.py` builds a dense BJR-25 curve (`data/reference/
pdd_6MV_BJR25.csv`) anchored on the cited points (dmax/d80/D10) with a documented
piecewise-exponential between them (validated against independent textbook values it
did not fit: d5 86.1%, d15 50.8%, d20 38.7%). `scripts/gamma_clinical_bjr25.py` then
runs γ(2%/2mm) of the clinical MC (Mohan6 + inverse-square) over [dmax, 25 cm]:

| primaries | pass rate | γ mean / max | result |
|---|---|---|---|
| 4M  | 73.0 % | 0.78 / 1.68 | FAIL (statistics-limited) |
| **20M** | **95.7 %** | **0.62 / 1.16** | **PASS** (threshold 95 %) |

The gate is statistics-limited, not physics-limited: 20M primaries clears γ(2%/2mm).
**Stage-1 physics gate: PASSED** against a cited-anchored BJR-25 reference. For a
definitive result, swap in the exact BJR-25 book table (only landmarks are openly
cited) and/or model beam divergence directly instead of the post-hoc ISF.

## beam divergence MODELLED (post-hoc ISF removed), 2026-07-02

The post-hoc inverse-square "asterisk" above is now closed: the divergence is
produced by the transport itself. A GPS **point source at SSD 100 cm** (source at
z ≈ −115 cm, inside an enlarged world via `world_half_z_cm = 120`) emits an `iso`
cone whose half-angle `atan(5/100)=2.86°` reproduces the 10 cm field at the water
surface. Both the field divergence and the 1/r² fall-off are thus physical, not
applied afterward.

- Config: `geant4/run.config.benchmark.divergent`; macro
  `geant4/macros/benchmark_mohan6_divergent.generated.mac` (Mohan6 cited spectrum,
  20M primaries). Generated with `egsnrc_spectrum_to_macro.py --divergent`.
- Gate: `scripts/gamma_clinical_bjr25.py --no-isf` (skips the post-hoc ISF so
  divergence is not double-counted).

| beam model | γ(2%/2mm) over [dmax,25 cm] | γ mean / max | result |
|---|---|---|---|
| parallel + post-hoc ISF (20M) | 95.7 % | 0.62 / 1.16 | PASS |
| **divergent point source, modelled (20M)** | **100.0 %** | **0.42 / 0.76** | **PASS** |
| sanity: ISF applied on the already-divergent dump | 6.8 % | 4.54 / 5.93 | FAIL (double-counts divergence — expected) |

Modelling the divergence not only removes the methodological caveat, it **improves**
the agreement (100 % vs 95.7 %, γ mean 0.42 vs 0.62). dmax 1.45 cm; D10 ≈ 68.8 %
vs cited BJR-25 66.8 %, straight from the transport. The sanity row confirms the
`--no-isf` and post-hoc-ISF paths are mutually exclusive by construction.

Remaining caveat: the field is a circular `iso` cone (~ the 10×10 square field for
central-axis PDD); the BJR-25 reference is still cited-anchor-reconstructed (the full
book table is copyright).

## Caveats / next

- The per-bin curve is noisy (1×1 cm scoring column = a single lateral voxel; e.g. a
  statistical dip at 8 cm). For the *official* gate, widen the lateral scoring window
  or raise N so the point-wise gamma is statistics-limited, not noise-limited.
- This consistency check is **not** a substitute for a cited reference PDD. Decide
  the official reference: (A) an independent mono-6 MeV table, or (B) switch to a
  realistic 6 MV spectrum + clinical 6 MV PDD.
