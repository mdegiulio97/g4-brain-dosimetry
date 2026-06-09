# Stage C2 — Voxelised phantom scaffolding

> **Build status: PENDING VERIFICATION.** The C++ (MetaImage reader, material-map
> loader, `G4PhantomParameterisation` geometry) was written without a Geant4
> toolchain and has **not** been compiled. The Python preprocessing and I/O
> **have** been tested offline. Trust nothing from the C++ until it compiles in
> the Docker image and the Stage-1 water benchmark still passes.

## What this adds

The Stage-1 geometry was a water box + insert. Stage C2 adds the real anatomy
path: a regular voxel grid whose per-voxel material comes from a label image and
a material map, exactly per the frozen contract `docs/CPP_PYTHON_INTERFACE.md`.

```
MNI152 tissue-label NIfTI (RAS)
        │  scripts/build_tissue_labels_mha.py   (RAS → LPS, label validation)
        ▼
tissue_labels.mha (LPS, X-fastest) ──┐
configs/.../material_map.csv ─────────┤  Geant4 (geometry = voxel_phantom)
        │                             ▼
        │            DetectorConstruction::BuildVoxelPhantom
        │              MetaImageIO::Read + MaterialMap::Load
        │              → G4PhantomParameterisation (copy# = i + nx*j + nx*ny*k)
        ▼
   command-based dose mesh (make_phantom_score_macro.py, grid-matched)
        ▼
   dose dump → g4score_io → (TODO) dose_artefact bin/json → analytics pipeline
```

## Files

**Python (tested offline):**
- `python/g4brainatlasdose/metaimage_io.py` — uncompressed `.mha` read/write,
  **X-fastest** on-disk order (verified: `i + nx*j + nx*ny*k`).
- `scripts/build_tissue_labels_mha.py` — NIfTI(RAS) → `.mha`(LPS) with explicit
  flip `diag(-1,-1,1,1)` (numpy backend) or SimpleITK (preferred); validates
  every label is declared in `material_map.csv`.
- `scripts/make_synthetic_phantom.py` — 5-class ellipsoid head, no MNI152/nibabel
  needed; emits `.mha` + `material_map.csv`.
- `scripts/make_phantom_score_macro.py` — emits a scoring macro whose mesh equals
  the phantom grid (so dose voxel ≡ label voxel).
- `tests/test_metaimage_io.py` — round-trip + X-fastest guard.

**C++ (pending build):**
- `geant4/src/MetaImageIO.cc` — `.mha` → labels + dims/spacing/offset.
- `geant4/src/MaterialMap.cc` — `material_map.csv` → label→`G4Material`
  (CSV density is authoritative, passed to `MaterialFactory` as override).
- `geant4/src/DetectorConstruction.cc` — `BuildVoxelPhantom` via
  `G4PhantomParameterisation` + `G4PVParameterised` (regular navigation).

## Conventions pinned (read before changing anything)

- **Voxel order on disk is X-fastest** for the `.mha` (ITK native). The C++
  reader and `G4PhantomParameterisation` copy number both use
  `index = i + nx*j + nx*ny*k`, so they align without transposition. NB: this is
  a *different* on-disk order from `dose_artefact.py`, which uses numpy C-order on
  the dose payload — the two paths are independent but each must stay internally
  consistent.
- **RAS↔LPS**: Python owns RAS (NIfTI); the `.mha` handed to C++ is LPS. The flip
  is `diag(-1,-1,1,1)`. SimpleITK does this natively; the numpy backend does it
  explicitly (and warns on non-diagonal direction cosines, which are only
  round-trip-verified, not yet ITK-cross-checked).
- **Material id aliases**: `MaterialFactory` maps `G4_CSF`, `G4_GRAY_MATTER`,
  `G4_WHITE_MATTER` (used in the frozen CSV, but **not** NIST materials) to the
  custom Woodard&White builders.

## Try the Python chain now (offline)

```bash
python scripts/make_synthetic_phantom.py --out-dir data/derived/synthetic
python scripts/make_phantom_score_macro.py \
    --labels data/derived/synthetic/tissue_labels.mha \
    --out geant4/macros/run_phantom.generated.mac
```

## Run on Geant4 (once built)

```bash
# in run.config: geometry = voxel_phantom + the two paths
export G4BAD_RUNCONFIG=geant4/run.config.example
export G4BAD_ENERGY="6 MeV" G4BAD_NPRIM=2000000 G4BAD_OUT=reports/phantom_mc/dose.txt
./build/geant4/g4brainatlasdose geant4/macros/run_phantom.generated.mac
```

## TODO to close the loop (next increment)
- Map the scored dose dump back to a `dose_map.bin/.json` artefact with the
  **original NIfTI RAS affine** (carry it through), so the existing analytics
  pipeline (`pipeline.py`) produces the regional CSV unchanged.
- Verify scoring-mesh voxel indexing matches the phantom copy-number order on a
  real run (a deliberate asymmetric phantom will catch any transposition).
- Cross-check the numpy `.mha` writer against SimpleITK for non-diagonal affines.
- Real MNI152 + Harvard-Oxford: use `scripts/build_atlas_labels.py` (atlas) and a
  tissue-segmentation NIfTI → `build_tissue_labels_mha.py`.
