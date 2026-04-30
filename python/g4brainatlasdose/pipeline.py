"""MVP-1.5 regional dose pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from g4brainatlasdose.analytics import compute_regional_dose
from g4brainatlasdose.mapping_io import load_region_names
from g4brainatlasdose.nifti_io import load_nifti_array
from g4brainatlasdose.report_io import write_regional_dose_csv


def run_regional_dose_pipeline(
    dose_map_path: str | Path = "dose_map.nii.gz",
    atlas_labels_path: str | Path = "atlas_labels.nii.gz",
    output_path: str | Path = "regional_dose.csv",
    region_names_path: str | Path | None = None,
) -> pd.DataFrame:
    """Load inputs, compute regional dose analytics, and write the CSV report."""
    dose_map, _dose_affine = load_nifti_array(dose_map_path)
    atlas_labels, _atlas_affine = load_nifti_array(atlas_labels_path)
    region_names = load_region_names(region_names_path) if region_names_path is not None else None

    regional_dose = compute_regional_dose(
        dose_map,
        atlas_labels,
        region_names=region_names,
    )
    write_regional_dose_csv(regional_dose, output_path)
    return regional_dose


__all__ = ["run_regional_dose_pipeline"]
