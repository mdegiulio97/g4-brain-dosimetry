"""Minimal uncompressed MetaImage (.mha) reader/writer for tissue-label volumes.

This is the Python side of the frozen C++/Python contract
(``docs/CPP_PYTHON_INTERFACE.md``): the Geant4 core reads ``tissue_labels.mha``
in **LPS** world space, integer labels, 0 = background.

Conventions (pinned, do not change without changing the C++ reader too):
  * On-disk element order is **X-fastest** (MetaImage / ITK native):
    ``offset = ix + nx*iy + nx*ny*iz``. In numpy that is Fortran order on a
    ``(nx, ny, nz)`` array, so we read/write with ``order="F"``.
    (NB: this differs from ``dose_artefact.py``, which uses C-order on the dose
    payload; the two on-disk orders are independent but each producer/consumer
    pair must agree. The C++ MetaImage reader assumes X-fastest.)
  * ``TransformMatrix`` rows are the LPS direction cosines of the i, j, k axes.
  * ``Offset`` is the LPS world position of voxel (0,0,0) centre.

Only the uncompressed, single-file (``ElementDataFile = LOCAL``) form is
supported, which is all the pipeline needs. Prefer SimpleITK in the build script
when available; this module is the dependency-free fallback and the round-trip
test target.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

# numpy dtype <-> MetaImage ElementType
_DTYPE_TO_MET = {
    "uint8": "MET_UCHAR",
    "int16": "MET_SHORT",
    "uint16": "MET_USHORT",
    "int32": "MET_INT",
    "float32": "MET_FLOAT",
    "float64": "MET_DOUBLE",
}
_MET_TO_DTYPE = {v: k for k, v in _DTYPE_TO_MET.items()}


def write_metaimage(
    path: str | Path,
    labels: np.ndarray,
    spacing: Any,
    offset: Any,
    direction: Any = None,
) -> None:
    """Write a 3D integer label volume as an uncompressed .mha (X-fastest).

    Parameters
    ----------
    labels    : 3D array indexed ``[ix, iy, iz]`` (X first).
    spacing   : (sx, sy, sz) voxel size in mm.
    offset    : (ox, oy, oz) LPS world position of voxel (0,0,0) centre, mm.
    direction : 3x3 LPS direction cosines (rows = i,j,k axes). Identity if None.
    """
    labels = np.asarray(labels)
    if labels.ndim != 3:
        raise ValueError(f"labels must be 3D; got {labels.ndim}D")
    dtype_name = labels.dtype.name
    if dtype_name not in _DTYPE_TO_MET:
        # default to int16 for label maps
        labels = labels.astype(np.int16)
        dtype_name = "int16"

    nx, ny, nz = labels.shape
    sx, sy, sz = (float(v) for v in spacing)
    ox, oy, oz = (float(v) for v in offset)
    if direction is None:
        direction = np.eye(3)
    direction = np.asarray(direction, dtype=float).reshape(3, 3)

    tm = " ".join(f"{v:.10g}" for v in direction.flatten())  # row-major
    header = (
        "ObjectType = Image\n"
        "NDims = 3\n"
        "BinaryData = True\n"
        "BinaryDataByteOrderMSB = False\n"
        "CompressedData = False\n"
        f"TransformMatrix = {tm}\n"
        f"Offset = {ox:.10g} {oy:.10g} {oz:.10g}\n"
        "CenterOfRotation = 0 0 0\n"
        f"ElementSpacing = {sx:.10g} {sy:.10g} {sz:.10g}\n"
        f"DimSize = {nx} {ny} {nz}\n"
        f"ElementType = {_DTYPE_TO_MET[dtype_name]}\n"
        "ElementDataFile = LOCAL\n"
    )

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(header.encode("ascii"))
        # X-fastest on disk == Fortran order of an [ix,iy,iz] array.
        fh.write(np.asfortranarray(labels).tobytes(order="F"))


def read_metaimage(path: str | Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Read an uncompressed LOCAL .mha; return ``(labels[ix,iy,iz], header)``."""
    path = Path(path)
    raw = path.read_bytes()
    # Header is ASCII up to and including the ElementDataFile line.
    marker = b"ElementDataFile = LOCAL\n"
    idx = raw.find(marker)
    if idx < 0:
        raise ValueError("only uncompressed ElementDataFile = LOCAL is supported")
    header_bytes = raw[: idx + len(marker)]
    data_bytes = raw[idx + len(marker):]

    header: dict[str, Any] = {}
    for line in header_bytes.decode("ascii").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            header[k.strip()] = v.strip()

    dims = [int(x) for x in header["DimSize"].split()]
    nx, ny, nz = dims
    met = header["ElementType"]
    if met not in _MET_TO_DTYPE:
        raise ValueError(f"unsupported ElementType {met}")
    dtype = np.dtype(_MET_TO_DTYPE[met])
    if header.get("BinaryDataByteOrderMSB", "False").lower() == "true":
        dtype = dtype.newbyteorder(">")

    count = nx * ny * nz
    flat = np.frombuffer(data_bytes[: count * dtype.itemsize], dtype=dtype)
    # X-fastest on disk -> Fortran reshape into [ix,iy,iz].
    labels = np.reshape(flat, (nx, ny, nz), order="F")
    return np.ascontiguousarray(labels), header


__all__ = ["read_metaimage", "write_metaimage"]
