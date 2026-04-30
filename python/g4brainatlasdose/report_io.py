"""CSV report I/O for regional dose outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from g4brainatlasdose.analytics import REGIONAL_DOSE_COLUMNS


def write_regional_dose_csv(regional_dose: pd.DataFrame, output_path: str | Path) -> None:
    """Write a regional dose table to CSV without the DataFrame index."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    regional_dose.to_csv(path, columns=REGIONAL_DOSE_COLUMNS, index=False)


def write_qc_report_markdown(report_markdown: str, output_path: str | Path) -> None:
    """Write a markdown QC report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_markdown, encoding="utf-8")


__all__ = ["write_qc_report_markdown", "write_regional_dose_csv"]
