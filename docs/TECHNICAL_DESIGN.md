# Technical Design

## Purpose

G4BrainAtlasDose is structured as a reproducible research codebase for Monte Carlo
brain dosimetry on MRI-derived phantoms with atlas-based regional reporting.

The first software baseline intentionally excludes a complete Geant4 simulation
implementation. It defines the contracts needed to make later simulation runs
auditable: configuration files, run manifests, package layout, tests, and technical
documentation.

## MVP plan

1. Define data contracts for phantom images, tissue labels, material maps, dose maps,
   atlas labels, and run manifests.
2. Add Python CLI entry points for validation, preprocessing, postprocessing, and
   report generation.
3. Implement lightweight validation for YAML configs and run manifests.
4. Add deterministic atlas-region aggregation tests using tiny synthetic arrays.
5. Add a Geant4 smoke target that builds without embedding project data.
6. Connect the Python preprocessing outputs to the Geant4 input contract.
7. Produce dose maps, regional summaries, QC figures, and a final manifest for each
   run.

## Repository contracts

- `python/g4brainatlasdose/`: Python package for validation, preprocessing,
  postprocessing, and report utilities.
- `geant4/`: future C++ Geant4 simulation core.
- `configs/`: small, versioned YAML examples and run presets.
- `manifests/`: small run manifest examples and schema-facing documentation.
- `docs/`: scientific scope, technical design, and methodology notes.
- `tests/`: unit and smoke tests using synthetic data only.

Large raw data, derived volumes, Monte Carlo outputs, and generated reports must stay
outside git-tracked source files.

## MVP boundaries

- MRI intensities are anatomical support, not direct electron-density inputs.
- Material assignment is explicit and model-based.
- The first irradiation setup should be simple and deterministic enough for smoke
  testing.
- Regional reporting starts with Harvard-Oxford style label aggregation.
- Clinical treatment planning behavior is out of scope.
