# MVP-1 Validation Protocol

## Purpose

MVP-1 validates the completed Python analytics layer of G4BrainAtlasDose with a
small, deterministic, synthetic demo run. The protocol demonstrates that the
repository can aggregate voxel-wise dose values by atlas region, emit a regional
CSV report, create a markdown QC report, and record reproducibility metadata in a
run manifest.

This validation package intentionally does not exercise Geant4 geometry,
transport, scoring, or exported simulation dose maps.

## Tested Components

- Synthetic atlas generation in `scripts/run_mvp1_demo.py`.
- Deterministic dummy dose generation via
  `g4brainatlasdose.dummy_dose.generate_dummy_dose`.
- Regional dose aggregation via
  `g4brainatlasdose.analytics.compute_regional_dose`.
- CSV report writing via `g4brainatlasdose.report_io.write_regional_dose_csv`.
- QC summary and markdown report generation via `g4brainatlasdose.qc`.
- Run manifest creation with timestamp, seed, package version when available,
  synthetic input metadata, and output paths.

## Assumptions

- MVP-1 is a Python analytics validation release, not a physics validation
  release.
- The synthetic atlas is a deterministic 3D label array with background label
  `0` and five labeled regions.
- The dummy dose map is deterministic and generated from the synthetic atlas
  labels; it is not a physical dose field.
- Atlas and dose arrays have the same shape.
- Region label `0` is background and is excluded from regional dose rows.
- The package version is read from installed package metadata when available,
  with `pyproject.toml` used as a source-tree fallback.

## Procedure

From the repository root, run:

```bash
python scripts/run_mvp1_demo.py
```

The default output directory is:

```text
reports/mvp1_demo/
```

The deterministic seed can be overridden for exploratory runs:

```bash
python scripts/run_mvp1_demo.py --seed 12345
```

## Expected Outputs

The demo writes the following generated artifacts under `reports/mvp1_demo/`:

- `regional_dose.csv`: one row per non-background synthetic atlas region with
  columns `region_label`, `region_name`, `mean_dose`, `std_dose`, `max_dose`,
  and `n_voxels`.
- `qc_report.md`: markdown QC summary covering region count, labeled voxel
  count, voxel coverage, global dose min/mean/max, output CSV path, and demo
  input metadata.
- `run_manifest.yaml`: reproducibility metadata including timestamp, seed,
  package version when available, synthetic atlas metadata, Geant4 usage status,
  and output paths.

Generated reports are local validation artifacts and are not intended to be
committed unless a future release explicitly designates small example outputs.

## Limitations

- The synthetic atlas is not derived from MRI, MNI152, BrainWeb, or any clinical
  image.
- The dummy dose map is not a Monte Carlo result and must not be interpreted as
  physical or clinical dose.
- Geant4 core code, voxelized geometry construction, material assignment,
  transport physics, and scorer output are outside MVP-1 validation scope.
- The protocol validates deterministic analytics behavior, report generation,
  and basic reproducibility metadata only.
