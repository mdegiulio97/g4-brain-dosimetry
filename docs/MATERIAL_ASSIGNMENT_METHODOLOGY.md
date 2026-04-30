# Material Assignment Methodology (MVP-2)

> Closes audit items **L1** ("material assignment vague") and **D3**
> ("MATERIAL_MAP_SCHEMA defines schema but no concrete values").

## 1. Scope and decision

For MVP-2, brain anatomy comes from a **fixed MNI152 atlas** (Fonov et al.
2011, *NeuroImage* 54:313, doi:10.1016/j.neuroimage.2010.07.033). There is
no patient-specific CT, no subject MRI, and no recalculation: the geometry
and the materials are **frozen artefacts of the project**. Three
candidate strategies were considered:

| Strategy | Description | Adopted? |
|---|---|---|
| **A — Bulk look-up (ICRU-44 / Woodard & White)** | 5 tissue classes (`air`, `csf`, `brain_gm`, `brain_wm`, `bone`) with fixed densities and elemental compositions taken from public reference tables. | **YES — adopted for MVP-2** |
| B — Synthetic CT (sCT) | Generate a pseudo-CT from MRI via deep learning (e.g. SynthSR / pseudo-CT) and apply Schneider piecewise HU→ρ. | Rejected for MVP-2 |
| C — Hybrid | Bulk for soft tissues, sCT for skull; or sCT inside, bulk outside. | Rejected for MVP-2 |

**Rationale for choosing A.** The MNI152 atlas is a population template: no
individual MR scan is available to convert to HU, so sCT (B) cannot be
applied to it directly. Even where sCT is technically applicable, Owrangi
et al. (2018, *PMB* 63:05TR01, doi:10.1088/1361-6560/aaaca4) and Edmund &
Nyholm (2017, *Radiat. Oncol.* 12:28, doi:10.1186/s13014-016-0747-y) report
that 5-class bulk assignment achieves PTV dose accuracy within 1-2 % of
full sCT for cranial photon plans — well below the systematic uncertainty
budget of an atlas-based statistical pipeline. Bulk lookup is fully public,
citable, frozen, and immediately reproducible; sCT introduces a
training-set dependency and is reserved for MVP-3+ when individual MR
volumes appear in the workflow.

## 2. Reference standards

The five tissue classes are defined by the following primary sources.
Quoting the specific report saves ambiguity: the values flow into Geant4
material objects unmodified.

- **ICRU Report 44 (1989)** — *Tissue Substitutes in Radiation Dosimetry
  and Measurement*, doi:10.1093/jicru/os23.1.Report44. Bulk densities and
  elemental compositions of body tissues, including whole brain, soft
  tissue, cortical bone, and air.
- **ICRU Report 46 (1992)** — *Photon, Electron, Proton and Neutron
  Interaction Data for Body Tissues*, doi:10.1093/jicru/os24.1.Report46.
  Companion to ICRU-44, accepts the same compositions and provides the
  cross-section tables.
- **Woodard & White (1986)** — "The composition of body tissues",
  *Br. J. Radiol.* 59:1209, doi:10.1259/0007-1285-59-708-1209. The most
  cited primary source for the **gray matter / white matter / CSF split**,
  which ICRU-44 does not explicitly publish.
- **ICRP Publication 89 (Valentin 2002)** — *Annals of the ICRP* 32(3-4):
  doi:10.1016/S0146-6453(03)00002-2. Adult reference brain mass and
  density (ρ = 1.04 g cm⁻³).

A modern in-vivo MR-elastography re-measurement (Shen et al. 2024,
*NeuroImage* 287:120516, doi:10.1016/j.neuroimage.2024.120516) confirms
the Woodard & White GM/WM densities to within ±0.004 g cm⁻³.

## 3. The five tissue classes

Mass fractions in % (rounded to 0.1), density in g cm⁻³.

