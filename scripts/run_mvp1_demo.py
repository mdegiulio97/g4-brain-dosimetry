#!/usr/bin/env python3
"""Run a deterministic MVP-1 analytics validation demo.

This script intentionally exercises only the Python analytics layer. It does not
invoke, configure, or require the Geant4 simulation core.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SRC = REPO_ROOT / "python"
if PYTHON_SRC.exists() and str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from g4brainatlasdose.analytics import compute_regional_dose  # noqa: E402
from g4brainatlasdose.dummy_dose import generate_dummy_dose  # noqa: E402
from g4brainatlasdose.qc import compute_qc_summary, render_qc_report_markdown  # noqa: E402
from g4brainatlasdose.report_io import (  # noqa: E402
    write_qc_report_markdown,
    write_regional_dose_csv,
)

DEFAULT_OUTPUT_DIR = Path("reports/mvp1_demo")
DEFAULT_SEED = 20260430
SYNTHETIC_ATLAS_SHAPE = (8, 8, 6)
REGION_NAMES = {
    1: "Synthetic anterior left",
    2: "Synthetic posterior left",
    3: "Synthetic anterior right",
    4: "Synthetic posterior right",
    5: "Synthetic central core",
}


@dataclass(frozen=True)
class DemoOutputs:
    """Output paths written by the MVP-1 demo."""

    output_dir: Path
    regional_csv_path: Path
    qc_report_path: Path
    manifest_path: Path


def generate_synthetic_atlas(seed: int = DEFAULT_SEED) -> np.ndarray:
    """Generate a deterministic 3D synthetic atlas with background and 5 regions."""
    rng = np.random.default_rng(seed)
    shape = SYNTHETIC_ATLAS_SHAPE
    x_idx, y_idx, z_idx = np.indices(shape)
    center = (np.array(shape, dtype=np.float64) - 1.0) / 2.0
    radii = np.array(shape, dtype=np.float64) / 2.2

    normalized_radius = (
        ((x_idx - center[0]) / radii[0]) ** 2
        + ((y_idx - center[1]) / radii[1]) ** 2
        + ((z_idx - center[2]) / radii[2]) ** 2
    )
    brain_mask = normalized_radius <= 1.0

    atlas = np.zeros(shape, dtype=np.int16)
    atlas[brain_mask & (x_idx < center[0]) & (y_idx < center[1])] = 1
    atlas[brain_mask & (x_idx < center[0]) & (y_idx >= center[1])] = 2
    atlas[brain_mask & (x_idx >= center[0]) & (y_idx < center[1])] = 3
    atlas[brain_mask & (x_idx >= center[0]) & (y_idx >= center[1])] = 4

    central_core = (
        brain_mask
        & (np.abs(x_idx - center[0]) <= 1.5)
        & (np.abs(y_idx - center[1]) <= 1.5)
        & (np.abs(z_idx - center[2]) <= 1.0)
    )
    atlas[central_core] = 5

    background_holes = (rng.random(shape) < 0.04) & brain_mask & ~central_core
    atlas[background_holes] = 0
    return atlas


def run_demo(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    seed: int = DEFAULT_SEED,
    timestamp_utc: str | None = None,
) -> DemoOutputs:
    """Run the deterministic MVP-1 demo and write report artifacts."""
    resolved_output_dir = Path(output_dir)
    regional_csv_path = resolved_output_dir / "regional_dose.csv"
    qc_report_path = resolved_output_dir / "qc_report.md"
    manifest_path = resolved_output_dir / "run_manifest.yaml"

    atlas_labels = generate_synthetic_atlas(seed=seed)
    dose_map = generate_dummy_dose(atlas_labels)
    regional_dose = compute_regional_dose(
        dose_map,
        atlas_labels,
        region_names=REGION_NAMES,
    )

    write_regional_dose_csv(regional_dose, regional_csv_path)

    qc_summary = compute_qc_summary(
        dose_map,
        atlas_labels,
        output_csv_path=regional_csv_path,
    )
    write_qc_report_markdown(
        _render_demo_qc_report(
            qc_markdown=render_qc_report_markdown(qc_summary),
            seed=seed,
            atlas_shape=atlas_labels.shape,
        ),
        qc_report_path,
    )

    manifest = _build_manifest(
        seed=seed,
        timestamp_utc=timestamp_utc or _current_utc_timestamp(),
        atlas_labels=atlas_labels,
        output_paths=DemoOutputs(
            output_dir=resolved_output_dir,
            regional_csv_path=regional_csv_path,
            qc_report_path=qc_report_path,
            manifest_path=manifest_path,
        ),
    )
    _write_manifest(manifest, manifest_path)

    return DemoOutputs(
        output_dir=resolved_output_dir,
        regional_csv_path=regional_csv_path,
        qc_report_path=qc_report_path,
        manifest_path=manifest_path,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the MVP-1 demo."""
    parser = argparse.ArgumentParser(
        description="Run the deterministic MVP-1 Python analytics validation demo.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated MVP-1 demo reports.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed used to create the deterministic synthetic atlas.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the MVP-1 demo CLI."""
    args = build_parser().parse_args(argv)
    outputs = run_demo(output_dir=args.output_dir, seed=args.seed)
    print(outputs.output_dir)
    return 0


def _render_demo_qc_report(
    qc_markdown: str,
    seed: int,
    atlas_shape: tuple[int, int, int],
) -> str:
    lines = [
        qc_markdown.rstrip(),
        "",
        "## MVP-1 Demo Inputs",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Synthetic atlas shape | `{atlas_shape}` |",
        f"| Synthetic atlas seed | {seed} |",
        "| Dose source | Deterministic dummy dose generated from atlas labels |",
        "",
    ]
    return "\n".join(lines)


def _build_manifest(
    seed: int,
    timestamp_utc: str,
    atlas_labels: np.ndarray,
    output_paths: DemoOutputs,
) -> dict[str, Any]:
    labels, counts = np.unique(atlas_labels, return_counts=True)
    atlas_label_counts = {int(label): int(count) for label, count in zip(labels, counts, strict=True)}

    return {
        "run": {
            "id": "mvp1_demo",
            "timestamp_utc": timestamp_utc,
            "purpose": "Deterministic validation/demo run for the Python analytics layer.",
        },
        "software": {
            "project": "G4BrainAtlasDose",
            "package_version": _package_version(),
            "geant4_used": False,
        },
        "configuration": {
            "seed": seed,
            "synthetic_atlas_shape": list(atlas_labels.shape),
            "region_names": REGION_NAMES,
        },
        "inputs": {
            "atlas": "generated deterministic synthetic atlas",
            "dose_map": "generated deterministic dummy dose map",
        },
        "synthetic_atlas": {
            "label_counts": atlas_label_counts,
        },
        "outputs": {
            "regional_dose_csv": {"path": str(output_paths.regional_csv_path)},
            "qc_report_md": {"path": str(output_paths.qc_report_path)},
            "run_manifest_yaml": {"path": str(output_paths.manifest_path)},
        },
        "limitations": [
            "Synthetic atlas and dummy dose are not anatomical or physical dose models.",
            "Geant4 simulation, voxel geometry, and particle transport are not exercised.",
        ],
    }


def _write_manifest(manifest: dict[str, Any], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )


def _package_version() -> str | None:
    try:
        return version("g4brainatlasdose")
    except PackageNotFoundError:
        return _pyproject_version()


def _pyproject_version() -> str | None:
    pyproject_path = REPO_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        return None

    with pyproject_path.open("rb") as pyproject_file:
        metadata = tomllib.load(pyproject_file)
    project = metadata.get("project", {})
    package_version = project.get("version")
    return package_version if isinstance(package_version, str) else None


def _current_utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
