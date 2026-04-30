"""Deterministic synthetic dose generation for MVP smoke runs."""

from __future__ import annotations

from typing import Any

import numpy as np

from g4brainatlasdose.contracts import validate_atlas_label_array


def generate_dummy_dose(atlas_labels: Any) -> np.ndarray:
    """Generate a deterministic synthetic dose map matching an atlas label grid.

    The dummy field is intentionally simple: a normalized voxel-order gradient plus
    a small normalized label component. It is only for pipeline smoke tests and
    demonstrations, not for physical dose modeling.
    """
    labels = validate_atlas_label_array(atlas_labels)
    flat_gradient = np.arange(labels.size, dtype=np.float64).reshape(labels.shape)
    flat_gradient /= max(labels.size - 1, 1)

    max_label = float(np.max(labels))
    label_component = np.zeros(labels.shape, dtype=np.float64)
    if max_label > 0.0:
        label_component = labels.astype(np.float64) / max_label * 0.1

    return (flat_gradient + label_component).astype(np.float32)


__all__ = ["generate_dummy_dose"]