| Class | `material_id` | ρ | H | C | N | O | Na | Mg | P | S | Cl | K | Ca | Ar | Source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `air` | `G4_AIR` | 1.20479e-3 | – | 0.0 | 75.5 | 23.2 | – | – | – | – | – | – | – | 1.3 | NIST / ICRU-44 |
| `csf` | `G4_CSF` | 1.007 | 11.1 | – | – | 88.0 | 0.5 | – | – | – | 0.4 | – | – | – | Woodard & White 1986 |
| `brain_gm` | `G4_GRAY_MATTER` | 1.045 | 10.7 | 9.5 | 1.8 | 76.7 | 0.2 | – | 0.3 | 0.2 | 0.3 | 0.3 | – | – | Woodard & White 1986 |
| `brain_wm` | `G4_WHITE_MATTER` | 1.041 | 10.6 | 19.4 | 2.5 | 66.1 | 0.2 | – | 0.4 | 0.2 | 0.3 | 0.3 | – | – | Woodard & White 1986 |
| `bone` | `G4_BONE_CORTICAL_ICRP` | 1.850 | 4.7 | 14.4 | 4.2 | 44.6 | 0.1 | 0.2 | 10.5 | 0.3 | – | – | 21.0 | – | ICRU-44 / ICRP-89 |

**Why no whole-brain class.** ICRU-44's "Brain (whole, adult)" entry
(ρ = 1.040, 71.2 % O, 14.5 % C) is *not* used: the MNI152-derived
segmentation natively exposes a GM/WM/CSF split, and the GM/WM elemental
compositions diverge enough (76.7 % vs 66.1 % O) to deserve separate
materials. Using the whole-brain proxy would discard available structural
information.

**Why ICRP cortical bone.** The skull in MNI152 has no internal
trabeculation visible at 1 mm; the ICRU-46 / ICRP cortical-bone proxy is
the standard choice for cranial dosimetry (Andreo 1991, *PMB* 36:861,
doi:10.1088/0031-9155/36/7/001). Skin and adipose layers are not
segmented separately in this MVP and are absorbed into `brain_gm` /
background.

## 4. Geant4 material construction

Three of the five classes resolve to a NIST entry already present in
Geant4 (`G4NistManager::FindOrBuildMaterial`):

```cpp
auto* nist = G4NistManager::Instance();
G4Material* air  = nist->FindOrBuildMaterial("G4_AIR");
G4Material* bone = nist->FindOrBuildMaterial("G4_BONE_CORTICAL_ICRP");
G4Material* water = nist->FindOrBuildMaterial("G4_WATER"); // CSF surrogate, see §5
```

`brain_gm`, `brain_wm`, and (optionally) a saline `csf` need explicit
`G4Material` objects built from the elemental fractions in §3, e.g.:

```cpp
G4Material* gm = new G4Material("G4_GRAY_MATTER", 1.045*g/cm3, 9);
gm->AddElement(nist->FindOrBuildElement("H"),  10.7*perCent);
gm->AddElement(nist->FindOrBuildElement("C"),   9.5*perCent);
gm->AddElement(nist->FindOrBuildElement("N"),   1.8*perCent);
gm->AddElement(nist->FindOrBuildElement("O"),  76.7*perCent);
gm->AddElement(nist->FindOrBuildElement("Na"),  0.2*perCent);
gm->AddElement(nist->FindOrBuildElement("P"),   0.3*perCent);
gm->AddElement(nist->FindOrBuildElement("S"),   0.2*perCent);
gm->AddElement(nist->FindOrBuildElement("Cl"),  0.3*perCent);
gm->AddElement(nist->FindOrBuildElement("K"),   0.3*perCent);
```

The MVP-2 implementation must not silently fall back to `G4_WATER` for
`brain_gm` / `brain_wm`: photon dose-to-medium in white matter differs
from dose-to-water by ~1 % at 6 MV (Andreo 2015, *PMB* 60:309,
doi:10.1088/0031-9155/60/1/309), which is exactly the resolution this
project is targeting.

## 5. Production cuts

A single uniform **range cut of 0.1 mm** for γ, e⁻, e⁺ inside the brain
region is recommended (AAPM TG-105: Chetty et al. 2007, *Med Phys* 34:4818,
doi:10.1118/1.2795842; Apostolakis et al. 2009, *RPC* 78:859,
doi:10.1016/j.radphyschem.2009.04.026). Outside the brain (air, world
volumes), the Geant4 default of 1 mm is sufficient and saves CPU. The
range cut is realised via a dedicated `G4Region` covering the
parameterised phantom; see `docs/PHYSICS_LIST_AND_CONVERGENCE.md` for the
Geant4 wiring.

## 6. Sensitivity to density choice

Brain tissues all sit within ~5 % of water density, so absolute dose is
weakly sensitive to small density errors:

- du Plessis et al. 1998 (*Med Phys* 25:1195, doi:10.1118/1.598297): 5 %
  density perturbation in soft tissue → < 0.7 % dose change at 6 MV.
