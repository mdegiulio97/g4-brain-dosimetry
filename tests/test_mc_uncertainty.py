"""Tests for the Monte Carlo statistical-uncertainty layer:
g4score_io (parsing Sum(x^2)/N + per-voxel/region/ratio uncertainty) and
analytics.compute_regional_dose_mc.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import g4score_io as gio  # noqa: E402
from g4brainatlasdose.analytics import (  # noqa: E402
    REGIONAL_DOSE_MC_COLUMNS, compute_regional_dose_mc)

HEADER = "# iX, iY, iZ, total(value) [Gy], total(val^2), entry\n"


def test_voxel_rel_unc_matches_known_dump_voxel():
    # Real corner voxel from reports/scoping_mc/dose_0.060MeV_bone.txt.
    ru = gio.voxel_rel_unc(1.451349972747815e-08, 2.123928020458567e-17, 28)
    assert abs(float(ru) - 0.2599) < 1e-3


def test_voxel_rel_unc_nan_guards():
    assert np.isnan(gio.voxel_rel_unc(1.0, 1.0, 1))      # N<2
    assert np.isnan(gio.voxel_rel_unc(0.0, 0.0, 10))     # s<=0
    assert np.isnan(gio.voxel_rel_unc(1.0, np.nan, 10))  # missing sumsq


def _write_dump(path, rows, five_col=True):
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEADER if five_col else "# iX, iY, iZ, dose\n")
        for (i, j, k, s, q, n) in rows:
            if five_col:
                f.write(f"{i},{j},{k},{s:.6e},{q:.6e},{n}\n")
            else:
                f.write(f"{i},{j},{k},{s:.6e}\n")


def test_full_reader_and_backward_compat(tmp_path):
    p = tmp_path / "d.txt"
    rows = [(0, 0, 0, 1e-8, 2e-17, 20), (0, 0, 1, 2e-8, 5e-17, 40)]
    _write_dump(p, rows)
    # backward-compatible 2-tuple
    dose, shape = gio.read_score_dump(str(p))
    assert shape == (1, 1, 2)
    assert dose[0, 0, 1] == 2e-8
    # full reader carries sumsq + n
    d = gio.read_score_dump_full(str(p))
    assert d.shape == (1, 1, 2)
    assert d.sumsq[0, 0, 1] == 5e-17
    assert d.n[0, 0, 0] == 20


def test_four_column_dump_tolerated(tmp_path):
    p = tmp_path / "old.txt"
    _write_dump(p, [(0, 0, 0, 1e-8, 0, 0)], five_col=False)
    d = gio.read_score_dump_full(str(p))
    assert d.dose[0, 0, 0] == 1e-8
    assert np.isnan(d.sumsq[0, 0, 0]) and np.isnan(d.n[0, 0, 0])


def test_ratio_with_unc_independent_propagation():
    r, sr = gio.ratio_with_unc(2.0, 0.1, 1.0, 0.05)
    assert abs(r - 2.0) < 1e-9
    # rel = sqrt(0.05^2 + 0.05^2) = 0.0707 -> sigma = 2*0.0707
    assert abs(sr - 2.0 * np.sqrt(0.05**2 + 0.05**2)) < 1e-9


def test_regional_dose_mc_columns_and_propagation():
    # Region 1: 4 identical voxels, each s=1.0, q with rel unc r0 per voxel.
    # Per voxel var_s = N*q - s^2 chosen so sigma_s = 0.1 (rel 10%).
    # sigma_s^2 = 0.01 -> (N*q - s^2)/(N-1) = 0.01. Pick N=2 -> 2q-1=0.01 -> q=0.505.
    dose = np.ones((2, 2, 1))
    sumsq = np.full((2, 2, 1), 0.505)
    n = np.full((2, 2, 1), 2.0)
    atlas = np.ones((2, 2, 1), dtype=int)  # single region, 4 voxels
    df = compute_regional_dose_mc(dose, sumsq, n, atlas)
    assert list(df.columns) == REGIONAL_DOSE_MC_COLUMNS
    row = df.iloc[0]
    assert row["n_voxels"] == 4
    assert abs(row["mean_dose_Gy"] - 1.0) < 1e-12
    # sigma(region) = (1/M) sqrt(sum sigma_v^2) = (1/4) sqrt(4*0.01) = 0.25*0.2 = 0.05
    assert abs(row["mc_unc_Gy"] - 0.05) < 1e-9
    assert abs(row["mc_rel_unc"] - 0.05) < 1e-9
    # spatial std is 0 here (all voxels identical) -> distinct from mc_unc
    assert row["std_dose_Gy"] == 0.0
