import nibabel as nib
import numpy as np

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
