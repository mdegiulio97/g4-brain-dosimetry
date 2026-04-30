"""Analytics utilities for regional dose reporting."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REGIONAL_DOSE_COLUMNS = [
    "region_label",
    "region_name",
    "mean_dose",
    "std_dose",
    "max_dose",
    "n_voxels",
]


def compute_regional_dose(
    dose_map: Any,
    atlas_labels: Any,
    region_names: Mapping[int, str] | None = None,
) -> pd.DataFrame:
    """Aggregate a dose map by atlas region labels.

    Label 0 is treated as background and excluded from the returned table.
    Missing region names are represented as empty strings.
    """
    dose_array = np.asarray(dose_map, dtype=float)
    label_array = np.asarray(atlas_labels)
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
                "mean_dose": float(np.mean(region_dose)),
                "std_dose": float(np.std(region_dose, ddof=0)),
                "max_dose": float(np.max(region_dose)),
                "n_voxels": int(region_dose.size),
            }
        )

    return pd.DataFrame(rows, columns=REGIONAL_DOSE_COLUMNS)


def write_regional_dose_csv(regional_dose: pd.DataFrame, output_path: str | Path) -> None:
    """Write a regional dose table to CSV without the DataFrame index."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    regional_dose.to_csv(path, columns=REGIONAL_DOSE_COLUMNS, index=False)
