"""Smoke tests for the C++/Python dose artefact contract (MVP-2)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from g4brainatlasdose.dose_artefact import (
    REQUIRED_SIDECAR_FIELDS,
    dose_artefact_to_nifti,
    read_dose_artefact,
    write_dose_artefact,
)
from g4brainatlasdose.nifti_io import save_nifti_array
from g4brainatlasdose.pipeline import run_regional_dose_pipeline


def _example_metadata() -> dict[str, object]:
    return {
        "n_primaries": 100,
        "seed": 42,
        "geant4_version": "11.2.1",
        "physics_list": "G4EmStandardPhysics_option4",
    }


def test_write_and_read_dose_artefact_round_trip(tmp_path):
    dose = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    affine = np.diag([1.0, 1.0, 1.0, 1.0])

    sidecar_written = write_dose_artefact(
        dose,
        affine,
        _example_metadata(),
        tmp_path / "dose_map.bin",
        tmp_path / "dose_map.json",
    )

    array, loaded_affine, sidecar = read_dose_artefact(
        tmp_path / "dose_map.bin",
        tmp_path / "dose_map.json",
    )

    np.testing.assert_array_equal(array, dose)
    np.testing.assert_array_equal(loaded_affine, affine)
    assert sidecar == sidecar_written
    for field in REQUIRED_SIDECAR_FIELDS:
        assert field in sidecar
    assert sidecar["units"] == "Gy"
    assert sidecar["dtype"] == "float32"
    assert sidecar["storage_order"] == "row-major X-fastest"


def test_read_dose_artefact_detects_bin_corruption(tmp_path):
    dose = np.zeros((2, 2, 2), dtype=np.float32)
    affine = np.eye(4)
    bin_path = tmp_path / "dose_map.bin"
    json_path = tmp_path / "dose_map.json"
    write_dose_artefact(dose, affine, _example_metadata(), bin_path, json_path)

    # Corrupt the bin payload.
    with bin_path.open("r+b") as fh:
        fh.seek(0)
        fh.write(b"\xff\xff\xff\xff")

    with pytest.raises(ValueError, match="bin sha256 mismatch"):
        read_dose_artefact(bin_path, json_path)


def test_read_dose_artefact_detects_size_mismatch(tmp_path):
    dose = np.zeros((2, 2, 2), dtype=np.float32)
    affine = np.eye(4)
    bin_path = tmp_path / "dose_map.bin"
    json_path = tmp_path / "dose_map.json"
    write_dose_artefact(dose, affine, _example_metadata(), bin_path, json_path)

    # Rewrite the sidecar with a wrong shape but keep the original sha256
    # so the size mismatch is the first failure encountered.
    sidecar = json.loads(json_path.read_text())
    sidecar["shape"] = [3, 3, 3]
    json_path.write_text(json.dumps(sidecar))

    with pytest.raises(ValueError, match="bin size mismatch"):
        read_dose_artefact(bin_path, json_path)


def test_dose_artefact_drives_regional_pipeline_end_to_end(tmp_path):
    """Full smoke test: a stub Geant4 dose artefact survives the pipeline.

    Mimics the MVP-2 hand-off: the C++ core (here: `write_dose_artefact`
    standing in for it) writes the bin/json pair; Python converts to
    NIfTI; ``run_regional_dose_pipeline`` aggregates against an atlas
    label NIfTI sharing the same affine. Ensures the affine guard added
    in P1 stays green when the contract is honoured.
    """
    shape = (2, 2, 4)
    affine = np.array(
        [
            [1.0, 0.0, 0.0, -10.0],
            [0.0, 1.0, 0.0, -20.0],
            [0.0, 0.0, 1.0, -30.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    dose = np.linspace(0.0, 1.0, num=int(np.prod(shape)), dtype=np.float32).reshape(shape)
    atlas_labels = np.zeros(shape, dtype=np.int16)
    atlas_labels[..., 1] = 1
    atlas_labels[..., 2] = 2

    bin_path = tmp_path / "dose_map.bin"
    json_path = tmp_path / "dose_map.json"
    nifti_dose_path = tmp_path / "dose_map.nii.gz"
    atlas_path = tmp_path / "atlas_labels.nii.gz"
    output_path = tmp_path / "regional_dose.csv"

    sidecar_written = write_dose_artefact(
        dose, affine, _example_metadata(), bin_path, json_path
    )
    sidecar = dose_artefact_to_nifti(bin_path, json_path, nifti_dose_path)
    save_nifti_array(atlas_path, atlas_labels, affine)

    regional = run_regional_dose_pipeline(
        dose_map_path=nifti_dose_path,
        atlas_labels_path=atlas_path,
        output_path=output_path,
    )

    loaded = pd.read_csv(output_path, keep_default_na=False)
    assert loaded["region_label"].tolist() == [1, 2]
    assert (regional["n_voxels"] > 0).all()
    # Reproducibility metadata propagated through the sidecar.
    assert sidecar["seed"] == sidecar_written["seed"] == 42
    assert sidecar["physics_list"] == "G4EmStandardPhysics_option4"
