#!/usr/bin/env python3
"""Generate Harvard-Oxford ``atlas_labels.csv`` files from an FSL install.

The script consumes the FSL Harvard-Oxford XML descriptors and the
corresponding ``maxprob-thr25-1mm`` NIfTI volumes, then emits two CSV files
that conform to ``docs/ATLAS_LABELS_SCHEMA.md``:

- ``atlas_labels_cortical.csv``    (48 cortical regions, label 1..48)
- ``atlas_labels_subcortical.csv`` (21 subcortical compartments, label 1..21)

The two files are kept separate because the cortical and subcortical
maxprob volumes both reuse label values 1..21 — putting them in a single
CSV would collide.

Usage
-----

    # Auto-detect from $FSLDIR (typical research workstation)
    python scripts/build_atlas_labels.py --output-dir configs/atlases

    # Or point at a specific install
    python scripts/build_atlas_labels.py \\
        --fsldir /usr/local/fsl \\
        --output-dir configs/atlases

    # Override the threshold variant (default: maxprob-thr25-1mm)
    python scripts/build_atlas_labels.py \\
        --variant maxprob-thr50-1mm \\
        --output-dir configs/atlases

References: see ``docs/HARVARD_OXFORD_SETUP.md``.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# nibabel is a runtime dependency of g4brainatlasdose; importing here lets the
# script work even when run outside the installed package.
import nibabel as nib

ATLAS_LABEL_CSV_FIELDS = ("label", "name", "hemisphere", "source")

TISSUE_KEYWORDS = ("Cerebral White Matter", "Cerebral Cortex", "Lateral Ventricle")
HO_SOURCE = "Harvard-Oxford (FSL); Center for Morphometric Analysis, MGH"


@dataclass(frozen=True)
class AtlasSpec:
    """One Harvard-Oxford atlas (cortical or subcortical) on disk."""

    name: str
    xml_relpath: Path
    nifti_relpath: Path
    output_filename: str


def build_atlas_specs(variant: str) -> list[AtlasSpec]:
    return [
        AtlasSpec(
            name="cortical",
            xml_relpath=Path("data/atlases/HarvardOxford-Cortical.xml"),
            nifti_relpath=Path(f"data/atlases/HarvardOxford/HarvardOxford-cort-{variant}.nii.gz"),
            output_filename="atlas_labels_cortical.csv",
        ),
        AtlasSpec(
            name="subcortical",
            xml_relpath=Path("data/atlases/HarvardOxford-Subcortical.xml"),
            nifti_relpath=Path(f"data/atlases/HarvardOxford/HarvardOxford-sub-{variant}.nii.gz"),
            output_filename="atlas_labels_subcortical.csv",
        ),
    ]


def hemisphere_for(name: str) -> str:
    if name.startswith("Left "):
        return "L"
    if name.startswith("Right "):
        return "R"
    return "Bilateral"


def is_tissue_compartment(name: str) -> bool:
    return any(keyword in name for keyword in TISSUE_KEYWORDS)


def parse_xml_labels(xml_path: Path) -> dict[int, str]:
    """Parse an FSL atlas XML and return ``{label_value: region_name}``.

    FSL XML attribute ``index`` is 0-based; voxel intensities in maxprob
    NIfTI volumes equal ``index + 1`` (with 0 reserved for background).
    """
    if not xml_path.exists():
        msg = f"FSL atlas XML not found: {xml_path}"
        raise FileNotFoundError(msg)
    tree = ET.parse(xml_path)
    return {
        int(elem.attrib["index"]) + 1: (elem.text or "").strip()
        for elem in tree.getroot().findall("./data/label")
    }


def validate_volume_against_xml(
    atlas_name: str,
    nifti_path: Path,
    labels: dict[int, str],
) -> None:
    """Ensure every nonzero voxel value in the NIfTI exists in the XML."""
    if not nifti_path.exists():
        msg = f"FSL atlas NIfTI not found: {nifti_path}"
        raise FileNotFoundError(msg)
    volume = nib.load(str(nifti_path)).get_fdata().astype(int)
    present = set(np.unique(volume).tolist()) - {0}
    missing = present - set(labels)
    if missing:
        msg = (
            f"{atlas_name}: voxel values {sorted(missing)} appear in the "
            f"maxprob volume but are not declared in the XML."
        )
        raise ValueError(msg)


def write_atlas_csv(
    output_path: Path,
    labels: dict[int, str],
    source: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=ATLAS_LABEL_CSV_FIELDS)
        writer.writeheader()
        for label_value in sorted(labels):
            name = labels[label_value]
            writer.writerow(
                {
                    "label": label_value,
                    "name": name,
                    "hemisphere": hemisphere_for(name),
                    "source": source,
                }
            )


def discover_fsldir(arg_fsldir: str | None) -> Path:
    if arg_fsldir is not None:
        return Path(arg_fsldir).expanduser().resolve()
    env_value = os.environ.get("FSLDIR")
    if env_value:
        return Path(env_value).expanduser().resolve()
    msg = (
        "FSLDIR is not set and --fsldir was not provided. "
        "Install FSL or pass --fsldir /path/to/fsl explicitly."
    )
    raise SystemExit(msg)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Harvard-Oxford atlas_labels CSV files from an FSL install. "
            "See docs/HARVARD_OXFORD_SETUP.md for context."
        ),
    )
    parser.add_argument(
        "--fsldir",
        default=None,
        help="FSL install directory (default: $FSLDIR environment variable).",
    )
    parser.add_argument(
        "--variant",
        default="maxprob-thr25-1mm",
        help=(
            "Harvard-Oxford NIfTI variant suffix. Default: 'maxprob-thr25-1mm'. "
            "Other useful values: 'maxprob-thr0-1mm', 'maxprob-thr50-1mm', "
            "'maxprob-thr25-2mm'."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("configs/atlases"),
        help="Directory to write the CSV files in (created if missing).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fsldir = discover_fsldir(args.fsldir)
    specs = build_atlas_specs(args.variant)

    summary: list[dict[str, Any]] = []
    for spec in specs:
        xml_path = fsldir / spec.xml_relpath
        nifti_path = fsldir / spec.nifti_relpath

        labels = parse_xml_labels(xml_path)
        validate_volume_against_xml(spec.name, nifti_path, labels)

        output_path = args.output_dir / spec.output_filename
        write_atlas_csv(output_path, labels, source=HO_SOURCE)
        summary.append(
            {
                "atlas": spec.name,
                "labels": len(labels),
                "csv": str(output_path),
                "nifti": str(nifti_path),
            }
        )

    for entry in summary:
        print(
            f"{entry['atlas']:<12s} {entry['labels']:>3d} labels  ->  {entry['csv']}",
            file=sys.stdout,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
