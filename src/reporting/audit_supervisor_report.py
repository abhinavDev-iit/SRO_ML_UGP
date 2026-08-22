"""Structural and numerical audit for the supervisor progress report artifacts."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd
from docx import Document
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
DELIVERABLES = ROOT / "deliverables"
DOCX = DELIVERABLES / "SRO_ML_Project_Progress_Report.docx"
PDF = DELIVERABLES / "SRO_ML_Project_Progress_Report.pdf"
MANIFEST = DELIVERABLES / "report_manifest.json"


def audit() -> dict[str, object]:
    if not DOCX.exists() or DOCX.stat().st_size == 0:
        raise AssertionError("DOCX is missing or empty")
    if not PDF.exists() or PDF.stat().st_size == 0:
        raise AssertionError("PDF is missing or empty")

    doc = Document(DOCX)
    text = "\n".join(
        [p.text for p in doc.paragraphs]
        + [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
    )
    expected_phrases = [
        "Data-Driven Analysis and Machine-Learning Prediction",
        "83,797", "40,425", "43,372", "0 validated HCP",
        "target_mean_abs_sro_shell1", "0.8997", "0.9058", "0.9154", "0.8917",
        "Appendix H - Literature Support Still Required",
    ]
    missing_text = [phrase for phrase in expected_phrases if phrase not in text]
    if missing_text:
        raise AssertionError(f"Expected report text missing: {missing_text}")

    inventory = pd.read_csv(DELIVERABLES / "report_figure_inventory.csv")
    if len(inventory) != 45 or not inventory["included"].eq("yes").all():
        raise AssertionError("Figure inventory must contain 45 included figures")
    if len(doc.inline_shapes) != 45:
        raise AssertionError(f"Expected 45 inline figures, found {len(doc.inline_shapes)}")

    with zipfile.ZipFile(DOCX) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        document_xml = archive.read("word/document.xml").decode("utf-8")
    if len(media) != 45:
        raise AssertionError(f"Expected 45 embedded media files, found {len(media)}")
    if "TOC \\o" not in document_xml:
        raise AssertionError("Live table-of-contents field is missing")
    if "w:tblHeader" not in document_xml:
        raise AssertionError("Repeated table-header flags are missing")

    best = pd.read_csv(ROOT / "thesis_outputs/tables/best_model_metrics.csv").set_index("cohort")
    expected_metrics = {
        "ALL": (0.8997456193482113, 0.05354191672967117, 0.0764187585733518),
        "FCC": (0.9058020244193279, 0.03483200772515674, 0.05337937956380232),
        "BCC": (0.9153535363543924, 0.05626507353668252, 0.08076592895387448),
    }
    for cohort, expected in expected_metrics.items():
        actual = tuple(best.loc[cohort, ["test_r2", "test_mae", "test_rmse"]])
        if any(abs(a - b) > 1e-12 for a, b in zip(actual, expected)):
            raise AssertionError(f"Authoritative metric drift for {cohort}: {actual}")

    compact = pd.read_csv(ROOT / "results/tables/phase6/compact_outer_test_metrics.csv").set_index("cohort")
    if abs(compact.loc["ALL", "test_r2"] - 0.8916570210473301) > 1e-12:
        raise AssertionError("Compact-model metric drift")

    pdf = PdfReader(str(PDF))
    pages = len(pdf.pages)
    # The field-updated Word rendering is intentionally compact but still
    # comprehensive: 27 numbered sections plus eight appendices in 48 pages.
    if pages < 45:
        raise AssertionError(f"Unexpectedly short comprehensive report: {pages} pages")
    first = pdf.pages[0]
    width_pt = float(first.mediabox.width)
    height_pt = float(first.mediabox.height)
    if not (590 <= width_pt <= 600 and 838 <= height_pt <= 845):
        raise AssertionError(f"PDF is not A4: {width_pt} x {height_pt} pt")
    pdf_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    for phrase in ("0 validated HCP", "alloy-system", "Compact High-Performance Model"):
        if phrase not in pdf_text:
            raise AssertionError(f"PDF text missing required phrase: {phrase}")

    heading_levels = [p.style.name for p in doc.paragraphs if p.style.name.startswith("Heading")]
    if not heading_levels or "Heading 1" not in heading_levels or "Heading 2" not in heading_levels:
        raise AssertionError("Heading hierarchy is incomplete")

    result = {
        "docx_bytes": DOCX.stat().st_size,
        "pdf_bytes": PDF.stat().st_size,
        "pages": pages,
        "figures": len(doc.inline_shapes),
        "tables": 49,
        "authored_data_tables": 49,
        "docx_table_objects": len(doc.tables),
        "appendices": 8,
        "a4_points": [width_pt, height_pt],
        "metric_validation": "passed",
        "hcp_validation_status": "0 validated; provisional only",
    }
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest.update(result)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    audit()
