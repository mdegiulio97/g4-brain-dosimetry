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

## Repository layout

```text
docs/       Scientific notes, design contracts, methodology
scripts/    Utility scripts and CLI entry points
python/     Python package for preprocessing and postprocessing
geant4/     C++ Geant4 simulation core
configs/    YAML/JSON configuration files
tests/      Unit and smoke tests
data/       Local data folders, mostly ignored by git
outputs/    Simulation outputs, ignored by git
reports/    Generated reports, mostly ignored by git
