"""Analytics utilities for regional dose reporting."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from g4brainatlasdose.contracts import validate_atlas_label_array

REGIONAL_DOSE_COLUMNS = [
    "region_label",
    "region_name",
    "mean_dose_Gy",
    "std_dose_Gy",
    "max_dose_Gy",
    "n_voxels",
]

# compute_regional_dose_mc adds the two MC-statistical columns to the base set.
# std_dose_Gy is SPATIAL spread across a region's voxels; mc_unc_Gy / mc_rel_unc
# are the MONTE CARLO statistical error on the region mean (shrinks as 1/sqrt(N)).
# The two are physically distinct and both are reported.
REGIONAL_DOSE_MC_COLUMNS = REGIONAL_DOSE_COLUMNS + ["mc_unc_Gy", "mc_rel_unc"]


def compute_regional_dose(
    dose_map: Any,
    atlas_labels: Any,
    region_names: Mapping[int, str] | None = None,
) -> pd.DataFrame:
    """Aggregate a dose map by atlas region labels.

    Label 0 is treated as background and excluded from the returned table.
    Missing region names are represented as empty strings. The ``std_dose_Gy``
    column reports the **sample** standard deviation (``ddof=1``) following
    medical-imaging convention; single-voxel regions get ``NaN`` because the
    sample standard deviation is undefined for n=1.
    """
    dose_array = np.asarray(dose_map, dtype=float)
    label_array = validate_atlas_label_array(atlas_labels)
    names = region_names or {}

    if dose_array.shape != label_array.shape:
        msg = (
            "dose_map and atlas_labels must have the same shape: "
            f"{dose_array.shape} != {label_array.shape}"
        )
        raise ValueError(msg)

    rows = []
    for raw_label in sorted(np.unique(label_array)):
        label = int(raw_label)
        if label == 0:
            continue

        region_dose = dose_array[label_array == raw_label]
        rows.append(
            {
                "region_label": label,
                "region_name": names.get(label, ""),
                "mean_dose_Gy": float(np.mean(region_dose)),
                "std_dose_Gy": float(np.std(region_dose, ddof=1)) if region_dose.size > 1 else float("nan"),
                "max_dose_Gy": float(np.max(region_dose)),
                "n_voxels": int(region_dose.size),
            }
        )

    return pd.DataFrame(rows, columns=REGIONAL_DOSE_COLUMNS)


def compute_regional_dose_mc(
    dose_map: Any,
    sumsq_map: Any,
    n_map: Any,
    atlas_labels: Any,
    region_names: Mapping[int, str] | None = None,
) -> pd.DataFrame:
    """Regional dose table with Monte Carlo statistical uncertainty.

    Adds ``mc_unc_Gy`` (absolute 1-sigma statistical error on the region mean
    dose) and ``mc_rel_unc`` (relative) to the columns of
    :func:`compute_regional_dose`. Inputs ``sumsq_map`` and ``n_map`` are the
    per-voxel Sum(value^2) and entry-count arrays from
    ``read_score_dump_full``; ``dose_map`` is Sum(value).

    Per voxel the accumulated-dose variance is ``(N*Sum(x^2) - s^2)/(N-1)``;
    treating voxels as independent, the region-mean sigma is
    ``sqrt(sum_v var_v) / M``. Voxels with N<2 or non-finite stats contribute 0
    to the variance sum (still counted in the mean); this is the standard
    history-by-history / TG-105 estimator. Distinct from ``std_dose_Gy`` (spatial
    spread, which does not shrink with more histories).
    """
    dose_array = np.asarray(dose_map, dtype=float)
    sumsq_array = np.asarray(sumsq_map, dtype=float)
    n_array = np.asarray(n_map, dtype=float)
    label_array = validate_atlas_label_array(atlas_labels)
    names = region_names or {}

    for arr, nm in ((sumsq_array, "sumsq_map"), (n_array, "n_map")):
        if arr.shape != dose_array.shape:
            msg = f"{nm} and dose_map must have the same shape: {arr.shape} != {dose_array.shape}"
            raise ValueError(msg)
    if dose_array.shape != label_array.shape:
        msg = (
            "dose_map and atlas_labels must have the same shape: "
            f"{dose_array.shape} != {label_array.shape}"
        )
        raise ValueError(msg)

    rows = []
    for raw_label in sorted(np.unique(label_array)):
        label = int(raw_label)
        if label == 0:
            continue
        sel = label_array == raw_label
        s = dose_array[sel]
        q = sumsq_array[sel]
        nn = n_array[sel]
        m = s.size

        with np.errstate(invalid="ignore", divide="ignore"):
            var_s = (nn * q - s * s) / (nn - 1.0)
        var_s = np.where(np.isfinite(var_s) & (var_s > 0), var_s, 0.0)
        mean = float(np.mean(s))
        mc_unc = float(np.sqrt(var_s.sum()) / m) if m else float("nan")
        mc_rel = float(mc_unc / mean) if mean else float("nan")

        rows.append(
            {
                "region_label": label,
                "region_name": names.get(label, ""),
                "mean_dose_Gy": mean,
                "std_dose_Gy": float(np.std(s, ddof=1)) if m > 1 else float("nan"),
                "max_dose_Gy": float(np.max(s)),
                "n_voxels": int(m),
                "mc_unc_Gy": mc_unc,
                "mc_rel_unc": mc_rel,
            }
        )

    return pd.DataFrame(rows, columns=REGIONAL_DOSE_MC_COLUMNS)
