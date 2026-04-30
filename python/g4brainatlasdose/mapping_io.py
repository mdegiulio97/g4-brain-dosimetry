"""Region-name mapping file loaders."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

LABEL_FIELDS = ("region_label", "label", "id")
NAME_FIELDS = ("region_name", "name")


def load_region_names(path: str | Path) -> dict[int, str]:
    """Load region-label names from a JSON or CSV mapping file."""
    mapping_path = Path(path)
    suffix = mapping_path.suffix.lower()

    if suffix == ".json":
        return _parse_mapping(json.loads(mapping_path.read_text(encoding="utf-8")))
    if suffix == ".csv":
        with mapping_path.open(newline="", encoding="utf-8") as mapping_file:
            return _parse_rows(csv.DictReader(mapping_file))

    msg = f"region names mapping must be a JSON or CSV file: {mapping_path}"
    raise ValueError(msg)


def _parse_mapping(raw_mapping: Any) -> dict[int, str]:
    if isinstance(raw_mapping, Mapping):
        return _coerce_items(raw_mapping.items())
    if isinstance(raw_mapping, list):
        return _parse_rows(raw_mapping)

    msg = "JSON region names mapping must be an object or a list of row objects"
    raise ValueError(msg)


def _parse_rows(rows: Iterable[Mapping[str, Any]]) -> dict[int, str]:
    names: dict[int, str] = {}
    for row in rows:
        if _is_blank_row(row):
            continue
        label = _coerce_label(_pick(row, LABEL_FIELDS, "region label"))
        name = _coerce_name(_pick(row, NAME_FIELDS, "region name"))
        _store_unique(names, label, name)
    return names


def _coerce_items(items: Iterable[tuple[Any, Any]]) -> dict[int, str]:
    names: dict[int, str] = {}
    for raw_label, raw_name in items:
        label = _coerce_label(raw_label)
        name = _coerce_name(raw_name)
        _store_unique(names, label, name)
    return names


def _pick(row: Mapping[str, Any], fields: tuple[str, ...], field_description: str) -> Any:
    for field in fields:
        if field in row:
            return row[field]

    msg = f"region names mapping rows must include a {field_description} column"
    raise ValueError(msg)


def _coerce_label(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        msg = f"invalid region label in mapping: {value!r}"
        raise ValueError(msg) from exc


def _coerce_name(value: Any) -> str:
    return "" if value is None else str(value)


def _store_unique(names: dict[int, str], label: int, name: str) -> None:
    if label in names:
        msg = f"duplicate region label in mapping: {label}"
        raise ValueError(msg)
    names[label] = name


def _is_blank_row(row: Mapping[str, Any]) -> bool:
    return all(value in (None, "") for value in row.values())


__all__ = ["load_region_names"]
