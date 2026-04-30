"""C++/Python interchange format for MVP-2 dose maps.

This module implements the on-disk contract documented in
``docs/CPP_PYTHON_INTERFACE.md``: the Geant4 simulation core writes a flat
binary ``.bin`` payload (float32, row-major, X-fastest) plus a JSON sidecar
that carries shape, spacing, origin, direction matrix, the equivalent
NIfTI RAS affine, units, primary count, RNG seed, Geant4 version, and the
physics-list identifier. The Python side wraps this pair back into a
NIfTI image for the analytics pipeline.

The format is intentionally minimal so that the C++ side does not need to
link ITK or nifticlib. The orientation flip (LPS at the C++ boundary →
RAS in the NIfTI) is performed entirely in Python, so the simulation
core can stay agnostic about NIfTI conventions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

DOSE_ARTEFACT_VERSION = "1.0"
DOSE_ARTEFACT_DTYPE = np.float32

REQUIRED_SIDECAR_FIELDS = (
    "version",
    "shape",
    "affine_ras",
    "units",
    "n_primaries",
    "seed",
    "geant4_version",
    "physics_list",
)


def write_dose_artefact(
    dose_array: np.ndarray,
    affine_ras: np.ndarray,
    metadata: dict[str, Any],
    bin_path: str | Path,
    json_path: str | Path,
) -> dict[str, Any]:
    """Write a dose map as the MVP-2 ``.bin`` + ``.json`` artefact pair.

    Parameters
    ----------
    dose_array
        3D array of voxel doses in Gy. Cast to ``float32`` row-major
        (X-fastest, matching ITK's buffer convention and Geant4's
        ``G4PhantomParameterisation`` copy-number layout
        ``i + nx*j + nx*ny*k``).
    affine_ras
        4x4 NIfTI affine in RAS+ world space (the same convention used
        by the rest of the pipeline). The C++ side stores spacing /
        origin / direction in LPS; this affine is the post-conversion
        RAS form.
    metadata
        Dict with at least ``n_primaries`` (int), ``seed`` (int),
        ``geant4_version`` (str), ``physics_list`` (str). Optional keys
        are passed through verbatim.
    bin_path, json_path
        Output paths. Parent directories are created if missing.

    Returns
    -------
    The sidecar dict actually written, including the binary's sha256
    (useful for run manifests).
    """
    if dose_array.ndim != 3:
        msg = f"dose_array must be 3D; got {dose_array.ndim}D"
        raise ValueError(msg)
    affine_ras = np.asarray(affine_ras, dtype=np.float64)
    if affine_ras.shape != (4, 4):
        msg = f"affine_ras must be 4x4; got {affine_ras.shape}"
        raise ValueError(msg)

    payload = np.ascontiguousarray(dose_array.astype(DOSE_ARTEFACT_DTYPE))

    bin_path = Path(bin_path)
    json_path = Path(json_path)
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    payload.tofile(str(bin_path))

    sidecar = {
        "version": DOSE_ARTEFACT_VERSION,
        "shape": list(payload.shape),
        "affine_ras": affine_ras.tolist(),
        "units": metadata.get("units", "Gy"),
        "n_primaries": int(metadata["n_primaries"]),
        "seed": int(metadata["seed"]),
        "geant4_version": str(metadata["geant4_version"]),
        "physics_list": str(metadata["physics_list"]),
        "bin_sha256": _sha256_file(bin_path),
        "dtype": "float32",
        "byte_order": "little",
        "storage_order": "row-major X-fastest",
    }
    for extra_key, extra_value in metadata.items():
        if extra_key not in sidecar and extra_key not in {"units"}:
            sidecar[extra_key] = extra_value

    json_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    return sidecar


def read_dose_artefact(
    bin_path: str | Path,
    json_path: str | Path,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Read the artefact pair and return ``(dose_array, affine_ras, sidecar)``.

    The bin's sha256 is recomputed and compared against the value in the
    sidecar; mismatch raises ``ValueError`` so silent corruption cannot
    propagate into a downstream report.
    """
    bin_path = Path(bin_path)
    json_path = Path(json_path)

    sidecar = json.loads(json_path.read_text(encoding="utf-8"))
    missing = [field for field in REQUIRED_SIDECAR_FIELDS if field not in sidecar]
    if missing:
        msg = f"dose artefact sidecar is missing required fields: {missing}"
        raise ValueError(msg)

    expected_sha = sidecar.get("bin_sha256")
    actual_sha = _sha256_file(bin_path)
    if expected_sha is not None and expected_sha != actual_sha:
        msg = (
            "dose artefact bin sha256 mismatch: "
            f"sidecar says {expected_sha}, file is {actual_sha}"
        )
        raise ValueError(msg)

    shape = tuple(sidecar["shape"])
    affine = np.asarray(sidecar["affine_ras"], dtype=np.float64)
    array = np.fromfile(str(bin_path), dtype=DOSE_ARTEFACT_DTYPE)
    if array.size != int(np.prod(shape)):
        msg = (
            f"dose artefact bin size mismatch: expected {int(np.prod(shape))} "
            f"voxels, got {array.size}"
        )
        raise ValueError(msg)
    return array.reshape(shape), affine, sidecar


def dose_artefact_to_nifti(
    bin_path: str | Path,
    json_path: str | Path,
    nifti_path: str | Path,
) -> dict[str, Any]:
    """Convert a ``.bin`` + ``.json`` artefact pair into a NIfTI file.

    Returns the sidecar dict so the caller can copy reproducibility
    metadata (seed, primaries, physics list) into a run manifest.
    """
    array, affine, sidecar = read_dose_artefact(bin_path, json_path)
    nifti_path = Path(nifti_path)
    nifti_path.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(array, affine)
    nib.save(image, str(nifti_path))
    return sidecar


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = [
    "DOSE_ARTEFACT_DTYPE",
    "DOSE_ARTEFACT_VERSION",
    "REQUIRED_SIDECAR_FIELDS",
    "dose_artefact_to_nifti",
    "read_dose_artefact",
    "write_dose_artefact",
]
