import numpy as np
import pandas as pd
import pytest

from g4brainatlasdose import compute_regional_dose, write_regional_dose_csv


def test_compute_regional_dose_aggregates_non_background_labels():
    dose_map = np.array(
        [
            [0.0, 1.0, 2.0],
            [3.0, 4.0, 5.0],
        ]
    )
    atlas_labels = np.array(
        [
            [0, 1, 1],
            [2, 2, 0],
        ]
    )

    regional_dose = compute_regional_dose(dose_map, atlas_labels)

    assert list(regional_dose.columns) == [
        "region_label",
        "mean_dose",
        "std_dose",
        "max_dose",
        "n_voxels",
    ]
    assert regional_dose.to_dict(orient="records") == [
        {
            "region_label": 1,
            "mean_dose": 1.5,
            "std_dose": 0.5,
            "max_dose": 2.0,
            "n_voxels": 2,
        },
        {
            "region_label": 2,
            "mean_dose": 3.5,
            "std_dose": 0.5,
            "max_dose": 4.0,
            "n_voxels": 2,
        },
    ]


def test_compute_regional_dose_sorts_region_labels():
    dose_map = np.array([10.0, 20.0, 30.0])
    atlas_labels = np.array([3, 1, 2])

    regional_dose = compute_regional_dose(dose_map, atlas_labels)

    assert regional_dose["region_label"].tolist() == [1, 2, 3]


def test_compute_regional_dose_rejects_shape_mismatch():
    dose_map = np.zeros((2, 2))
    atlas_labels = np.zeros((2, 3), dtype=int)

    with pytest.raises(ValueError, match="same shape"):
        compute_regional_dose(dose_map, atlas_labels)


def test_write_regional_dose_csv_writes_expected_file(tmp_path):
    regional_dose = pd.DataFrame(
        [
            {
                "region_label": 1,
                "mean_dose": 1.5,
                "std_dose": 0.5,
                "max_dose": 2.0,
                "n_voxels": 2,
            }
        ]
    )
    output_path = tmp_path / "nested" / "regional_dose.csv"

    write_regional_dose_csv(regional_dose, output_path)

    loaded = pd.read_csv(output_path)
    pd.testing.assert_frame_equal(loaded, regional_dose)
