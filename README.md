# g4-brain-dosimetry

Monte Carlo photon dosimetry on MRI-derived brain phantoms with Geant4, with dose reported by atlas region.

The repository contains a small Geant4 application (C++) and a Python layer around it:

- **Geant4 core** (`geant4/`): water-box and voxelised-phantom geometries, a material factory (NIST materials, Woodard & White brain tissues, mixtures with a density override), selectable electromagnetic physics (`option4`, `option3`, Livermore, Penelope) and command-based dose scoring.
- **Phantom building** (`scripts/`): MNI152 tissue labels → MetaImage (`.mha`, X-fastest voxel order) + material map → voxel phantom; tooling to place a heterogeneity insert inside the anatomy.
- **Sources**: monoenergetic beams, a cited 6 MV spectrum, a parallel or divergent (SSD point source) field, and a 120 kVp spectrum generated with SpekPy.
- **Analytics** (`python/g4brainatlasdose/`): dose-map I/O, Monte Carlo statistical uncertainty per voxel and per region, regional dose aggregation on the Harvard-Oxford atlas, QC reports and run manifests with reproducibility metadata.

Extracted from a private research repository; results under preparation are not included.

## Validation: 6 MV water depth dose

The physics was checked in a 30 cm water cube before any phantom run (`reports/benchmark_mc/REPORT.md`):

- **Cross-physics check**: the same 6 MeV benchmark with three independent electromagnetic models (option4, Livermore, Penelope) gives consistent depth-dose curves.
- **Clinical 6 MV beam**: a cited 6 MV spectrum (Mohan et al.) with a modelled divergent point source at SSD 100 cm, 20 million primaries, compared with BJR Supplement 25 depth-dose data: gamma (2%/2 mm) pass rate 100% over [dmax, 25 cm], mean gamma 0.42.

The BJR-25 reference curve is reconstructed from published landmark values, because the full table is not openly available. The comparison is a consistency check of the transport and the beam model, not a commissioning measurement.

## Repository layout

```
geant4/          C++ application: geometry, materials, physics list, sources, run configs and macros
python/          g4brainatlasdose package: dose I/O, MC uncertainty, regional analytics, QC, CLI
scripts/         phantom building, spectra, benchmark analysis, regional report, Geant4 setup/run helpers
configs/         example atlas-label and material-map files
data/reference/  6 MV and 120 kVp spectra, BJR-25 reference landmarks (with provenance)
docs/            interface contract, material assignment, physics list, atlas setup, voxel phantom
reports/benchmark_mc/  water depth-dose benchmark
tests/           unit tests for the Python layer (no Geant4 needed)
```

## Build and run (Geant4)

Geant4 11.2 from conda-forge, built in WSL Ubuntu or Linux, without root and without Docker:

```bash
bash scripts/setup_geant4_conda.sh               # micromamba env with Geant4 11.2 + compiler, then build
bash scripts/setup_geant4_conda.sh --benchmark   # also run the water depth-dose benchmark

# run any macro with a run config
G4BAD_RUNCONFIG=geant4/run.config.benchmark G4BAD_NPRIM=2000000 \
  bash scripts/run_g4.sh geant4/macros/benchmark_water.mac
```

A `docker/Dockerfile` is provided as an alternative. Monte Carlo dose dumps are regenerable and not committed.

## Python layer

```bash
python -m venv .venv && . .venv/bin/activate      # or: uv venv
pip install -e ".[dev,viz,geant4-prep]"
pytest -q                                          # unit tests, no Geant4 needed
ruff check .
g4brainatlasdose-mvp --help                        # regional-dose CLI
```

## Data and licenses

- MNI152 ICBM 2009c tissue priors and the Harvard-Oxford atlas are downloaded at run time (via nilearn) and are subject to their own licences; they are not redistributed here.
- Spectra and reference landmarks in `data/reference/` carry their provenance and citations in the accompanying files.

## License

Code: MIT (see `LICENSE`).
