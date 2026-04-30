"""Validation helpers for MVP data contracts."""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np

MATERIAL_MAP_REQUIRED_FIELDS = ("label", "material_id", "density_g_cm3")
ATLAS_LABEL_REQUIRED_FIELDS = ("label", "name")

_MATERIAL_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def load_material_map_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate a material-map CSV file."""
    with Path(path).open(newline="", encoding="utf-8") as material_map_file:
        return validate_material_map_rows(csv.DictReader(material_map_file))


def load_atlas_label_table_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate an atlas-label lookup CSV file."""
    with Path(path).open(newline="", encoding="utf-8") as atlas_label_file:
        return validate_atlas_label_rows(csv.DictReader(atlas_label_file))


def validate_material_map_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate material-map CSV rows and return normalized entries."""
    entries: list[dict[str, Any]] = []
    labels: set[int] = set()
    material_ids: set[str] = set()

    for line_number, row in enumerate(rows, start=2):
        if _is_blank_row(row):
            continue

        _require_fields(row, MATERIAL_MAP_REQUIRED_FIELDS, "material map", line_number)
        label = _coerce_non_negative_int(row["label"], "label", line_number)
        material_id = _coerce_material_id(row["material_id"], line_number)
        density = _coerce_positive_float(row["density_g_cm3"], "density_g_cm3", line_number)
        description = _optional_text(row.get("description"))

        if label in labels:
            msg = f"duplicate material map label at line {line_number}: {label}"
            raise ValueError(msg)
        if material_id in material_ids:
            msg = f"duplicate material_id at line {line_number}: {material_id}"
            raise ValueError(msg)

        labels.add(label)
        material_ids.add(material_id)
        entries.append(
            {
                "label": label,
                "material_id": material_id,
                "density_g_cm3": density,
                "description": description,
            }
        )

    if not entries:
        msg = "material map must contain at least one row"
        raise ValueError(msg)
    if 0 not in labels:
        msg = "material map must include label 0 for background"
        raise ValueError(msg)

    return entries


def validate_atlas_label_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate atlas-label table rows and return normalized entries."""
    entries: list[dict[str, Any]] = []
    labels: set[int] = set()

    for line_number, row in enumerate(rows, start=2):
        if _is_blank_row(row):
            continue

        _require_fields(row, ATLAS_LABEL_REQUIRED_FIELDS, "atlas label table", line_number)
        label = _coerce_non_negative_int(row["label"], "label", line_number)
        name = _coerce_required_text(row["name"], "name", line_number)

        if label in labels:
            msg = f"duplicate atlas label at line {line_number}: {label}"
            raise ValueError(msg)

        labels.add(label)
        entries.append(
            {
                "label": label,
                "name": name,
                "hemisphere": _optional_text(row.get("hemisphere")),
                "source": _optional_text(row.get("source")),
            }
        )

    if not entries:
        msg = "atlas label table must contain at least one row"
        raise ValueError(msg)

    return entries


def validate_atlas_label_array(atlas_labels: Any) -> np.ndarray:
    """Validate an atlas label array and return it as a NumPy array."""
    labels = np.asarray(atlas_labels)

    if labels.ndim != 3:
        msg = f"atlas_labels must be a 3D array: got {labels.ndim} dimensions"
        raise ValueError(msg)
    if not np.issubdtype(labels.dtype, np.number):
        msg = "atlas_labels must contain numeric labels"
        raise ValueError(msg)
    if not np.all(np.isfinite(labels)):
        msg = "atlas_labels must contain only finite values"
        raise ValueError(msg)
    if not np.all(labels == np.floor(labels)):
        msg = "atlas_labels must contain only integer-valued labels"
        raise ValueError(msg)
    if np.any(labels < 0):
        msg = "atlas_labels must not contain negative labels"
        raise ValueError(msg)

    return labels


def _require_fields(
    row: Mapping[str, Any],
    required_fields: tuple[str, ...],
    table_name: str,
    line_number: int,
) -> None:
    missing = [field for field in required_fields if field not in row]
    if missing:
        joined = ", ".join(missing)
        msg = f"{table_name} row at line {line_number} is missing required field(s): {joined}"
        raise ValueError(msg)


def _coerce_non_negative_int(value: Any, field_name: str, line_number: int) -> int:
    if isinstance(value, bool):
        msg = f"invalid {field_name} at line {line_number}: {value!r}"
        raise ValueError(msg)

    try:
        label = int(value)
    except (TypeError, ValueError) as exc:
        msg = f"invalid {field_name} at line {line_number}: {value!r}"
        raise ValueError(msg) from exc

    if isinstance(value, float) and not value.is_integer():
        msg = f"{field_name} must be an integer at line {line_number}: {value!r}"
        raise ValueError(msg)
    if label < 0:
        msg = f"{field_name} must be non-negative at line {line_number}: {label}"
        raise ValueError(msg)

    return label


def _coerce_material_id(value: Any, line_number: int) -> str:
    material_id = _coerce_required_text(value, "material_id", line_number)
    if not _MATERIAL_ID_RE.fullmatch(material_id):
        msg = (
            "material_id must start with a letter and contain only letters, "
            f"digits, or underscores at line {line_number}: {material_id!r}"
        )
        raise ValueError(msg)
    return material_id


def _coerce_positive_float(value: Any, field_name: str, line_number: int) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        msg = f"invalid {field_name} at line {line_number}: {value!r}"
        raise ValueError(msg) from exc

    if not math.isfinite(numeric_value) or numeric_value <= 0.0:
        msg = f"{field_name} must be a positive finite value at line {line_number}"
        raise ValueError(msg)

    return numeric_value


def _coerce_required_text(value: Any, field_name: str, line_number: int) -> str:
    text = _optional_text(value)
    if not text:
        msg = f"{field_name} must be non-empty at line {line_number}"
        raise ValueError(msg)
    return text


def _optional_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _is_blank_row(row: Mapping[str, Any]) -> bool:
    return all(value in (None, "") for value in row.values())


__all__ = [
    "ATLAS_LABEL_REQUIRED_FIELDS",
    "MATERIAL_MAP_REQUIRED_FIELDS",
    "load_atlas_label_table_csv",
    "load_material_map_csv",
    "validate_atlas_label_array",
    "validate_atlas_label_rows",
    "validate_material_map_rows",
]
