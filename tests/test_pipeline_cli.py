import numpy as np
import pandas as pd

from g4brainatlasdose.cli import main
from g4brainatlasdose.nifti_io import save_nifti_array
from g4brainatlasdose.pipeline import run_regional_dose_pipeline


def _write_synthetic_inputs(tmp_path):
    dose_map = np.array(
        [
            [[0.0, 1.0], [2.0, 3.0]],
            [[4.0, 5.0], [6.0, 7.0]],
        ],
        dtype=np.float32,
    )
    atlas_labels = np.array(
        [
            [[0, 1], [1, 2]],
            [[2, 2], [0, 3]],
        ],
        dtype=np.int16,
    )
    affine = np.eye(4)
    dose_map_path = tmp_path / "dose_map.nii.gz"
    atlas_labels_path = tmp_path / "atlas_labels.nii.gz"

    save_nifti_array(dose_map_path, dose_map, affine)
    save_nifti_array(atlas_labels_path, atlas_labels, affine)

    return dose_map_path, atlas_labels_path


def test_run_regional_dose_pipeline_writes_csv_with_json_region_names(tmp_path):
    dose_map_path, atlas_labels_path = _write_synthetic_inputs(tmp_path)
    region_names_path = tmp_path / "region_names.json"
    region_names_path.write_text('{"1": "Frontal", "2": "Temporal"}', encoding="utf-8")
    output_path = tmp_path / "reports" / "regional_dose.csv"

    regional_dose = run_regional_dose_pipeline(
        dose_map_path=dose_map_path,
        atlas_labels_path=atlas_labels_path,
        output_path=output_path,
        region_names_path=region_names_path,
    )

    loaded = pd.read_csv(output_path, keep_default_na=False)
    pd.testing.assert_frame_equal(loaded, regional_dose)
    assert loaded[["region_label", "region_name", "mean_dose", "n_voxels"]].to_dict(
        orient="records"
    ) == [
        {"region_label": 1, "region_name": "Frontal", "mean_dose": 1.5, "n_voxels": 2},
        {"region_label": 2, "region_name": "Temporal", "mean_dose": 4.0, "n_voxels": 3},
        {"region_label": 3, "region_name": "", "mean_dose": 7.0, "n_voxels": 1},
    ]


def test_cli_uses_default_mvp_paths_and_csv_region_names(tmp_path, monkeypatch, capsys):
    _write_synthetic_inputs(tmp_path)
    region_names_path = tmp_path / "region_names.csv"
    region_names_path.write_text(
        "label,name\n1,Frontal\n2,Temporal\n3,Occipital\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["--region-names", "region_names.csv"])

    assert exit_code == 0
    assert capsys.readouterr().out == "regional_dose.csv\n"
    loaded = pd.read_csv(tmp_path / "regional_dose.csv", keep_default_na=False)
    assert loaded[["region_label", "region_name", "mean_dose", "n_voxels"]].to_dict(
        orient="records"
    ) == [
        {"region_label": 1, "region_name": "Frontal", "mean_dose": 1.5, "n_voxels": 2},
        {"region_label": 2, "region_name": "Temporal", "mean_dose": 4.0, "n_voxels": 3},
        {"region_label": 3, "region_name": "Occipital", "mean_dose": 7.0, "n_voxels": 1},
    ]
