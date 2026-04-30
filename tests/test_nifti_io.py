import nibabel as nib
import numpy as np
import pytest

from g4brainatlasdose.nifti_io import load_nifti_array, save_nifti_array


def test_load_nifti_array_returns_data_and_affine(tmp_path):
    array = np.arange(24, dtype=np.float32).reshape((2, 3, 4))
    affine = np.array(
        [
            [2.0, 0.0, 0.0, 10.0],
            [0.0, 3.0, 0.0, 20.0],
            [0.0, 0.0, 4.0, 30.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    path = tmp_path / "synthetic.nii.gz"
    nib.save(nib.Nifti1Image(array, affine), str(path))

    loaded_array, loaded_affine = load_nifti_array(path)

    np.testing.assert_array_equal(loaded_array, array)
    np.testing.assert_array_equal(loaded_affine, affine)


def test_save_nifti_array_writes_loadable_file(tmp_path):
    array = np.array(
        [
            [[0, 1], [2, 3]],
            [[4, 5], [6, 7]],
        ],
        dtype=np.int16,
    )
    affine = np.array(
        [
            [1.0, 0.0, 0.0, -1.0],
            [0.0, 1.0, 0.0, -2.0],
            [0.0, 0.0, 1.5, -3.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    path = tmp_path / "nested" / "synthetic_labels.nii.gz"

    save_nifti_array(path, array, affine)

    reloaded = nib.load(str(path))
    np.testing.assert_array_equal(np.asarray(reloaded.dataobj), array)
    np.testing.assert_array_equal(reloaded.affine, affine)


def test_save_and_load_nifti_array_round_trip(tmp_path):
    array = np.linspace(0.0, 1.0, num=8, dtype=np.float32).reshape((2, 2, 2))
    affine = np.eye(4)
    path = tmp_path / "round_trip.nii"

    save_nifti_array(path, array, affine)
    loaded_array, loaded_affine = load_nifti_array(path)

    np.testing.assert_array_equal(loaded_array, array)
    np.testing.assert_array_equal(loaded_affine, affine)


def test_round_trip_preserves_affine_with_high_precision(tmp_path):
    array = np.zeros((2, 2, 2), dtype=np.float32)
    affine = np.array(
        [
            [1.234567, 0.0, 0.0, -98.765],
            [0.0, 2.345678, 0.0, 12.345],
            [0.0, 0.0, 0.987654, -45.678],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    path = tmp_path / "precise_affine.nii.gz"

    save_nifti_array(path, array, affine)
    _loaded_array, loaded_affine = load_nifti_array(path)

    np.testing.assert_allclose(loaded_affine, affine, atol=1e-6)


def test_round_trip_preserves_ras_orientation(tmp_path):
    array = np.zeros((2, 2, 2), dtype=np.float32)
    ras_affine = np.diag([1.0, 1.0, 1.0, 1.0])
    path = tmp_path / "ras.nii.gz"

    save_nifti_array(path, array, ras_affine)
    _loaded_array, loaded_affine = load_nifti_array(path)

    assert nib.aff2axcodes(loaded_affine) == ("R", "A", "S")


def test_round_trip_preserves_lps_orientation(tmp_path):
    array = np.zeros((2, 2, 2), dtype=np.float32)
    lps_affine = np.diag([-1.0, -1.0, 1.0, 1.0])
    path = tmp_path / "lps.nii.gz"

    save_nifti_array(path, array, lps_affine)
    _loaded_array, loaded_affine = load_nifti_array(path)

    assert nib.aff2axcodes(loaded_affine) == ("L", "P", "S")


@pytest.mark.parametrize("spacing", [(1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (0.5, 0.75, 1.5)])
def test_round_trip_preserves_voxel_spacing(tmp_path, spacing):
    array = np.zeros((2, 2, 2), dtype=np.float32)
    affine = np.diag([*spacing, 1.0])
    path = tmp_path / f"spacing_{spacing[0]}_{spacing[1]}_{spacing[2]}.nii.gz"

    save_nifti_array(path, array, affine)
    _loaded_array, loaded_affine = load_nifti_array(path)

    np.testing.assert_allclose(nib.affines.voxel_sizes(loaded_affine), spacing, atol=1e-6)
