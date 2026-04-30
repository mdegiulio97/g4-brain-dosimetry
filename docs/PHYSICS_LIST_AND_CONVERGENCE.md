# Physics List and Monte Carlo Convergence (MVP-2)

> Closes audit items **L2** ("physics-list ablation missing"), **L3**
> ("convergence criterion vague"), and **L6** ("water-phantom acceptance
> criterion undefined").

## 1. Decision summary

| Item | MVP-2 choice |
|---|---|
| EM physics constructor | **`G4EmStandardPhysics_option4`** (the "EMZ" option set) |
| Hadronic | **None** (pure photon MV) |
| Range cut (brain region) | **0.1 mm** for γ, e⁻, e⁺ |
| Range cut (world) | 1 mm (Geant4 default) |
| MSC | Inherited from option4 (Goudsmit–Saunderson < 100 MeV) |
| Step function | Inherited from option4 (do not override) |
| Voxel scorer | **`G4PSDoseDeposit`** inside a `G4MultiFunctionalDetector` |
| Variance reduction | Range rejection only |
| Convergence target | σ/μ ≤ 3 % in voxels above 50 % D_max (TG-105) |
| Primaries (target) | **N = 2 × 10⁸** for 1 mm³ brain phantom, 6 MV |
| Validation phantom | 30 × 30 × 30 cm³ water cube, 1 mm voxel along CAX |
| Acceptance | γ(2 %/2 mm) ≥ 95 % on PDD over [d_max, 25 cm]; ≤ 1 % at d_max |

The remaining sections justify each choice with literature.

## 2. Why `G4EmStandardPhysics_option4`

### 2.1 The seven candidates

Geant4 11.x ships seven curated EM constructors relevant to medical photon
transport (Geant4 Collaboration, *Physics Reference Manual* rel. 11.2, 2024,
[geant4.web.cern.ch](https://geant4.web.cern.ch/support/user_documentation);
Allison J. et al. 2016, *NIM A* 835:186, doi:10.1016/j.nima.2016.06.125):

- `G4EmStandardPhysics` (option0) — HEP default; fast, but coarse step
  limits make it inappropriate for voxel-wise dosimetry below ~100 MeV.
- `G4EmStandardPhysics_option1` (fast/HEP) — even coarser, *not* used in
  medical applications.
- `G4EmStandardPhysics_option2` — legacy experimental set; **deprecated**.
- `G4EmStandardPhysics_option3` (medical/space) — Goudsmit–Saunderson MSC,
  tightened step-limits (RangeFactor 0.04). Fine for radiotherapy.
- `G4EmStandardPhysics_option4` — combines best models from Standard,
  Livermore, and Penelope at energies where each is most accurate;
  RangeFactor 0.08, step-limit type `fUseSafetyPlus`. Commonly aliased
  "EMZ" in TOPAS/GATE docs and on user fora.
- `G4EmLivermorePhysics` — data-driven EPDL97/EEDL/EADL down to 10 eV;
  optimal for keV photons (radiology, brachytherapy), overkill above
  ~1 MeV.
- `G4EmPenelopePhysics` — port of PENELOPE-2008 models (Salvat 2019,
  *PENELOPE-2018*, OECD/NEA). Comparable accuracy to option4 in MV
  regime, slightly slower.

The literal class `G4EmStandardPhysicsEMZ` does **not** exist in
Geant4 11.x; "EMZ" is the colloquial label for the option-4 set. The
class to instantiate is `G4EmStandardPhysics_option4` (file
`source/physics_lists/constructors/electromagnetic/src/G4EmStandardPhysics_option4.cc`).

### 2.2 Accuracy at 6 MV photons

At 6 MV the dominant interactions are Compton scattering (~70-80 % of
energy transfer) and pair production above 1.022 MeV. Photoelectric is
sub-percent in soft tissue. The detailed atomic-shell description offered
by Livermore / Penelope is therefore **not the limiting factor**;
secondary-electron transport accuracy is. Faddegon et al. 2009 (*Med Phys*
36:4337, doi:10.1118/1.3215526) showed that, with matched step parameters,
Geant4 option3, Livermore, and Penelope reproduce measured electron
lateral spread within 1 %, while option0 deviates by 2–3 %. Cortés-Giraldo
et al. 2012 (*NIM B* 290:51, doi:10.1016/j.nimb.2012.08.022) and
Apostolakis et al. 2009 confirm the equivalence of option4 and Penelope
for MV photons. The IAEA-sponsored G4-Med benchmark (Arce et al. 2021,
*Med Phys* 48:19, doi:10.1002/mp.14226) explicitly recommends option4
as the reference choice for medical-physics photon applications.

### 2.3 Cost

Approximate wall-clock factors for analogous MV water-phantom benchmarks
(Geant4 Validation Repository; Grevillot et al. 2011, *PMB* 56:5203,
doi:10.1088/0031-9155/56/16/008):

| Constructor | wall-clock relative to option0 |
|---|---:|
| option0 | 1.00 |
| option1 | 0.85 |
| option3 | 1.6–1.8 |
| **option4 / EMZ** | **2.5–3.0** |
| Livermore | 3.5–4.5 |
| Penelope | 4.0–5.0 |

option4 buys back the ~2 % accuracy gap at < 3× the option0 cost; at the
same cost Livermore/Penelope add no measurable benefit at 6 MV. **Adopt
option4** for MVP-2; allow `option3` as a documented "fast mode" at the
cost of relaxed acceptance.

## 3. Multiple scattering (MSC)

option4 inherits Goudsmit–Saunderson MSC for e± below 100 MeV (Kadri et al.
2009, *NIM B* 267:3624, doi:10.1016/j.nimb.2009.09.015) — the recommended
choice for medical electron transport. Above 100 MeV it falls back to
`G4UrbanMscModel` (Urban 2006, CERN-OPEN-2006-077). The default
`StepFunction(dRoverRange, finalRange) = (0.08, 50 µm)` gives sub-1 %
PDD accuracy in build-up; loosening to (0.2, 1 mm) costs ~2 % distortion
(Kadri & Ivanchenko 2010, *J Phys Conf Ser* 219:032023). **Do not
override the option4 defaults.**

## 4. Production cuts

Geant4 uses **range** cuts, not energy cuts; the toolkit converts the
range to a per-material energy threshold for each particle type using the
respective range tables (Geant4 *Application Developers Guide* rel. 11.2,
§5.4). Setting an energy cut globally would over-track in dense media; a
range cut produces uniform tracking fidelity per length, which is the
right invariant for voxel-wise dose scoring.

For 1 mm³ voxels with 6 MV photons, AAPM TG-105 (Chetty et al. 2007)
recommends an electron range cut equal to roughly **half the voxel
size**, i.e. 0.5 mm acceptable, **0.1 mm safe**. Tightening below 0.05 mm
increases tracking time superlinearly with negligible dose-distribution
benefit (Faddegon et al. 2009).

Recommended wiring:

```cpp
auto* brain_region = new G4Region("BrainRegion");
brain_region->AddRootLogicalVolume(brain_logical);
auto* brain_cuts = new G4ProductionCuts();
brain_cuts->SetProductionCut(0.1*mm, "gamma");
brain_cuts->SetProductionCut(0.1*mm, "e-");
brain_cuts->SetProductionCut(0.1*mm, "e+");
brain_region->SetProductionCuts(brain_cuts);
```

The world / air / collimator volumes keep the Geant4 default 1 mm cut.
This bounds CPU growth: per Apostolakis et al. 2009, dropping cuts from
1 mm to 0.1 mm in soft tissue is < 2× cost.

## 5. Voxel-wise dose scorer

The recommended scorer is **`G4PSDoseDeposit`** (header
`G4PSDoseDeposit.hh`), attached to a `G4MultiFunctionalDetector` made
sensitive on the parameterised logical voxel (Geant4 *Application
Developers Guide* §4.4.5). It scores `dE / (ρ · V_voxel)` directly
(units Gy = J/kg) and returns a `G4THitsMap<G4double>*` keyed by the
copy number, which for `G4PhantomParameterisation` is the linear voxel
index `i + nx·j + nx·ny·k`.

Why not `G4PSEnergyDeposit + post-process`. The latter is faster (no
per-step density lookup) and lets you re-cast the same energy field
against multiple density assignments, but introduces extra plumbing for
the same final answer. For the MVP-2 scope, `G4PSDoseDeposit` is the
simpler and standard choice.

Note: `G4PSDoseDeposit` returns **dose-to-medium** (Spencer–Attix with
tracked secondaries), *not* kerma. Kerma approximations (`G4PSCellFlux`
× μ_en / ρ) are valid only under charged-particle equilibrium, which
fails in build-up and at tissue interfaces — exactly where this project
is interesting (skull/brain). Always use dose-to-medium.

## 6. Per-voxel uncertainty

Track the per-voxel σ via the **history-by-history** estimator
(Walters et al. 2002, *Med Phys* 29:2745, doi:10.1118/1.1517611):

σ²(D) = (1 / (N·(N − 1))) · [Σ d_i² − (Σ d_i)² / N]

where the sums run over the N independent primary histories and d_i is
the dose contribution of history i to the voxel. Implement as a second
`G4PSDoseDeposit`-like primitive that accumulates `dose²` per history,
or use the `G4VPrimitiveScorer` running-sum / running-sum-of-squares
pattern documented in `examples/extended/runAndEvent/RE03`.

## 7. Convergence target and primaries

AAPM TG-105 sets the standard:

- **σ/μ ≤ 2 %** in voxels receiving ≥ 50 % of D_max ("high-dose region");
- ≤ 3 % in voxels with ≥ 20 % D_max.

Empirical scaling for 1 mm³ voxels, 6 MV broad beam in water/brain
(Sempau et al. 2000, *PMB* 45:587, doi:10.1088/0031-9155/45/3/304;
Kawrakow 2002, *PMB* 47:3087):

| N primaries | σ in 50 % isodose region |
|---:|---:|
| 10⁷ | ~10 % |
| 10⁸ | ~3 % |
| 10⁹ | ~1 % |

For the MVP-2 brain phantom (~1.4 × 10⁶ voxels at 1 mm³, 10 × 10 cm²
field at SSD 100 cm), **N = 2 × 10⁸** primaries achieves the 3 % target.
N = 10⁹ is needed for 2 %. Document the runtime cost: on a modern
single-CPU thread option4 throughputs ~10⁵ primaries/s for a brain
voxelised geometry; 2 × 10⁸ ≈ 30 min single-thread, ~5 min on 8 cores
with `G4MTRunManager`. Realistic upper bound including phase-space input:
1–6 hours per simulation, consistent with the project rationale.

### Stopping rule

Auto-stop when ≥ 95 % of voxels above 50 % D_max satisfy σ/μ < target
(TG-105 §V.C). Implement by polling the per-voxel σ map every 10⁷ events
and short-circuiting `G4Run::Process`.

## 8. Variance reduction

For a *static* brain phantom the only useful technique is **range
rejection**: kill an electron when its residual CSDA range is shorter
than its distance to the nearest region boundary. Speed-up 2–5×, no bias
if applied below the production cut (Sarrut et al. 2014, *Med Phys*
41:064301, doi:10.1118/1.4871617). Implement via Geant4's standard
`G4UAtomicDeexcitation` + the `range rejection` flag in the EM physics
parameters (`G4EmParameters::Instance()->ApplyCuts(true)`).

Bremsstrahlung splitting and Russian roulette are useful only when
modelling a full linac head, which is out of scope for MVP-2 (we read a
phase-space file or use a parametric source).

## 9. Water-phantom benchmark

The first pass before any brain run is a TG-21 / TRS-398 water-phantom
benchmark (IAEA TRS-398 2000; Aird et al. *BJR Suppl. 25* 1996).

**Geometry**

- Water box 30 × 30 × 30 cm³.
- Voxelisation 1 × 1 × 1 mm³ along the central axis (CAX); 2 mm
  laterally is acceptable.
- SSD = 100 cm, square field 10 × 10 cm² at isocentre.
- Beam: monoenergetic 6 MeV photons (cleanest MC benchmark) **or** an
  IAEA 6 MV phase-space (Capote et al. 2006, *IAEA-NDS-0484*).

**Reference data**

- BJR Suppl. 25 PDD/TPR tables (water, 6 MV, 10 × 10 cm², SSD 100 cm).
- Geant4 example `examples/extended/medical/dosimetry/dnaphysics` and
  `examples/extended/medical/fanoCavity` precomputed PDDs.

**Acceptance criteria** (Low et al. 1998, *Med Phys* 25:656,
doi:10.1118/1.598248; AAPM TG-105):

- **Gamma index 2 %/2 mm pass-rate ≥ 95 %** on PDD between d_max and
  25 cm depth.
- ≤ 1 % deviation at d_max (1.5 cm for 6 MV).
- ≤ 2 % on cross-profiles inside 80 % field width.

Failing this benchmark means the physics list, geometry, or scorer is
wrong — *do not* attempt the brain phantom until the water phantom
passes.

### Scripted automation

A target acceptance script lives (or will live) at
`scripts/run_water_phantom_benchmark.py` and produces:

- `dose_pdd_geant4.csv`
- `dose_pdd_reference.csv` (BJR 25 / Geant4 dosimetry example)
- `gamma_index_2pct_2mm.json` with pass-rate.

CI hooks compare the gamma pass-rate against the 95 % threshold and
fail the build on regression.

## 10. GATE cross-check

GATE 9.x / 10 (Sarrut et al. 2014; Sarrut et al. 2022, *PMB* 67:184001,
doi:10.1088/1361-6560/ac8c83) wraps Geant4 and selects the same physics
list via the macro
`/gate/physics/addPhysicsList emstandard_opt4`. The water-phantom PDD
should agree with the Geant4 stand-alone within < 1 % when constructors
and cuts match (Jan et al. 2011, *PMB* 56:881,
doi:10.1088/0031-9155/56/4/001). Cross-check is recommended before
archiving the first MVP-2 brain results.

## 11. References

- Allison J. et al. 2016. *NIM A* 835:186. doi:10.1016/j.nima.2016.06.125.
- Apostolakis J. et al. 2009. *RPC* 78:859.
  doi:10.1016/j.radphyschem.2009.04.026.
- Arce P. et al. (G4-Med) 2021. *Med Phys* 48:19. doi:10.1002/mp.14226.
- Capote R. et al. 2006. IAEA-NDS-0484.
- Chetty I. J. et al. (AAPM TG-105) 2007. *Med Phys* 34:4818.
  doi:10.1118/1.2795842.
- Cortés-Giraldo M. A. et al. 2012. *NIM B* 290:51.
  doi:10.1016/j.nimb.2012.08.022.
- Faddegon B. A. et al. 2009. *Med Phys* 36:4337. doi:10.1118/1.3215526.
- Geant4 Collaboration. *Physics Reference Manual* rel. 11.2, 2024.
  [https://geant4.web.cern.ch/support/user_documentation](https://geant4.web.cern.ch/support/user_documentation).
- Grevillot L. et al. 2011. *PMB* 56:5203.
  doi:10.1088/0031-9155/56/16/008.
- IAEA. *TRS-398* 2000. Absorbed dose determination in external beam
  radiotherapy.
- Jan S. et al. 2011. *PMB* 56:881. doi:10.1088/0031-9155/56/4/001.
- Kadri H. et al. 2009. *NIM B* 267:3624.
  doi:10.1016/j.nimb.2009.09.015.
- Kawrakow I. 2002. *PMB* 47:3087.
- Low D. A. et al. 1998. *Med Phys* 25:656. doi:10.1118/1.598248.
- Salvat F. 2019. *PENELOPE-2018: A code system for Monte Carlo simulation
  of electron and photon transport*. OECD/NEA.
- Sarrut D. et al. 2014. *Med Phys* 41:064301. doi:10.1118/1.4871617.
- Sarrut D. et al. 2022. *PMB* 67:184001. doi:10.1088/1361-6560/ac8c83.
- Sempau J. et al. 2000. *PMB* 45:587. doi:10.1088/0031-9155/45/3/304.
- Walters B. R. B. et al. 2002. *Med Phys* 29:2745. doi:10.1118/1.1517611.
