"""Structural and numerical audit for the final UGP thesis deliverables."""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from PIL import Image
from pypdf import PdfReader

from build_final_thesis import DOCX_PATH, FIGURES, ROOT, verify_repository_values


PDF_PATH = DOCX_PATH.with_suffix(".pdf")
MANIFEST_PATH = ROOT / "deliverables" / "final_thesis_manifest.json"


def _caption_page_map(text: str, label: str) -> dict[int, int]:
    starts = list(re.finditer(rf"{label}\s+(\d+)\.", text))
    result: dict[int, int] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.end():end]
        numbers = re.findall(r"(?<!\d)(\d{1,3})(?!\d)", block)
        if not numbers:
            raise AssertionError(f"No page number found for {label} {match.group(1)}")
        result[int(match.group(1))] = int(numbers[-1])
    return result


def audit() -> dict[str, object]:
    verify_repository_values()
    assert DOCX_PATH.exists() and PDF_PATH.exists()

    document = Document(DOCX_PATH)
    xml = document._element.xml
    all_text = "\n".join(p.text for p in document.paragraphs)
    for table in document.tables:
        for row in table.rows:
            all_text += "\n" + " | ".join(cell.text for cell in row.cells)

    forbidden = (
        "[[PAGE]]",
        "Update field to generate",
        "Error! Reference source not found",
        "Lorem ipsum",
        "TBD",
        "PLACEHOLDER",
        "transformative",
        "multifaceted framework",
        "paradigm shift",
    )
    for token in forbidden:
        assert token.lower() not in all_text.lower(), token

    assert xml.count("SEQ Figure") == 18
    assert xml.count("SEQ Table") == 17
    assert len(document.inline_shapes) == 19  # institute logo + 18 project figures
    assert len(document.tables) == 18  # declaration signatures + 17 numbered data tables

    required_strings = (
        "83,797",
        "40,425",
        "43,372",
        "348 candidate numerical predictors",
        "198 BALANCED predictors",
        "R² = 0.8997",
        "0.9058",
        "0.9154",
        "0.8917",
        "0.0262",
        "0.2640",
        "0.4002",
        "255 provisional",
        "four fixed-composition Co-Cr configurations",
    )
    for token in required_strings:
        assert token in all_text, token

    pdf = PdfReader(str(PDF_PATH))
    assert len(pdf.pages) == 35
    pages = [page.extract_text() or "" for page in pdf.pages]
    assert all(len(text.strip()) > 20 for text in pages), "blank or nearly blank PDF page"

    actual_fig_pages: dict[int, int] = {}
    actual_table_pages: dict[int, int] = {}
    for page_number, text in enumerate(pages[7:], start=8):
        for number in range(1, 19):
            if f"Figure {number}." in text:
                actual_fig_pages[number] = page_number
        for number in range(1, 18):
            if f"Table {number}." in text:
                actual_table_pages[number] = page_number
    assert len(actual_fig_pages) == 18, actual_fig_pages
    assert len(actual_table_pages) == 17, actual_table_pages

    listed_fig_pages = _caption_page_map(pages[3], "Figure")
    listed_table_pages = _caption_page_map(pages[4], "Table")
    assert listed_fig_pages == actual_fig_pages, (listed_fig_pages, actual_fig_pages)
    assert listed_table_pages == actual_table_pages, (listed_table_pages, actual_table_pages)

    toc_text = pages[5] + "\n" + pages[6]
    for heading, page_number in (
        ("Chapter 1: Introduction and Literature Review", 9),
        ("Chapter 2: Material and Methods", 12),
        ("Chapter 3: Results and Discussion", 17),
        ("Chapter 4: Conclusions and Future Work", 33),
        ("References", 35),
    ):
        normalized = re.sub(r"\s+", " ", toc_text)
        assert heading in normalized
        pattern = re.escape(heading) + r".*?" + str(page_number)
        assert re.search(pattern, normalized), (heading, page_number)

    effective_dpi: dict[str, float] = {}
    figure_shapes = list(document.inline_shapes)[1:]
    assert len(figure_shapes) == len(FIGURES)
    for shape, (key, relative, _) in zip(figure_shapes, FIGURES):
        with Image.open(ROOT / relative) as image:
            width_in = shape.width / 914400
            height_in = shape.height / 914400
            effective_dpi[key] = round(min(image.width / width_in, image.height / height_in), 1)
            assert image.width >= 1200 and image.height >= 700, (key, image.size)
            assert effective_dpi[key] >= 300, (key, effective_dpi[key])

    manifest = {
        "docx": str(DOCX_PATH),
        "pdf": str(PDF_PATH),
        "page_count": len(pdf.pages),
        "figure_count": 18,
        "table_count": 17,
        "authors": [
            {"name": "Abhinav Choudhary", "roll": "23145102"},
            {"name": "Yuvraj Singh", "roll": "23145101"},
            {"name": "Ashish Gautam", "roll": "23145017"},
        ],
        "toc_pages_verified": True,
        "figure_list_pages_verified": True,
        "table_list_pages_verified": True,
        "all_pdf_pages_nonblank": True,
        "core_repository_values_verified": True,
        "minimum_effective_figure_dpi": min(effective_dpi.values()),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
