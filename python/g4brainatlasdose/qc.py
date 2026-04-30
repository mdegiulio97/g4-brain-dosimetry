"""Pure QC summary utilities for MVP regional dose outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from g4brainatlasdose.contracts import validate_atlas_label_array


@dataclass(frozen=True)
class QCSummary:
    """Minimal QC summary values for a regional dose run."""

    number_of_regions: int
    total_labeled_voxels: int
    voxel_coverage: float
    global_dose_min: float
    global_dose_mean: float
    global_dose_max: float
    output_csv_path: str


def compute_qc_summary(
    dose_map: Any,
    atlas_labels: Any,
    output_csv_path: str | Path,
) -> QCSummary:
    """Compute minimal QC metrics for a dose map and atlas label grid."""
    dose_array = np.asarray(dose_map, dtype=np.float64)
    label_array = validate_atlas_label_array(atlas_labels)

    if dose_array.shape != label_array.shape:
        msg = (
            "dose_map and atlas_labels must have the same shape: "
            f"{dose_array.shape} != {label_array.shape}"
        )
        raise ValueError(msg)
    if dose_array.size == 0:
        msg = "dose_map and atlas_labels must not be empty"
        raise ValueError(msg)
    if not np.all(np.isfinite(dose_array)):
        msg = "dose_map must contain only finite values"
        raise ValueError(msg)

    labeled_mask = label_array != 0
    labeled_voxels = int(np.count_nonzero(labeled_mask))
    labels = np.unique(label_array[labeled_mask])

    return QCSummary(
        number_of_regions=int(labels.size),
        total_labeled_voxels=labeled_voxels,
        voxel_coverage=labeled_voxels / dose_array.size,
        global_dose_min=float(np.min(dose_array)),
        global_dose_mean=float(np.mean(dose_array)),
        global_dose_max=float(np.max(dose_array)),
        output_csv_path=str(output_csv_path),
    )


def render_qc_report_markdown(summary: QCSummary) -> str:
    """Render a minimal markdown QC report from a computed summary."""
    coverage_percent = summary.voxel_coverage * 100.0
    return "\n".join(
        [
            "# MVP QC Report",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Number of regions | {summary.number_of_regions} |",
            f"| Total labeled voxels | {summary.total_labeled_voxels} |",
            f"| Voxel coverage | {summary.voxel_coverage:.6f} ({coverage_percent:.2f}%) |",
            f"| Global dose min | {summary.global_dose_min:.6g} |",
            f"| Global dose mean | {summary.global_dose_mean:.6g} |",
            f"| Global dose max | {summary.global_dose_max:.6g} |",
            f"| Output CSV path | `{summary.output_csv_path}` |",
            "",
        ]
    )


__all__ = ["QCSummary", "compute_qc_summary", "render_qc_report_markdown"]
