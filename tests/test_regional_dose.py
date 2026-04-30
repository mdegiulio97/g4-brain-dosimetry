import math

import numpy as np
import pandas as pd
import pytest

from g4brainatlasdose import (
    REGIONAL_DOSE_COLUMNS,
    compute_regional_dose,
    write_regional_dose_csv,
)


def test_compute_regional_dose_aggregates_non_background_labels():
    dose_map = np.array(
        [
            [
                [0.0, 1.0, 2.0],
                [3.0, 4.0, 5.0],
            ],
        ]
    )
    atlas_labels = np.array(
        [
            [
                [0, 1, 1],
                [2, 2, 0],
            ],
        ]
    )

    regional_dose = compute_regional_dose(dose_map, atlas_labels)

    assert list(regional_dose.columns) == REGIONAL_DOSE_COLUMNS
    assert regional_dose.to_dict(orient="records") == [
        {
            "region_label": 1,
            "region_name": "",
            "mean_dose_Gy": 1.5,
            "std_dose_Gy": math.sqrt(0.5),
            "max_dose_Gy": 2.0,
            "n_voxels": 2,
        },
        {
            "region_label": 2,
            "region_name": "",
            "mean_dose_Gy": 3.5,
            "std_dose_Gy": math.sqrt(0.5),
            "max_dose_Gy": 4.0,
            "n_voxels": 2,
        },
    ]


def test_compute_regional_dose_sorts_region_labels():
    dose_map = np.array([[[10.0, 20.0, 30.0]]])
    atlas_labels = np.array([[[3, 1, 2]]])

    regional_dose = compute_regional_dose(dose_map, atlas_labels)

    assert regional_dose["region_label"].tolist() == [1, 2, 3]


def test_compute_regional_dose_uses_region_names_mapping():
    dose_map = np.array([[[10.0, 20.0]]])
    atlas_labels = np.array([[[1, 2]]])

    regional_dose = compute_regional_dose(
        dose_map,
        atlas_labels,
        region_names={1: "Frontal", 2: "Temporal"},
    )

    assert regional_dose[["region_label", "region_name"]].to_dict(orient="records") == [
        {"region_label": 1, "region_name": "Frontal"},
        {"region_label": 2, "region_name": "Temporal"},
    ]


def test_compute_regional_dose_leaves_missing_region_names_blank():
    dose_map = np.array([[[10.0, 20.0]]])
    atlas_labels = np.array([[[1, 2]]])

    regional_dose = compute_regional_dose(
        dose_map,
        atlas_labels,
        region_names={1: "Frontal"},
    )

    assert regional_dose["region_name"].tolist() == ["Frontal", ""]


def test_compute_regional_dose_rejects_shape_mismatch():
    dose_map = np.zeros((2, 2, 2))
    atlas_labels = np.zeros((2, 2, 3), dtype=int)

    with pytest.raises(ValueError, match="same shape"):
        compute_regional_dose(dose_map, atlas_labels)


def test_compute_regional_dose_rejects_non_3d_atlas_labels():
    dose_map = np.array([0.0, 1.0])
    atlas_labels = np.array([1, 2])

    with pytest.raises(ValueError, match="3D"):
        compute_regional_dose(dose_map, atlas_labels)


def test_compute_regional_dose_omits_labels_absent_from_atlas():
    dose_map = np.array([[[10.0, 20.0, 30.0]]], dtype=np.float32)
    atlas_labels = np.array([[[1, 2, 0]]], dtype=np.int16)

    regional_dose = compute_regional_dose(
        dose_map,
        atlas_labels,
        region_names={1: "Frontal", 2: "Temporal", 5: "Empty"},
    )

    assert regional_dose["region_label"].tolist() == [1, 2]
    assert "Empty" not in regional_dose["region_name"].tolist()


def test_compute_regional_dose_returns_nan_std_for_single_voxel_regions():
    dose_map = np.array([[[10.0, 20.0]]], dtype=np.float32)
    atlas_labels = np.array([[[1, 2]]], dtype=np.int16)

    regional_dose = compute_regional_dose(dose_map, atlas_labels)

    assert math.isnan(regional_dose.loc[0, "std_dose_Gy"])
    assert math.isnan(regional_dose.loc[1, "std_dose_Gy"])


def test_write_regional_dose_csv_writes_expected_file(tmp_path):
    regional_dose = pd.DataFrame(
        [
            {
                "region_label": 1,
                "region_name": "Frontal",
                "mean_dose_Gy": 1.5,
                "std_dose_Gy": 0.5,
                "max_dose_Gy": 2.0,
                "n_voxels": 2,
            }
        ]
    )
    regional_dose = regional_dose[
        ["n_voxels", "max_dose_Gy", "std_dose_Gy", "mean_dose_Gy", "region_name", "region_label"]
    ]
    output_path = tmp_path / "nested" / "regional_dose.csv"

    write_regional_dose_csv(regional_dose, output_path)

    loaded = pd.read_csv(output_path)
    assert list(loaded.columns) == REGIONAL_DOSE_COLUMNS
    pd.testing.assert_frame_equal(loaded, regional_dose[REGIONAL_DOSE_COLUMNS])
