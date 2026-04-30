from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from g4brainatlasdose import REGIONAL_DOSE_COLUMNS

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_mvp1_demo.py"
SPEC = importlib.util.spec_from_file_location("run_mvp1_demo", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
run_mvp1_demo = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = run_mvp1_demo
SPEC.loader.exec_module(run_mvp1_demo)


def test_generate_synthetic_atlas_is_deterministic_and_has_expected_labels():
    atlas_a = run_mvp1_demo.generate_synthetic_atlas(seed=12345)
    atlas_b = run_mvp1_demo.generate_synthetic_atlas(seed=12345)
    atlas_c = run_mvp1_demo.generate_synthetic_atlas(seed=54321)

    np.testing.assert_array_equal(atlas_a, atlas_b)
    assert atlas_a.shape == run_mvp1_demo.SYNTHETIC_ATLAS_SHAPE
    assert atlas_a.dtype == np.int16
    assert np.unique(atlas_a).tolist() == [0, 1, 2, 3, 4, 5]
    assert not np.array_equal(atlas_a, atlas_c)


def test_run_demo_writes_reports_and_manifest(tmp_path):
    output_dir = tmp_path / "reports" / "mvp1_demo"
    outputs = run_mvp1_demo.run_demo(
        output_dir=output_dir,
        seed=12345,
        timestamp_utc="2026-04-30T12:00:00Z",
    )

    assert outputs.output_dir == output_dir
    assert outputs.regional_csv_path == output_dir / "regional_dose.csv"
    assert outputs.qc_report_path == output_dir / "qc_report.md"
    assert outputs.manifest_path == output_dir / "run_manifest.yaml"

    regional_dose = pd.read_csv(outputs.regional_csv_path)
    assert list(regional_dose.columns) == REGIONAL_DOSE_COLUMNS
    assert regional_dose["region_label"].tolist() == [1, 2, 3, 4, 5]
    assert regional_dose["region_name"].tolist() == [
        "Synthetic anterior left",
        "Synthetic posterior left",
        "Synthetic anterior right",
        "Synthetic posterior right",
        "Synthetic central core",
    ]
    assert (regional_dose["n_voxels"] > 0).all()

    qc_report = outputs.qc_report_path.read_text(encoding="utf-8")
    assert "# MVP QC Report" in qc_report
    assert "| Number of regions | 5 |" in qc_report
    assert "| Synthetic atlas seed | 12345 |" in qc_report

    manifest = yaml.safe_load(outputs.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run"]["id"] == "mvp1_demo"
    assert manifest["run"]["timestamp_utc"] == "2026-04-30T12:00:00Z"
    assert manifest["software"]["package_version"] == run_mvp1_demo._package_version()
    assert manifest["software"]["geant4_used"] is False
    assert manifest["configuration"]["seed"] == 12345
    assert manifest["configuration"]["synthetic_atlas_shape"] == [8, 8, 6]
    assert manifest["outputs"]["regional_dose_csv"]["path"] == str(outputs.regional_csv_path)
    assert manifest["outputs"]["qc_report_md"]["path"] == str(outputs.qc_report_path)
    assert manifest["outputs"]["run_manifest_yaml"]["path"] == str(outputs.manifest_path)


def test_main_writes_default_named_outputs_in_requested_directory(tmp_path, capsys):
    output_dir = tmp_path / "demo"

    exit_code = run_mvp1_demo.main(["--output-dir", str(output_dir), "--seed", "20260430"])

    assert exit_code == 0
    assert capsys.readouterr().out == f"{output_dir}\n"
    assert (output_dir / "regional_dose.csv").is_file()
    assert (output_dir / "qc_report.md").is_file()
    assert (output_dir / "run_manifest.yaml").is_file()
