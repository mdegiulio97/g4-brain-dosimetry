"""MVP-1.5 regional dose pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from g4brainatlasdose.analytics import compute_regional_dose
from g4brainatlasdose.dummy_dose import generate_dummy_dose
from g4brainatlasdose.mapping_io import load_region_names
from g4brainatlasdose.nifti_io import load_nifti_array, save_nifti_array
from g4brainatlasdose.qc import compute_qc_summary, render_qc_report_markdown
from g4brainatlasdose.report_io import write_qc_report_markdown, write_regional_dose_csv


def run_regional_dose_pipeline(
    dose_map_path: str | Path = "dose_map.nii.gz",
    atlas_labels_path: str | Path = "atlas_labels.nii.gz",
    output_path: str | Path = "regional_dose.csv",
    region_names_path: str | Path | None = None,
    use_dummy_dose: bool = False,
    dummy_dose_output_path: str | Path | None = None,
    qc_report_path: str | Path | None = None,
) -> pd.DataFrame:
    """Load inputs, compute regional dose analytics, and write the CSV report."""
    atlas_labels, atlas_affine = load_nifti_array(atlas_labels_path)
    should_use_dummy_dose = use_dummy_dose or dummy_dose_output_path is not None
    if should_use_dummy_dose:
        dose_map = generate_dummy_dose(atlas_labels)
        if dummy_dose_output_path is not None:
            save_nifti_array(dummy_dose_output_path, dose_map, atlas_affine)
    else:
        dose_map, dose_affine = load_nifti_array(dose_map_path)
        if not np.allclose(dose_affine, atlas_affine):
            msg = (
                "dose_map and atlas_labels must share the same NIfTI affine matrix; "
                f"got dose affine\n{dose_affine}\nvs atlas affine\n{atlas_affine}"
            )
            raise ValueError(msg)

    region_names = load_region_names(region_names_path) if region_names_path is not None else None

    regional_dose = compute_regional_dose(
        dose_map,
        atlas_labels,
        region_names=region_names,
    )
    write_regional_dose_csv(regional_dose, output_path)
    if qc_report_path is not None:
        summary = compute_qc_summary(
            dose_map,
            atlas_labels,
            output_csv_path=output_path,
        )
        write_qc_report_markdown(render_qc_report_markdown(summary), qc_report_path)
    return regional_dose


__all__ = ["run_regional_dose_pipeline"]
