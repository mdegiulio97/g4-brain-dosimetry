"""End-to-end test for scripts/add_insert_to_mni152.py on a tiny synthetic .mha
(no Geant4 / no MC): the relabelling, tissue-embedding and CSV extension logic.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import add_insert_to_mni152 as ai  # noqa: E402
from g4brainatlasdose.metaimage_io import read_metaimage, write_metaimage  # noqa: E402


def _make_phantom(path):
    # 7^3 grid: a background air shell (0) with a solid WM(3) core, plus a CSF(1)
    # voxel at the centre that must NOT be carved (only GM/WM are targets).
    labels = np.zeros((7, 7, 7), dtype=np.int16)
    labels[1:6, 1:6, 1:6] = 3           # WM core
    labels[3, 3, 3] = 1                  # a CSF voxel at the centre
    write_metaimage(path, labels, (3.0, 3.0, 3.0), (0.0, 0.0, 0.0), np.eye(3))


def _write_map(path):
    path.write_text(
        "label,material_id,density_g_cm3,description\n"
        "0,G4_AIR,0.001205,air\n1,G4_CSF,1.007,csf\n"
        "2,G4_GRAY_MATTER,1.045,gm\n3,G4_WHITE_MATTER,1.041,wm\n",
        encoding="utf-8")


def test_insert_embeds_in_tissue_only_and_extends_map(tmp_path):
    mha = tmp_path / "in.mha"
    csv = tmp_path / "in.csv"
    out = tmp_path / "out"
    _make_phantom(mha)
    _write_map(csv)

    rc = ai.main(["--in-mha", str(mha), "--in-csv", str(csv), "--preset", "air",
                  "--center", "3", "3", "3", "--half", "1", "1", "1",
                  "--out-dir", str(out)])
    assert rc == 0

    labels, _ = read_metaimage(out / "tissue_labels.mha")
    # new label is max(3)+1 = 4
    assert (labels == 4).sum() > 0
    # the central CSF voxel (label 1) was NOT carved (only GM/WM targeted)
    assert labels[3, 3, 3] == 1
    # background air outside the WM core stays 0 (insert embedded in tissue)
    assert labels[0, 0, 0] == 0
    # extended CSV declares label 4 as air
    map_text = (out / "material_map.csv").read_text(encoding="utf-8")
    assert "4,G4_AIR" in map_text


def test_insert_raises_when_box_has_no_target_tissue(tmp_path):
    mha = tmp_path / "in.mha"
    csv = tmp_path / "in.csv"
    out = tmp_path / "out"
    _make_phantom(mha)
    _write_map(csv)
    # corner is background air only -> no GM/WM -> must refuse
    try:
        ai.main(["--in-mha", str(mha), "--in-csv", str(csv), "--preset", "calc",
                 "--center", "0", "0", "0", "--half", "0", "0", "0",
                 "--out-dir", str(out)])
    except SystemExit:
        return
    raise AssertionError("expected SystemExit for an insert box with no tissue")
