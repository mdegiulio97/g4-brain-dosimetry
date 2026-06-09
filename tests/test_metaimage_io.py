"""Round-trip and on-disk-order tests for the MetaImage label I/O.

These guard the frozen C++/Python contract: tissue_labels.mha must be written
X-fastest (MetaImage / ITK native, matching G4PhantomParameterisation's copy
number i + nx*j + nx*ny*k), or the Geant4 voxel phantom is silently transposed.
"""
from __future__ import annotations

import numpy as np

from g4brainatlasdose.metaimage_io import read_metaimage, write_metaimage


def _labelled(nx, ny, nz):
    a = np.zeros((nx, ny, nz), dtype=np.int16)
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                a[i, j, k] = i * 100 + j * 10 + k
    return a


def test_round_trip_preserves_labels_and_geometry(tmp_path):
    lab = _labelled(3, 4, 5)
    path = tmp_path / "labels.mha"
    write_metaimage(path, lab, (1.0, 1.5, 2.0), (-10.0, -20.0, -30.0),
                    np.diag([-1.0, -1.0, 1.0]))

    back, hdr = read_metaimage(path)
    assert back.shape == (3, 4, 5)
    assert np.array_equal(back, lab)
    assert hdr["DimSize"] == "3 4 5"
    assert hdr["ElementType"] == "MET_SHORT"
    assert hdr["ElementSpacing"].split() == ["1", "1.5", "2"]


def test_on_disk_order_is_x_fastest(tmp_path):
    nx, ny, nz = 3, 4, 5
    lab = _labelled(nx, ny, nz)
    path = tmp_path / "labels.mha"
    write_metaimage(path, lab, (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))

    raw = path.read_bytes()
    marker = b"ElementDataFile = LOCAL\n"
    data = raw[raw.find(marker) + len(marker):]
    flat = np.frombuffer(data[: nx * ny * nz * 2], dtype="<i2")
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                assert flat[i + nx * j + nx * ny * k] == lab[i, j, k]


def test_dtype_defaults_to_int16_for_labels(tmp_path):
    lab = np.array([[[0, 1]], [[2, 3]]], dtype=np.int64)
    path = tmp_path / "labels.mha"
    write_metaimage(path, lab, (1.0, 1.0, 1.0), (0.0, 0.0, 0.0))
    _, hdr = read_metaimage(path)
    assert hdr["ElementType"] == "MET_SHORT"
