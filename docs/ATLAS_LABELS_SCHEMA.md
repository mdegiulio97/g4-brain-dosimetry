# Atlas Labels Schema

## Purpose

The MVP-1 atlas labels contract defines how atlas-region labels are represented
for regional dose aggregation. It separates the label image from the label-name
table so that dose aggregation can remain deterministic and auditable.

The repository must not track real atlas volumes, patient images, or derived
neuroimaging data. Only tiny synthetic examples are allowed in `configs/examples/`.

## Atlas Label Image

The atlas label image is the voxel-wise input used during regional dose
aggregation.

Required properties:

- Format: NIfTI (`.nii` or `.nii.gz`).
- Dimensionality: 3D scalar image.
- Values: finite, integer-valued, non-negative labels.
- Background: label `0` is reserved for background and is excluded from regional
  dose summaries.
- Alignment: shape, voxel grid, and affine should match the dose map used for
  aggregation.
- Semantics: each non-zero voxel belongs to one atlas region.

MVP-1 does not support probabilistic atlas maps, overlapping labels, or label
resampling in the regional aggregation step.

## Atlas Label Table

The label table maps integer labels to display names used in regional reports.

- Format: CSV with a single header row.
- Encoding: UTF-8.
- Filename convention: `atlas_labels.csv`.
- Example: `configs/examples/atlas_labels.example.csv`.

Required columns:

| Column | Type | Rule |
| --- | --- | --- |
| `label` | integer | Non-negative atlas label value. Labels must be unique. |
| `name` | string | Non-empty region name. |

Optional columns:

| Column | Type | Rule |
| --- | --- | --- |
| `hemisphere` | string | Optional hemisphere or laterality descriptor. |
| `source` | string | Optional provenance note for the label definition. |

## Validation Rules

A valid atlas label table:

1. contains at least one row;
2. contains the required columns;
3. has unique non-negative integer labels;
4. uses non-empty region names.

A valid atlas label image:

1. is 3D;
2. contains only finite values;
3. contains only integer-valued labels;
4. contains no negative labels.

The example file in `configs/examples/` is synthetic and does not reproduce a
real atlas lookup table.
