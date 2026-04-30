# Material Map Schema

## Purpose

The MVP-1 material map defines the contract between tissue labels and simulation
material assumptions. It is metadata only: it does not contain voxels, images,
patient data, or derived neuroimaging data.

The material map is intentionally independent of the Geant4 implementation. Later
Geant4 code may consume this contract, but MVP-1 only defines and validates the
Python-side file shape.

## File Format

- Format: CSV with a single header row.
- Encoding: UTF-8.
- Filename convention: `material_map.csv`.
- Example: `configs/examples/material_map.example.csv`.

Required columns:

| Column | Type | Rule |
| --- | --- | --- |
| `label` | integer | Non-negative tissue label value. Labels must be unique. Label `0` is reserved for background or air. |
| `material_id` | string | Stable ASCII identifier using letters, digits, and underscores. Values must be unique. |
| `density_g_cm3` | float | Positive mass density in grams per cubic centimeter. |

Optional columns:

| Column | Type | Rule |
| --- | --- | --- |
| `description` | string | Human-readable note for the modeling assumption. |

## Semantics

- `label` values must match the integer values in the tissue-label image.
- The map is exhaustive for labels that will be simulated. Unknown labels should
  fail validation before simulation setup.
- Density values are explicit modeling assumptions and should be cited in run
  documentation when used for scientific results.
- MVP-1 does not define elemental composition, mixtures, production cuts, or
  Geant4 material construction.

## Validation Rules

A valid material map:

1. contains at least one row;
2. contains the required columns;
3. has unique non-negative integer labels;
4. includes label `0`;
5. has unique non-empty `material_id` values;
6. uses strictly positive finite `density_g_cm3` values.

The example file in `configs/examples/` is synthetic and exists only to exercise
the contract. It must not be treated as a real tissue model.
