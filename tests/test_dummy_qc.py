import numpy as np
import pytest

from g4brainatlasdose import (
    QCSummary,
    compute_qc_summary,
    generate_dummy_dose,
    render_qc_report_markdown,
)


def test_generate_dummy_dose_is_deterministic_and_matches_atlas_shape():
    atlas_labels = np.array(
        [
            [[0, 1], [2, 0]],
            [[1, 2], [0, 3]],
        ],
        dtype=np.int16,
    )

    dose_a = generate_dummy_dose(atlas_labels)
    dose_b = generate_dummy_dose(atlas_labels)

    assert dose_a.shape == atlas_labels.shape
    assert dose_a.dtype == np.float32
    np.testing.assert_array_equal(dose_a, dose_b)
    np.testing.assert_allclose(
        dose_a.ravel(),
        np.array(
            [
                0.0,
                1.0 / 7.0 + 1.0 / 3.0 * 0.1,
                2.0 / 7.0 + 2.0 / 3.0 * 0.1,
                3.0 / 7.0,
                4.0 / 7.0 + 1.0 / 3.0 * 0.1,
                5.0 / 7.0 + 2.0 / 3.0 * 0.1,
                6.0 / 7.0,
                1.1,
            ],
            dtype=np.float32,
        ),
    )


def test_generate_dummy_dose_rejects_non_3d_atlas_labels():
    with pytest.raises(ValueError, match="3D"):
        generate_dummy_dose(np.array([0, 1, 2]))


def test_compute_qc_summary_returns_minimal_metrics():
    dose_map = np.array([[[0.0, 1.0], [2.0, 3.0]]], dtype=np.float32)
    atlas_labels = np.array([[[0, 1], [2, 2]]], dtype=np.int16)

    summary = compute_qc_summary(
        dose_map,
        atlas_labels,
        output_csv_path="reports/regional_dose.csv",
    )

    assert summary == QCSummary(
        number_of_regions=2,
        total_labeled_voxels=3,
        voxel_coverage=0.75,
        global_dose_min=0.0,
        global_dose_mean=1.5,
        global_dose_max=3.0,
        output_csv_path="reports/regional_dose.csv",
    )


def test_render_qc_report_markdown_includes_required_fields():
    summary = QCSummary(
        number_of_regions=2,
        total_labeled_voxels=3,
        voxel_coverage=0.75,
        global_dose_min=0.0,
        global_dose_mean=1.5,
        global_dose_max=3.0,
        output_csv_path="reports/regional_dose.csv",
    )

    report = render_qc_report_markdown(summary)

    assert "| Number of regions | 2 |" in report
    assert "| Total labeled voxels | 3 |" in report
    assert "| Voxel coverage | 0.750000 (75.00%) |" in report
    assert "| Global dose min | 0 |" in report
    assert "| Global dose mean | 1.5 |" in report
    assert "| Global dose max | 3 |" in report
    assert "| Output CSV path | `reports/regional_dose.csv` |" in report
