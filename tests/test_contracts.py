from pathlib import Path

import numpy as np
import pytest

from g4brainatlasdose.contracts import (
    load_atlas_label_table_csv,
    load_material_map_csv,
    validate_atlas_label_array,
    validate_atlas_label_rows,
    validate_material_map_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_example_contract_files_are_valid():
    material_map = load_material_map_csv(
        REPO_ROOT / "configs" / "examples" / "material_map.example.csv"
    )
    atlas_labels = load_atlas_label_table_csv(
        REPO_ROOT / "configs" / "examples" / "atlas_labels.example.csv"
    )

    assert material_map[0] == {
        "label": 0,
        "material_id": "air",
        "density_g_cm3": 0.001205,
        "description": "synthetic background compartment",
    }
    assert atlas_labels[0]["label"] == 0
    assert atlas_labels[0]["name"] == "Background"


def test_validate_material_map_rows_normalizes_values():
    rows = [
        {
            "label": "0",
            "material_id": "air",
            "density_g_cm3": "0.001205",
            "description": " background ",
        },
        {
            "label": "1",
            "material_id": "soft_tissue",
            "density_g_cm3": "1.04",
            "description": "",
        },
    ]

    assert validate_material_map_rows(rows) == [
        {
            "label": 0,
            "material_id": "air",
            "density_g_cm3": 0.001205,
            "description": "background",
        },
        {
            "label": 1,
            "material_id": "soft_tissue",
            "density_g_cm3": 1.04,
            "description": "",
        },
    ]


def test_validate_material_map_rows_rejects_duplicate_labels():
    rows = [
        {"label": 0, "material_id": "air", "density_g_cm3": 0.001205},
        {"label": 0, "material_id": "water", "density_g_cm3": 1.0},
    ]

    with pytest.raises(ValueError, match="duplicate material map label"):
        validate_material_map_rows(rows)


def test_validate_material_map_rows_rejects_invalid_density():
    rows = [{"label": 0, "material_id": "air", "density_g_cm3": 0.0}]

    with pytest.raises(ValueError, match="positive finite"):
        validate_material_map_rows(rows)


def test_validate_material_map_rows_requires_background_label():
    rows = [{"label": 1, "material_id": "soft_tissue", "density_g_cm3": 1.04}]

    with pytest.raises(ValueError, match="label 0"):
        validate_material_map_rows(rows)


def test_validate_atlas_label_rows_normalizes_values():
    rows = [
        {"label": "0", "name": " Background ", "hemisphere": "", "source": None},
        {"label": "1", "name": "Synthetic Region", "hemisphere": "left"},
    ]

    assert validate_atlas_label_rows(rows) == [
        {"label": 0, "name": "Background", "hemisphere": "", "source": ""},
        {"label": 1, "name": "Synthetic Region", "hemisphere": "left", "source": ""},
    ]


def test_validate_atlas_label_rows_rejects_duplicate_labels():
    rows = [
        {"label": 1, "name": "Synthetic Region A"},
        {"label": 1, "name": "Synthetic Region B"},
    ]

    with pytest.raises(ValueError, match="duplicate atlas label"):
        validate_atlas_label_rows(rows)


def test_validate_atlas_label_rows_rejects_empty_name():
    rows = [{"label": 1, "name": "  "}]

    with pytest.raises(ValueError, match="name must be non-empty"):
        validate_atlas_label_rows(rows)


def test_validate_atlas_label_rows_rejects_float_labels():
    rows = [{"label": 1.5, "name": "Synthetic Region"}]

    with pytest.raises(ValueError, match="must be an integer"):
        validate_atlas_label_rows(rows)


def test_validate_atlas_label_array_accepts_3d_integer_values():
    atlas_labels = np.array([[[0, 1], [2, 3]]], dtype=np.int16)

    validated = validate_atlas_label_array(atlas_labels)

    np.testing.assert_array_equal(validated, atlas_labels)


@pytest.mark.parametrize(
    ("atlas_labels", "message"),
    [
        (np.array([[0, 1], [2, 3]]), "3D"),
        (np.array([[["not-a-label"]]]), "numeric"),
        (np.array([[[0.0, 1.5]]]), "integer-valued"),
        (np.array([[[0, -1]]]), "negative"),
    ],
)
def test_validate_atlas_label_array_rejects_invalid_arrays(atlas_labels, message):
    with pytest.raises(ValueError, match=message):
        validate_atlas_label_array(atlas_labels)
