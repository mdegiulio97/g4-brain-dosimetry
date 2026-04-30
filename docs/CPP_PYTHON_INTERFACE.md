# C++ ↔ Python Interface (MVP-2)

> Closes audit items **L4** ("output dose format and scorer undefined"),
> **L7** ("reference frame conventions"), **D1** ("TECHNICAL_DESIGN
> abstract on the C++/Python contract"), and **D7** ("no smoke test for
> the contract").

## 1. Why a contract document is needed

MVP-1 lives entirely in Python. MVP-2 introduces the Geant4 simulation
core in C++. The two halves communicate only through files on disk.
Without a frozen, citable contract for those files, every change on one
side forces a coordinated change on the other and silent geometric or
unit-of-measure mismatches become trivially possible (audit item P1
already documented one such mismatch in MVP-1).

This document defines:

- the **input** files the C++ core consumes (geometry + materials);
- the **output** files the C++ core produces (dose + reproducibility
  sidecar);
- the **conventions** (units, axes, storage order, RAS↔LPS handling);
- the **smoke test** that lets the Python pipeline be developed and
  CI-ed against a *stub* of Geant4 before any C++ code runs.

The contract is implemented in
`python/g4brainatlasdose/dose_artefact.py` and exercised by
`tests/test_dose_artefact.py`.

## 2. Architectural choice: pure Geant4, file-on-disk boundary

Three integration patterns were considered:

- **Pure Geant4 + file-on-disk boundary** *(adopted)*. The simulation
  core is a stand-alone C++ executable that reads MetaImage + CSV,
  writes a binary dose dump + JSON sidecar. Maximum flexibility,
  minimum cross-language coupling.
- **GATE** (Sarrut et al. 2014, *Med Phys* 41:064301,
  doi:10.1118/1.4871617). Mature ecosystem, native MetaImage / Analyze
  /Interfile readers, macro language. Excellent at doing things the GATE
  authors anticipated; harder to embed bespoke C++ logic. Useful as a
  cross-check (see `docs/PHYSICS_LIST_AND_CONVERGENCE.md` §10).
- **TOPAS** (Perl et al. 2012, *Med Phys* 39:6818, doi:10.1118/1.4758060).
  User-friendly parameter-file interface, DICOM-centric I/O. NIfTI still
  needs conversion. Not chosen because the project is research code, not
  a clinical TPS surrogate.

Plain Geant4 has **no native NIfTI reader**. The pragmatic recipe used
by the medical-physics community is to convert to MetaImage on the
Python side (one-off, before each run) and to read the simple
`.mhd / .mha` text-header format from C++ in <100 LOC, without an ITK
dependency.

## 3. Reference-frame conventions

NIfTI-1 stores an affine to **RAS+** (Right-Anterior-Superior positive)
world space (Cox et al. 2004 NIH/NIfTI-1 spec; nibabel docs,
<https://nipy.org/nibabel/coordinate_systems.html>). ITK and MetaImage
use **LPS+** (Left-Posterior-Superior). The conversion is a deterministic
sign flip on the first two world axes:

```
T_LPS_from_RAS = diag(-1, -1, 1, 1)
```

**Convention used by this project:** the Python side is the only place
that knows about RAS. Anything written for or read from C++ is in LPS.
The Python wrappers `dose_artefact_to_nifti` and the future
`prepare_geometry.py` apply the flip explicitly. The C++ core never
manipulates RAS coordinates and never imports nibabel.

Voxel grid layout:

- **Origin** of the world coordinate system is the **container box
  centre**. Voxel (i, j, k) centre lives at
  `((i + 0.5) · sx − nx · sx / 2, (j + 0.5) · sy − ny · sy / 2,
  (k + 0.5) · sz − nz · sz / 2)` in container coordinates.
- **Storage order:** **row-major, X-fastest**. The flat copy-number used
  by `G4PhantomParameterisation` is `idx = i + nx · j + nx · ny · k`.
  This is the same order as ITK's `GetBufferPointer()` after
  `SimpleITK.WriteImage(.., .mha)`.
- **Spacing units:** mm. **Energy units:** MeV. **Dose units:** Gy.
  Always — the CLHEP defaults (Agostinelli et al. 2003,
  doi:10.1016/S0168-9002(03)01368-8).

## 4. Inputs the C++ core reads

### 4.1 `tissue_labels.mha` (MetaImage)

Generated from `tissue_labels.nii.gz` by a Python pre-processing step:

```python
import SimpleITK as sitk
img = sitk.ReadImage("tissue_labels.nii.gz")  # NIfTI -> RAS internally
sitk.WriteImage(img, "tissue_labels.mha")     # writes LPS to disk
```

SimpleITK silently flips the X/Y signs on read so the on-disk MetaImage
is in LPS, matching ITK's universal convention (Lowekamp et al. 2013,
*Front. Neuroinformatics* 7:45, doi:10.3389/fninf.2013.00045; Yaniv et
al. 2018, *J. Digit. Imaging* 31:290,
doi:10.1007/s10278-017-0037-8). Required round-trip invariants:

```python
back = sitk.ReadImage("tissue_labels.mha")
np.allclose(back.GetSpacing(),   img.GetSpacing(),   atol=1e-6)  # mm
np.allclose(back.GetOrigin(),    img.GetOrigin(),    atol=1e-4)  # mm
np.allclose(back.GetDirection(), img.GetDirection(), atol=1e-6)
```

The label volume must be integer (`MET_SHORT` or `MET_USHORT`), non-
negative, with `0` reserved for background air.

### 4.2 `material_map.csv`

Fixed schema (see `docs/MATERIAL_MAP_SCHEMA.md`):

```
label,material_id,density_g_cm3[,description]
```

Concrete brain instance: `configs/examples/material_map.brain.csv` (see
`docs/MATERIAL_ASSIGNMENT_METHODOLOGY.md` §7). `material_id` resolves
either to a Geant4 NIST entry (e.g. `G4_AIR`,
`G4_BONE_CORTICAL_ICRP`) via `G4NistManager::FindOrBuildMaterial`, or
to a custom name whose elemental composition is hard-coded in the
detector construction (e.g. `G4_GRAY_MATTER`).

The C++ core must verify, at start-up, that
`set(np.unique(tissue_labels)) ⊆ set(material_map.label)` and abort if
the set inclusion fails — silent fallback to background would be a
publication-killing bug.

### 4.3 `run_config.json` (planned, not yet schematised)

A future-MVP file carrying the beam definition (energy, type, particle,
source position, gantry angle), the random seed, and the convergence
target. Out of scope for MVP-2 doc 13; will be specified once the
geometry / source builders settle.

## 5. Outputs the C++ core writes

### 5.1 `dose_map.bin`

- Endianness: **little**.
- Element type: `float32`.
- Layout: **row-major, X-fastest**, length `nx · ny · nz`.
- Units: **Gy**.

This is the simplest possible binary format. C++ writes it with
`std::ofstream::write((char*)buf, sizeof(float)*N)`; Python reads it
with `np.fromfile(path, dtype=np.float32).reshape(shape)`.

### 5.2 `dose_map.json` (sidecar)

Schema (frozen at v1.0; bumped only by an explicit migration):

```json
{
  "version":         "1.0",
  "shape":           [nx, ny, nz],
  "affine_ras":      [[...4x4...]],
  "units":           "Gy",
  "n_primaries":     200000000,
  "seed":            12345,
  "geant4_version":  "11.2.1",
  "physics_list":    "G4EmStandardPhysics_option4",
  "bin_sha256":      "...64 hex chars...",
  "dtype":           "float32",
  "byte_order":      "little",
  "storage_order":   "row-major X-fastest"
}
```

Required fields: `version, shape, affine_ras, units, n_primaries, seed,
geant4_version, physics_list`. Extra fields are passed through verbatim,
useful for downstream metadata (e.g. number of MT workers, walltime,
build SHA).

The `affine_ras` is the **post-RAS-conversion** affine, identical (within
1e-6) to the affine of the input atlas / label NIfTI. The C++ core may
store its native LPS spacing/origin/direction in extra optional fields
(`origin_lps`, `direction_lps`, `spacing`) — those are convenience values
and are *not* used for downstream geometry decisions.

`bin_sha256` lets `read_dose_artefact` detect silent corruption (e.g.
truncated transfers, fileystem flips) before the dose enters the
analytics pipeline.

### 5.3 Why bin + JSON, not NIfTI directly

C++ NIfTI writers exist (`nifticlib`, `itkNiftiImageIO`) but tie the
build to either a one-purpose dependency (nifticlib) or a heavyweight
toolkit (ITK ≈ 80 MB, version-pinning conflicts with Geant4's own VTK /
expat). A flat binary plus a JSON sidecar is dependency-free, trivial
to inspect, and lets Python own the NIfTI semantics. A 50-line Python
wrapper materialises the `.nii.gz` from the artefact pair when the
analytics pipeline wants one.

## 6. Voxel scorer in Geant4

`G4PSDoseDeposit` attached to a `G4MultiFunctionalDetector` over the
parameterised logical volume; the hits map keys are the linear voxel
indices `i + nx · j + nx · ny · k` matching the on-disk layout. See
`docs/PHYSICS_LIST_AND_CONVERGENCE.md` §5 and §6 for the rationale and
for the per-voxel σ estimator (Walters et al. 2002).

## 7. Reproducibility

Geant4 single-thread runs are bit-reproducible given a fixed RNG seed,
fixed physics list, and fixed geometry (Geant4 *Application Developers
Guide* rel. 11.2 §3.6 "Random Number Generation"). The default engine
is `MixMaxRng` since 10.4. Always:

1. Set the seed explicitly: `G4Random::setTheSeed(seed);`.
2. At end-of-run, save the engine state:
   `G4Random::saveEngineStatus("rng_end.dat");`.
3. Persist `seed` in the JSON sidecar.

In multithreaded mode (`G4MTRunManager`) per-event ordering across
workers is not deterministic; for regression tests, use single-thread or
fix `G4MTRunManager::SetEventModulo(1)` plus a fixed worker count
(Allison et al. 2016, *NIM A* 835:186, doi:10.1016/j.nima.2016.06.125,
§3.4).

The Python pipeline carries the sidecar's `seed`, `n_primaries`,
`physics_list`, and `geant4_version` into the run manifest produced by
the analytics layer (see `scripts/run_mvp1_demo.py::_build_manifest`),
so a single `run_manifest.yaml` documents both halves of the
calculation.

## 8. Smoke test (CI gate)

The dummy-dose pattern of MVP-1 (Python emits a deterministic synthetic
NIfTI without invoking Geant4) is preserved for MVP-2 by a *stub
artefact*: `tests/test_dose_artefact.py::test_dose_artefact_drives_regional_pipeline_end_to_end`
performs the full hand-off cycle without any C++ binary:

1. Build a 3D dose array + an RAS affine.
2. `write_dose_artefact(...)` produces `dose_map.bin` + `dose_map.json`,
   imitating what the Geant4 core will write at MVP-2 release time.
3. `dose_artefact_to_nifti(...)` reconstructs `dose_map.nii.gz`.
4. The pipeline ingests it alongside an atlas label NIfTI sharing the
   same affine and produces the regional CSV.

This locks the contract before any C++ exists. When the Geant4 core
arrives, the stub is replaced by the real executable while the CSV-side
tests remain unchanged. The same pattern catches the affine guard
introduced in P1 (`pipeline.py` rejects mismatched affines): if Geant4
ever writes an affine that diverges from the atlas, the pipeline raises
`ValueError` at ingestion time rather than producing a geometrically
wrong report.

Other guards built into `dose_artefact.py`:

- **`bin_sha256` mismatch** → `ValueError` (silent corruption caught).
- **Bin size vs `shape` mismatch** → `ValueError` (truncated writes
  caught).
- **Missing required sidecar fields** → `ValueError` (forward-compat).

## 9. Reference Geant4 examples to mirror

- `examples/extended/medical/DICOM` — voxelised parameterisation,
  per-voxel material lookup (HU-based, but the discrete-label case is
  *simpler*), `G4PhantomParameterisation` plumbing.
- `examples/extended/medical/dosimetry/dnaphysics` — water-phantom PDD
  reference and physics-list comparison framework.
- `examples/extended/runAndEvent/RE03` — multi-functional detector with
  custom primitive scorers, useful for the per-voxel σ accumulator.
- `examples/extended/parameterisations/Par04` — voxel scoring
  parameterised geometry.

## 10. References

- Agostinelli S. et al. 2003. *NIM A* 506:250.
  doi:10.1016/S0168-9002(03)01368-8.
- Allison J. et al. 2016. *NIM A* 835:186. doi:10.1016/j.nima.2016.06.125.
- Apostolakis J. et al. 2008. "Optimization of Geometrical Navigation in
  Geant4." *J. Phys. Conf. Ser.* 119:032004.
  doi:10.1088/1742-6596/119/3/032004.
- Cox R. W. et al. 2004. NIH/NIfTI-1 specification.
- Geant4 Collaboration. *Application Developers Guide* rel. 11.2, 2024.
- Jan S. et al. 2011. *PMB* 56:881. doi:10.1088/0031-9155/56/4/001.
- Lowekamp B. et al. 2013. *Front. Neuroinformatics* 7:45.
  doi:10.3389/fninf.2013.00045.
- Perl J. et al. 2012. *Med Phys* 39:6818. doi:10.1118/1.4758060.
- Sarrut D. et al. 2014. *Med Phys* 41:064301. doi:10.1118/1.4871617.
- Schneider W., Bortfeld T., Schlegel W. 2000. *PMB* 45:459.
  doi:10.1088/0031-9155/45/2/314.
- Walters B. R. B. et al. 2002. *Med Phys* 29:2745.
  doi:10.1118/1.1517611.
- Yaniv Z. et al. 2018. *J. Digit. Imaging* 31:290.
  doi:10.1007/s10278-017-0037-8.
