"""Command-line interface for the MVP-1.5 regional dose pipeline."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from g4brainatlasdose.pipeline import run_regional_dose_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the MVP-1.5 pipeline argument parser."""
    parser = argparse.ArgumentParser(
        description="Run the MVP-1.5 regional dose pipeline.",
    )
    parser.add_argument(
        "--dose-map",
        type=Path,
        default=Path("dose_map.nii.gz"),
        help="Path to dose_map.nii.gz.",
    )
    parser.add_argument(
        "--atlas-labels",
        type=Path,
        default=Path("atlas_labels.nii.gz"),
        help="Path to atlas_labels.nii.gz.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("regional_dose.csv"),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--region-names",
        type=Path,
        default=None,
        help="Optional JSON or CSV mapping from region labels to names.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run_regional_dose_pipeline(
            dose_map_path=args.dose_map,
            atlas_labels_path=args.atlas_labels,
            output_path=args.output,
            region_names_path=args.region_names,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(status=2, message=f"error: {exc}\n")

    print(args.output)
    return 0


__all__ = ["build_parser", "main"]
