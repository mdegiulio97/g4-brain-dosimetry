# G4BrainAtlasDose

Monte Carlo brain dosimetry on MRI-derived phantoms with atlas-based regional reporting.

## Scientific scope

G4BrainAtlasDose is a research software project for Geant4-based Monte Carlo dose simulation on MRI-derived brain phantoms.

The initial MVP focuses on:

- static MNI152 or BrainWeb-like brain phantom;
- simplified tissue/material assignment;
- voxel-wise dose scoring with Geant4;
- export of dose maps;
- Harvard-Oxford atlas-based regional dose reporting.

## Non-goals

This repository is not a clinical treatment planning system.

It does not compute dose directly from raw MRI intensities. MRI-derived anatomy is used as anatomical support, while tissue classes and material maps are explicit modeling assumptions.

## Planned MVP

1. Prepare anatomical phantom and tissue labels.
2. Convert tissue labels into a material map.
3. Build voxelized Geant4 geometry.
4. Run a simple photon beam simulation.
5. Export dose map.
6. Aggregate dose by atlas regions.
7. Generate QC report and run manifest.

## MVP-1 Python Analytics

The first Python MVP provides pure analytics utilities to aggregate a dose map by
atlas labels and write a regional CSV report. It accepts optional atlas region names
as a `label -> region_name` mapping, can generate a deterministic synthetic dummy
dose map for smoke runs, and can write a minimal markdown QC report. It is
demonstrated with small synthetic arrays in the test suite and does not require
real MRI or Geant4 output data.

The expected report filename is `regional_dose.csv` with columns:
`region_label`, `region_name`, `mean_dose_Gy`, `std_dose_Gy`, `max_dose_Gy`, `n_voxels`.
The `_Gy` suffix marks the dose unit (Gray) for future Geant4 runs; the MVP-1
dummy dose populates these columns with dimensionless synthetic values for
pipeline validation only.

## MVP-1 demo

Run the deterministic Python-only validation demo from the repository root:

```bash
python scripts/run_mvp1_demo.py
```

The demo writes `regional_dose.csv`, `qc_report.md`, and `run_manifest.yaml`
under `reports/mvp1_demo/`. It uses a synthetic atlas and dummy dose map, records
the seed and package version when available, and does not invoke Geant4.

The MVP-1.5 CLI can run the NIfTI-to-regional-CSV pipeline with default local
paths:

```bash
g4brainatlasdose-mvp \
  --dose-map dose_map.nii.gz \
  --atlas-labels atlas_labels.nii.gz \
  --output regional_dose.csv \
  --region-names region_names.csv
```

For a synthetic smoke run without Geant4 dose output, use `--dummy-dose`. Add
`--dummy-dose-output` only when you also want the generated dummy dose map written
as NIfTI:

```bash
g4brainatlasdose-mvp \
  --atlas-labels atlas_labels.nii.gz \
  --dummy-dose \
  --dummy-dose-output outputs/dummy_dose.nii.gz \
  --output reports/regional_dose.csv \
  --qc-report reports/qc_report.md
```

## Repository layout

```text
docs/       Scientific notes, design contracts, methodology
scripts/    Utility scripts and CLI entry points
python/     Python package for preprocessing and postprocessing
geant4/     C++ Geant4 simulation core
configs/    YAML/JSON configuration files
manifests/  Small run manifests and reproducibility metadata examples
tests/      Unit and smoke tests
data/       Local data folders, mostly ignored by git
outputs/    Simulation outputs, ignored by git
reports/    Generated reports, mostly ignored by git
```

Some local data, output, and report directories are intentionally absent from a fresh
checkout because large artifacts should not be tracked in git.