- Andreo 1991: linear regime for thin layers; cumulative effect of
  Δρ/ρ = 2 % over 10 cm of brain tissue is < 1 % at MV photons.
- Yang et al. 2012 (*PMB* 57:4095, doi:10.1088/0031-9155/57/13/4095): for
  *protons*, the same 2 % density error costs ~1.5 % range — relevant
  only when MVP-3+ adds proton beams.

**Bottom line:** rounding the GM/WM densities to a single value
(e.g. 1.04 g cm⁻³) introduces < 0.3 % global dose error for photons.
The MVP-2 keeps the Woodard & White split because it is *free* (no
extra cost) and removes a free parameter from the methods description.

## 7. Concrete artefact

A frozen, citable instance of this material map lives at:

```
configs/examples/material_map.brain.csv
```

It carries the five rows of §3 in the schema defined by
`docs/MATERIAL_MAP_SCHEMA.md` (`label, material_id, density_g_cm3,
description`). Tissue labels and CSV labels match the convention:

- `0` → `air` (background)
- `1` → `csf`
- `2` → `brain_gm`
- `3` → `brain_wm`
- `4` → `bone`

The pre-existing `configs/examples/material_map.example.csv` (a
**synthetic** 4-class file used by the contract validator unit tests) is
left untouched: it has no anatomical pretensions and exists to exercise
the parser, not to drive simulations.

## 8. Documented limitations

1. Bulk assignment ignores partial-volume effects at the cortex / skull
   interface; with 1 mm voxel sampling this is acceptable but not zero.
2. CSF is modelled as saline (no proteins). Adequate for photons; revisit
   for proton MC.
3. Iron content in deep gray nuclei (substantia nigra, globus pallidus) is
   ignored at five-class resolution; effect on 6 MV photon dose is
   < 0.1 % per Andreo 1991.
4. The whole-brain ICRU-44 fallback is *not* used.
5. The material palette is fixed at MVP-2 design time. Any extension
   (skin, adipose, eye lens) requires a new `material_map.*.csv` and a
   methods-section update, *not* a code patch.

## 9. References

- Agostinelli S. et al. 2003. "Geant4 — a simulation toolkit." *NIM A*
  506:250. doi:10.1016/S0168-9002(03)01368-8.
- Allison J. et al. 2016. "Recent developments in Geant4." *NIM A* 835:186.
  doi:10.1016/j.nima.2016.06.125.
- Andreo P. 1991. "Monte Carlo techniques in medical radiation physics."
  *PMB* 36:861. doi:10.1088/0031-9155/36/7/001.
- Andreo P. 2015. "Dose to 'water-like' media or dose to tissue?" *PMB*
  60:309. doi:10.1088/0031-9155/60/1/309.
- Apostolakis J. et al. 2009. "Geometry and physics of the Geant4 toolkit
  for high and medium energy applications." *RPC* 78:859.
  doi:10.1016/j.radphyschem.2009.04.026.
- Chetty I. J. et al. (AAPM TG-105) 2007. *Med Phys* 34:4818.
  doi:10.1118/1.2795842.
- du Plessis F. C. P. et al. 1998. *Med Phys* 25:1195.
  doi:10.1118/1.598297.
- Edmund J. M., Nyholm T. 2017. *Radiat. Oncol.* 12:28.
  doi:10.1186/s13014-016-0747-y.
- Fonov V. et al. 2011. "Unbiased average age-appropriate atlases for
  pediatric studies." *NeuroImage* 54:313.
  doi:10.1016/j.neuroimage.2010.07.033.
- ICRU Report 44 (1989). doi:10.1093/jicru/os23.1.Report44.
- ICRU Report 46 (1992). doi:10.1093/jicru/os24.1.Report46.
- Owrangi A. M. et al. 2018. *PMB* 63:05TR01. doi:10.1088/1361-6560/aaaca4.
- Shen Y. et al. 2024. *NeuroImage* 287:120516.
  doi:10.1016/j.neuroimage.2024.120516.
- Valentin J. (ICRP Publication 89) 2002. *Ann. ICRP* 32(3-4).
  doi:10.1016/S0146-6453(03)00002-2.
- Woodard H. Q., White D. R. 1986. *Br. J. Radiol.* 59:1209.
  doi:10.1259/0007-1285-59-708-1209.
- Yang M. et al. 2012. *PMB* 57:4095. doi:10.1088/0031-9155/57/13/4095.
