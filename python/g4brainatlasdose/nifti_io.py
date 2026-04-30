"""Minimal NIfTI array I/O helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np


def load_nifti_array(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Load a NIfTI image and return its voxel data array and affine matrix."""
    image = nib.load(str(path))
    return np.asarray(image.dataobj), np.array(image.affine, copy=True)


def save_nifti_array(path: str | Path, array: Any, affine: Any) -> None:
    """Save a voxel data array and affine matrix as a NIfTI image."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(np.asarray(array), np.asarray(affine))
    nib.save(image, str(output_path))


__all__ = ["load_nifti_array", "save_nifti_array"]
