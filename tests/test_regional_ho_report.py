"""Unit tests for the pure-python helpers of scripts/regional_dose_report_ho.py.

The full script needs a nilearn atlas download; these tests exercise the logic
that does NOT (alignment guard, region table ordering) on synthetic grids.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import regional_dose_report_ho as rep  # noqa: E402


def test_alignment_guard_reports_containment_and_ratio():
    dose = np.zeros((4, 4, 4))
    brain = np.zeros((4, 4, 4), dtype=bool)
    brain[1:3, 1:3, 1:3] = True          # 8 brain voxels
    dose[brain] = 10.0                     # brain dose 10
    dose[~brain] = 1.0                     # air dose 1  -> ratio 10x
    atlas = np.zeros((4, 4, 4), dtype=int)
    atlas[1:3, 1:3, 1:3] = 5               # all 8 atlas voxels inside brain
    atlas[0, 0, 0] = 7                     # 1 atlas voxel outside brain

    g = rep.alignment_guard(dose, brain, atlas, "t")
    assert g["ratio"] == 10.0
    assert abs(g["frac_inside"] - 8 / 9) < 1e-9
    assert g["mean_brain"] == 10.0
    assert g["mean_air"] == 1.0


def test_region_table_sorted_desc_and_excludes_background():
    atlas = np.zeros((3, 3, 3), dtype=int)
    atlas[0] = 1        # 9 voxels, low dose
    atlas[1] = 2        # 9 voxels, high dose
    # plane 2 stays 0 -> background, must be excluded
    dose = np.zeros((3, 3, 3))
    dose[atlas == 1] = 1.0
    dose[atlas == 2] = 5.0

    df = rep.region_table(dose, atlas, {1: "low", 2: "high"})
    assert list(df["region_name"]) == ["high", "low"]     # sorted desc
    assert set(df["region_label"]) == {1, 2}              # no background 0
    assert df.iloc[0]["mean_dose_Gy"] == 5.0


def test_subcortical_skip_contains_generic_envelopes():
    assert "Left Cerebral White Matter" in rep.SUBCORTICAL_SKIP
    assert "Left Thalamus" not in rep.SUBCORTICAL_SKIP
