"""Build the final B.Tech UGP thesis from verified repository artifacts.

The script performs no new scientific analysis. It assembles the supplied IIT
(BHU) template, verified project summaries, compact tables, and existing 300 dpi
figures into an editable DOCX. Word is used separately to refresh fields and
export the QA PDF.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(r"D:\Thesis draft_2026.docx")
DELIVERABLES = ROOT / "deliverables"
DOCX_PATH = DELIVERABLES / "UGP_Final_Thesis_SRO_ML_2026.docx"
TMP_ASSETS = ROOT / "tmp" / "thesis_build" / "assets"

PAGE_WIDTH = Inches(8.5)
PAGE_HEIGHT = Inches(11.0)
MARGIN = Inches(1.0)
CONTENT_WIDTH_IN = 6.45

BLACK = "000000"
LIGHT_GRAY = "E7E6E6"
MID_GRAY = "666666"


FIGURES = [
    (
        "workflow",
        "deliverables/report_assets/workflow_diagram.png",
        "Overall two-semester workflow, from literature-derived pilot data to the validated theoretical database, grouped machine learning, interpretation, and compact recommendations.",
    ),
    (
        "phase_counts",
        "thesis_outputs/figures/phase4/phase_counts_hcp_exclusion.png",
        "Validated phase coverage of the 84k source, showing the FCC/BCC counts and the exclusion of provisional HCP configurations.",
    ),
    (
        "target_distribution",
        "thesis_outputs/figures/phase4/target_distribution_by_phase.png",
        "Distribution of aggregate first-neighbour SRO magnitude for validated FCC and BCC configurations.",
    ),
    (
        "spearman",
        "thesis_outputs/figures/phase4/top_abs_spearman_rho.png",
        "Features with the largest absolute Spearman association with the primary SRO target in the combined dataset.",
    ),
    (
        "redundancy",
        "thesis_outputs/figures/phase4/selected_feature_redundancy_heatmap.png",
        "Redundancy among selected portable descriptors, illustrating why feature filtering was required.",
    ),
    (
        "model_comparison",
        "thesis_outputs/figures/phase5/model_r2_comparison_unified.png",
        "Unified alloy-system-held-out model comparison across the screened model and feature-set combinations.",
    ),
    (
        "split_comparison",
        "thesis_outputs/figures/phase5/random_vs_grouped_validation.png",
        "Unified performance under random-configuration, composition-grouped, and alloy-system-held-out evaluation.",
    ),
    (
        "predicted_unified",
        "thesis_outputs/figures/phase5/predicted_vs_actual_unified.png",
        "Observed and predicted aggregate SRO magnitude for the unified HistGradientBoosting model on held-out alloy systems.",
    ),
    (
        "phase_models",
        "thesis_outputs/figures/phase5/unified_vs_phase_specific.png",
        "Unified-model and phase-specific-model performance on the same held-out FCC and BCC rows.",
    ),
    (
        "feature_sets",
        "thesis_outputs/figures/phase5/feature_set_comparison.png",
        "Grouped-validation comparison of composition-only, phase, initial-structure, and broader feature definitions.",
    ),
    (
        "compact_refinement",
        "thesis_outputs/figures/compact_feature_refinement.png",
        "Training-only grouped-validation curve used to select the compact high-performance feature count.",
    ),
    (
        "importance",
        "thesis_outputs/figures/phase5/feature_importance_unified.png",
        "Held-out permutation importance for the unified BALANCED model, expressed through the increase in prediction error.",
    ),
    (
        "group_ablation",
        "thesis_outputs/figures/feature_group_ablation.png",
        "Change in grouped-validation performance after removing one physical feature group at a time.",
    ),
    (
        "configuration_sensitivity",
        "thesis_outputs/figures/configuration_descriptor_sensitivity.png",
        "Sensitivity of unified performance to selected configuration-sensitive descriptors and descriptor groups.",
    ),
    (
        "fcc_bcc",
        "thesis_outputs/figures/fcc_bcc_final_comparison.png",
        "Comparison of FCC and BCC target magnitudes and phase-specific predictive performance.",
    ),
    (
        "robustness",
        "thesis_outputs/figures/model_robustness.png",
        "Alloy-system-held-out R-squared values across five deterministic group allocations.",
    ),
    (
        "error_decile",
        "thesis_outputs/figures/error_by_target_decile.png",
        "Mean absolute prediction error across deciles of the observed SRO target.",
    ),
    (
        "dft_energy",
        "figures/dft/dft_relative_energy.png",
        "Relative static DFT energies for the selected fixed-composition low- and high-SRO Co-Cr pairs.",
    ),
]
FIG_NO = {key: i for i, (key, _, _) in enumerate(FIGURES, start=1)}


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_repository_values() -> None:
    """Fail early if the compact source-of-truth tables have drifted."""

    phase = {row["phase"]: int(row["observations"]) for row in read_csv("thesis_outputs/tables/phase3/phase_counts.csv")}
    assert phase == {"FCC": 40425, "BCC": 43372, "HCP": 0}

    metrics = {row["cohort"]: row for row in read_csv("thesis_outputs/tables/best_model_metrics.csv")}
    assert math.isclose(float(metrics["ALL"]["test_r2"]), 0.8997456193482113, abs_tol=1e-12)
    assert math.isclose(float(metrics["FCC"]["test_r2"]), 0.9058020244193279, abs_tol=1e-12)
    assert math.isclose(float(metrics["BCC"]["test_r2"]), 0.9153535363543924, abs_tol=1e-12)

    compact = {row["cohort"]: row for row in read_csv("results/tables/phase6/compact_outer_test_metrics.csv")}
    assert int(compact["ALL"]["declared_features"]) == 10
    assert math.isclose(float(compact["ALL"]["test_r2"]), 0.8916570210473301, abs_tol=1e-12)

    phase_cmp = read_csv("thesis_outputs/tables/phase4/phase_target_comparison.csv")[0]
    assert math.isclose(float(phase_cmp["fcc_mean"]), 0.26398980368521835, abs_tol=1e-12)
    assert math.isclose(float(phase_cmp["bcc_mean"]), 0.4002233684621084, abs_tol=1e-12)

    dft = read_csv("results/tables/dft/dft_results.csv")
    assert len(dft) == 4
    assert {row["fid"] for row in dft} == {"gra62121526", "gra62121527", "gra64001864", "gra62121595"}

    for _, relative, _ in FIGURES:
        assert (ROOT / relative).exists(), relative


class ThesisBuilder:
    def __init__(self) -> None:
        self.doc = Document(TEMPLATE)
        self.figure_no = 0
        self.table_no = 0
        self.numbered_counter = 0
        self.logo_path = self._extract_template_logo()
        self._clear_template_body()
        self._configure_document()

    def _extract_template_logo(self) -> Path:
        TMP_ASSETS.mkdir(parents=True, exist_ok=True)
        if not self.doc.inline_shapes:
            raise RuntimeError("Template logo was not found")
        shape = self.doc.inline_shapes[0]
        blip = shape._inline.graphic.graphicData.pic.blipFill.blip
        part = self.doc.part.related_parts[blip.embed]
        suffix = Path(str(part.partname)).suffix or ".png"
        out = TMP_ASSETS / f"iit_bhu_logo{suffix}"
        out.write_bytes(part.blob)
        return out

    def _clear_template_body(self) -> None:
        body = self.doc._body._element
        for child in list(body):
            if child.tag != qn("w:sectPr"):
                body.remove(child)

    def _configure_document(self) -> None:
        section = self.doc.sections[0]
        section.page_width = PAGE_WIDTH
        section.page_height = PAGE_HEIGHT
        section.top_margin = MARGIN
        section.bottom_margin = MARGIN
        section.left_margin = MARGIN
        section.right_margin = MARGIN
        section.header_distance = Inches(0.5)
        section.footer_distance = Inches(0.5)
        section.different_first_page_header_footer = False

        styles = self.doc.styles
        normal = styles["Normal"]
        normal.font.name = "Arial"
        normal.font.size = Pt(11)
        normal.font.color.rgb = RGBColor.from_string(BLACK)
        normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        normal.paragraph_format.line_spacing = 1.15
        normal.paragraph_format.space_after = Pt(5)
        normal.paragraph_format.widow_control = True

        heading_specs = {
            "Heading 1": (19, 18, 8, WD_ALIGN_PARAGRAPH.CENTER),
            "Heading 2": (13, 12, 4, WD_ALIGN_PARAGRAPH.LEFT),
            "Heading 3": (11.5, 8, 3, WD_ALIGN_PARAGRAPH.LEFT),
        }
        for name, (size, before, after, alignment) in heading_specs.items():
            style = styles[name]
            style.font.name = "Arial"
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = RGBColor.from_string(BLACK)
            style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
            style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
            style.paragraph_format.alignment = alignment
            style.paragraph_format.space_before = Pt(before)
            style.paragraph_format.space_after = Pt(after)
            style.paragraph_format.keep_with_next = True

        try:
            caption = styles["Caption"]
        except KeyError:
            caption = styles.add_style("Caption", WD_STYLE_TYPE.PARAGRAPH)
        caption.font.name = "Arial"
        caption.font.size = Pt(9.5)
        caption.font.italic = False
        caption.font.color.rgb = RGBColor.from_string(BLACK)
        caption._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        caption._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        caption.paragraph_format.space_before = Pt(2)
        caption.paragraph_format.space_after = Pt(5)
        caption.paragraph_format.keep_with_next = False

        for toc_name, indent in (("toc 1", 0.0), ("toc 2", 0.22), ("toc 3", 0.44)):
            try:
                style = styles[toc_name]
            except KeyError:
                continue
            style.font.name = "Arial"
            style.font.size = Pt(9.2)
            style.paragraph_format.left_indent = Inches(indent)
            style.paragraph_format.space_after = Pt(0)
            style.paragraph_format.line_spacing = 1.0

        footer = section.footer
        p = footer.paragraphs[0]
        p.clear()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        self._add_field(p, "PAGE")
        for run in p.runs:
            run.font.name = "Arial"
            run.font.size = Pt(10)

        header = section.header
        hp = header.paragraphs[0]
        hp.clear()

        props = self.doc.core_properties
        props.title = "Data-Driven Analysis and Machine-Learning Prediction of Chemical Short-Range Order in Metallic Alloys"
        props.subject = "Final B.Tech UGP thesis"
        props.author = "Abhinav Choudhary; Yuvraj Singh; Ashish Gautam"
        props.keywords = "short-range order, Warren-Cowley, machine learning, FCC, BCC, DFT"
        props.comments = "Built only from verified repository artifacts; no new ML analysis."

        settings = self.doc.settings._element
        update = settings.find(qn("w:updateFields"))
        if update is None:
            update = OxmlElement("w:updateFields")
            settings.append(update)
        update.set(qn("w:val"), "true")

    @staticmethod
    def _add_field(paragraph, instruction: str, placeholder: str = "") -> None:
        run = paragraph.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = instruction
        sep = OxmlElement("w:fldChar")
        sep.set(qn("w:fldCharType"), "separate")
        text = OxmlElement("w:t")
        text.text = placeholder
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        run._r.extend([begin, instr, sep, text, end])

    def front_heading(self, text: str) -> None:
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(16)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(18)
        r.bold = True

    def paragraph(self, text: str, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold_lead: str | None = None) -> None:
        p = self.doc.add_paragraph()
        p.alignment = align
        if bold_lead and text.startswith(bold_lead):
            p.add_run(bold_lead).bold = True
            p.add_run(text[len(bold_lead):])
        else:
            p.add_run(text)

    def bullet(self, text: str) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.18)
        p.paragraph_format.space_after = Pt(3)
        p.add_run("• ")
        p.add_run(text)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def numbered(self, text: str) -> None:
        self.numbered_counter += 1
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.28)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(3)
        p.add_run(f"{self.numbered_counter}. ")
        p.add_run(text)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def page_break(self) -> None:
        self.doc.add_page_break()

    def add_title_page(self) -> None:
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(7)
        r = p.add_run("INDIAN INSTITUTE OF TECHNOLOGY (BHU), VARANASI")
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(13)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(7)
        p.add_run().add_picture(str(self.logo_path), width=Inches(1.15))

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(14)
        r = p.add_run("Data-Driven Analysis and Machine-Learning Prediction of\nChemical Short-Range Order in Metallic Alloys")
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(20)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run("A thesis submitted in partial fulfilment of the requirements for the\nBachelor of Technology degree in Metallurgical Engineering")
        r.font.size = Pt(11)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(5)
        r = p.add_run("Submitted by")
        r.bold = True
        r.font.size = Pt(11)

        for name, roll in (("Abhinav Choudhary (Leader)", "23145102"), ("Yuvraj Singh", "23145101"), ("Ashish Gautam", "23145017")):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            p.add_run(f"{name} — {roll}").font.size = Pt(11)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run("Under the guidance of")
        r.bold = True

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(10)
        r = p.add_run("Prof. Vikas Jindal\nProfessor, Department of Metallurgical Engineering")
        r.font.size = Pt(11)

        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        r = p.add_run("Department of Metallurgical Engineering\nIndian Institute of Technology (BHU), Varanasi\nNovember 2026")
        r.font.size = Pt(11)
        self.page_break()

    def add_declaration(self) -> None:
        self.front_heading("Declaration")
        self.paragraph(
            "We hereby declare that the work presented in this thesis, entitled “Data-Driven Analysis and Machine-Learning Prediction of Chemical Short-Range Order in Metallic Alloys”, was carried out by us under the guidance of Prof. Vikas Jindal, Department of Metallurgical Engineering, Indian Institute of Technology (BHU), Varanasi. The work combines the two semesters of our undergraduate project. The results reported here have not been submitted by us for another degree or diploma. Sources used in the study have been acknowledged in the text and reference list."
        )
        self.paragraph("Place: Varanasi", align=WD_ALIGN_PARAGRAPH.LEFT)
        self.paragraph("Date: November 2026", align=WD_ALIGN_PARAGRAPH.LEFT)

        table = self.doc.add_table(rows=2, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        names = (("Abhinav Choudhary", "23145102"), ("Yuvraj Singh", "23145101"), ("Ashish Gautam", "23145017"))
        for i, (name, roll) in enumerate(names):
            table.cell(0, i).text = "\n\n____________________"
            table.cell(1, i).text = f"{name}\n{roll}"
            for row in table.rows:
                row.cells[i].width = Inches(2.05)
                row.cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                for p in row.cells[i].paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_after = Pt(0)
        self.page_break()

    def add_acknowledgement(self) -> None:
        self.front_heading("Acknowledgement")
        self.paragraph(
            "We express our sincere gratitude to Prof. Vikas Jindal for his guidance, encouragement, and careful review throughout this undergraduate project. His suggestions helped us move from an initial literature-derived dataset to a more rigorous theoretical-data and machine-learning study."
        )
        self.paragraph(
            "We also thank the Department of Metallurgical Engineering, Indian Institute of Technology (BHU), Varanasi, for providing the academic environment and computational support required for the work. We acknowledge the authors who made the alloy datasets, scientific codes, and supporting repositories used in this project available."
        )
        self.paragraph(
            "Finally, we thank our classmates, friends, and family members for their support during the two semesters of the project."
        )
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_before = Pt(30)
        p.add_run("Abhinav Choudhary\nYuvraj Singh\nAshish Gautam").bold = True
        self.page_break()

    def add_front_lists(self) -> None:
        self.front_heading("List of Figures")
        p = self.doc.add_paragraph()
        self._add_field(p, 'TOC \\h \\z \\c "Figure"', "Update field to generate list")
        self.page_break()

        self.front_heading("List of Tables")
        p = self.doc.add_paragraph()
        self._add_field(p, 'TOC \\h \\z \\c "Table"', "Update field to generate list")
        self.page_break()

        self.front_heading("Table of Contents")
        p = self.doc.add_paragraph()
        self._add_field(p, 'TOC \\o "1-3" \\h \\z \\u', "Update field to generate contents")
        self.page_break()

    def add_abstract(self) -> None:
        self.front_heading("Abstract")
        self.paragraph(
            "Chemical short-range order (SRO) describes non-random local atomic arrangements in an alloy. This undergraduate project studied how SRO data can be organized, interpreted, and predicted using data analysis and machine learning. In the first semester, 437 literature-derived observations were standardized across FCC, BCC, and HCP phases. Correlation analysis, principal component analysis, clustering, Random Forest, and XGBoost were applied. Some FCC results appeared promising on individual splits, but cross-validation showed that the small, heterogeneous, and unevenly distributed dataset did not support stable general prediction."
        )
        self.paragraph(
            "The second semester therefore focused on a large theoretical high-entropy-alloy source. The exact label convention was audited, and a leakage-controlled database of 83,797 initial configurations was constructed: 40,425 FCC and 43,372 BCC, with no validated HCP labels. The primary target, target_mean_abs_sro_shell1, is the mean absolute first-neighbour Warren–Cowley coefficient over all unique unlike-element pairs in one configuration. A library of 348 candidate numerical predictors was assembled from composition, elemental references, initial geometry, symmetry, and local-difference descriptors. Final or relaxed DFT outcomes were excluded from the default predictors."
        )
        self.paragraph(
            "Models were selected using grouped inner cross-validation, and the main outer test held out complete alloy systems. HistGradientBoosting with 198 BALANCED predictors achieved R² = 0.8997, MAE = 0.0535, and RMSE = 0.0764 for the unified FCC+BCC task. Phase-specific R² values were 0.9058 for FCC and 0.9154 for BCC. A compact ten-feature model retained most of this performance (R² = 0.8917). Feature-set and group ablations showed that initial symmetry and structural information were central to configuration-level prediction, while composition alone was weak. These descriptors may also encode configuration-generation choices, so transfer to independent sources requires new validation."
        )
        self.paragraph(
            "A small static-DFT extension compared four fixed-composition Co-Cr configurations. The selected FCC and BCC pairs showed measurable but opposite energy trends with SRO; the calculations are therefore treated as a focused extension rather than a general SRO-energy conclusion. Overall, the project provides a reproducible FCC/BCC database, a strong in-domain grouped-validation result, a compact predictive feature set, and a clear account of the present HCP and transferability limitations."
        )

    def chapter(self, number: int, title: str) -> None:
        if len(self.doc.paragraphs) > 0:
            self.page_break()
        p = self.doc.add_paragraph(style="Heading 1")
        p.paragraph_format.space_before = Pt(24)
        p.add_run(f"Chapter {number}: {title}")

    def section(self, number: str, title: str) -> None:
        self.doc.add_heading(f"{number} {title}", level=2)

    def subsection(self, number: str, title: str) -> None:
        self.doc.add_heading(f"{number} {title}", level=3)

    @staticmethod
    def _set_repeat_header(row) -> None:
        tr_pr = row._tr.get_or_add_trPr()
        repeat = OxmlElement("w:tblHeader")
        repeat.set(qn("w:val"), "true")
        tr_pr.append(repeat)

    @staticmethod
    def _prevent_row_split(row) -> None:
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)

    @staticmethod
    def _shade_cell(cell, fill: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = tc_pr.find(qn("w:shd"))
        if shd is None:
            shd = OxmlElement("w:shd")
            tc_pr.append(shd)
        shd.set(qn("w:fill"), fill)

    def add_caption(self, label: str, title: str, *, alignment) -> None:
        p = self.doc.add_paragraph(style="Caption")
        p.alignment = alignment
        p.paragraph_format.keep_with_next = label == "Table"
        p.add_run(f"{label} ")
        self._add_field(p, f"SEQ {label} \\* ARABIC", "0")
        p.add_run(f". {title}")

    def add_table(
        self,
        title: str,
        headers: Sequence[str],
        rows: Sequence[Sequence[object]],
        widths: Sequence[float] | None = None,
        font_size: float = 8.4,
    ) -> int:
        self.table_no += 1
        self.add_caption("Table", title, alignment=WD_ALIGN_PARAGRAPH.LEFT)
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        self._set_table_borders(table)
        if widths is None:
            widths = [CONTENT_WIDTH_IN / len(headers)] * len(headers)
        if not math.isclose(sum(widths), CONTENT_WIDTH_IN, abs_tol=0.08):
            raise ValueError(f"Bad table widths for {title}: {sum(widths)}")
        hdr = table.rows[0]
        self._set_repeat_header(hdr)
        self._prevent_row_split(hdr)
        for j, text in enumerate(headers):
            cell = hdr.cells[j]
            cell.width = Inches(widths[j])
            cell.text = str(text)
            self._shade_cell(cell, LIGHT_GRAY)
            self._format_cell(cell, font_size, bold=True, center=True)
        for row in rows:
            cells = table.add_row().cells
            self._prevent_row_split(table.rows[-1])
            for j, value in enumerate(row):
                cells[j].width = Inches(widths[j])
                cells[j].text = str(value)
                self._format_cell(cells[j], font_size, bold=False, center=len(str(value)) < 16)
        return self.table_no

    @staticmethod
    def _format_cell(cell, size: float, *, bold: bool, center: bool) -> None:
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            for run in p.runs:
                run.font.name = "Arial"
                run.font.size = Pt(size)
                run.bold = bold

    @staticmethod
    def _set_table_borders(table) -> None:
        tbl_pr = table._tbl.tblPr
        borders = tbl_pr.find(qn("w:tblBorders"))
        if borders is None:
            borders = OxmlElement("w:tblBorders")
            tbl_pr.append(borders)
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            element = OxmlElement(f"w:{edge}")
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), "4")
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), "000000")
            borders.append(element)

    def add_figure(self, key: str, *, max_height: float = 4.35, max_width: float = 6.35) -> int:
        expected = FIG_NO[key]
        self.figure_no += 1
        if self.figure_no != expected:
            raise RuntimeError(f"Figure order drift: {key} expected {expected}, got {self.figure_no}")
        _, relative, caption = FIGURES[expected - 1]
        path = ROOT / relative
        with Image.open(path) as im:
            ratio = im.width / im.height
        width = min(max_width, max_height * ratio)
        width = max(3.5, width)
        if width / ratio > max_height:
            width = max_height * ratio
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path), width=Inches(width))
        for doc_pr in p._p.xpath(".//wp:docPr"):
            doc_pr.set("name", f"Figure {expected}: {key}")
            doc_pr.set("descr", caption)
        self.add_caption("Figure", caption, alignment=WD_ALIGN_PARAGRAPH.CENTER)
        return expected

    def add_equation(self) -> None:
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(7)
        omath_para = OxmlElement("m:oMathPara")
        omath = OxmlElement("m:oMath")
        run = OxmlElement("m:r")
        text = OxmlElement("m:t")
        text.text = "αᵢⱼ⁽ⁿ⁾ = 1 − P(j | i,n) / cⱼ"
        run.append(text)
        omath.append(run)
        omath_para.append(omath)
        p._p.append(omath_para)

    def add_references(self, references: Iterable[str]) -> None:
        for i, reference in enumerate(references, start=1):
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.28)
            p.paragraph_format.first_line_indent = Inches(-0.28)
            p.paragraph_format.space_after = Pt(4)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.add_run(f"[{i}] {reference}")

    def save(self) -> None:
        if self.figure_no != len(FIGURES):
            raise RuntimeError(f"Expected {len(FIGURES)} figures, found {self.figure_no}")
        if self.table_no < 12:
            raise RuntimeError(f"Expected at least 12 tables, found {self.table_no}")
        DELIVERABLES.mkdir(parents=True, exist_ok=True)
        self.doc.save(DOCX_PATH)


def build_thesis() -> ThesisBuilder:
    verify_repository_values()
    b = ThesisBuilder()
    b.add_title_page()
    b.add_declaration()
    b.add_acknowledgement()
    b.add_front_lists()
    b.add_abstract()

    # Chapter 1
    b.chapter(1, "Introduction and Literature Review")
    b.section("1.1", "Chemical short-range order")
    b.paragraph(
        "A substitutional alloy is often described as a random solid solution, but the atoms around a selected site need not occur in random proportions. Some unlike species may appear next to each other more often than expected, while other pairs may avoid one another. This local departure from randomness is called chemical short-range order (SRO). SRO does not require a new long-range crystal structure, yet it can be related to local stability, diffusion, mechanical response, magnetic behaviour, and transformation paths. Experimental studies commonly infer SRO from diffuse X-ray or neutron scattering, while simulations calculate it directly from atomic configurations [1–5]."
    )
    b.paragraph(
        "SRO is difficult to compare across papers because the reported quantity may depend on the element pair, neighbour shell, temperature, phase, composition, and sign convention. The same alloy can therefore produce many SRO values. A useful database must keep these distinctions instead of treating every value as one interchangeable target. This point became important in the first semester, when literature-derived records from FCC, BCC, and HCP systems were combined for exploratory analysis."
    )

    b.section("1.2", "Warren–Cowley SRO")
    b.paragraph(
        "The Warren–Cowley parameter expresses the deviation of a local pair probability from a random reference. For species i and j in neighbour shell n, it can be written as"
    )
    b.add_equation()
    b.paragraph(
        "where P(j | i,n) is the probability of finding species j in shell n around species i, and cⱼ is the bulk fraction of species j. A value near zero indicates random pair statistics for that shell. Negative values indicate that the unlike pair occurs more frequently than the random reference, whereas positive values indicate avoidance. The interpretation is pair- and shell-specific. The present main dataset stores summary statistics of these coefficients rather than the complete signed pair table."
    )
    b.paragraph(
        "The primary machine-learning target is target_mean_abs_sro_shell1: the arithmetic mean of the absolute first-neighbour Warren–Cowley coefficients over all unique unlike-element pairs represented in one configuration. Taking the absolute value prevents positive and negative pair coefficients from cancelling, but it removes the sign and pair identity. The target therefore measures aggregate ordering magnitude. It is not a signed pair-specific coefficient, and because the 84k source has no observation temperature, it is not a temperature-dependent equilibrium SRO value."
    )

    b.section("1.3", "Why SRO prediction is difficult")
    b.paragraph(
        "SRO depends on both chemistry and atomic arrangement. Two configurations may have the same overall composition but different occupations of neighbouring sites, different symmetries, and different local coordination statistics. A composition-only model cannot distinguish those configurations. At the same time, highly detailed structural descriptors may reproduce how a particular dataset was generated rather than a general physical relation. Useful prediction therefore requires a clear target definition, strict leakage control, and evaluation on chemically distinct groups."
    )
    b.paragraph(
        "Another difficulty is statistical independence. Computational datasets can contain many structures from the same alloy system, composition, supercell policy, or configuration generator. A random row split places very similar records in training and test sets and gives an optimistic estimate. For this reason, the second-semester study treats complete alloy-system holdout as the main evaluation and uses random and composition-held-out results only as comparisons."
    )

    b.section("1.4", "First-semester experimental study")
    b.paragraph(
        "The project began with a small experimental and literature-derived dataset. Reported SRO values were collected for FCC, BCC, and HCP alloys and standardized into a common row format containing composition, phase, shell number, temperature where reported, element-pair information, and SRO value. Missing-value markers were cleaned, compositions were converted to fractions, and basic thermodynamic and elemental descriptors were added. Table 1 summarizes the final pilot dataset. These 437 rows were reported observations, not the later theoretical configurations."
    )
    b.add_table(
        "Phase distribution of the first-semester literature-derived SRO dataset",
        ("Phase", "Rows", "Examples reported in the pilot set"),
        (("FCC", 331, "Cu–Zn, Ni–Ti, Ni–Cr, Ag–Al"), ("BCC", 24, "Fe–Al, Fe–Cr"), ("HCP", 82, "Ag–Al"), ("Total", 437, "—")),
        (1.1, 1.0, 4.35),
    )
    b.paragraph(
        "The first-semester analysis used correlation heatmaps, principal component analysis (PCA), K-means clustering, Random Forest, XGBoost, and phase-wise modelling. The purpose was exploratory: to test whether the available fields contained a consistent signal and to learn which data limitations mattered. Results improved when FCC was analysed separately, but the best-looking single split did not remain stable under multi-fold validation."
    )

    b.section("1.5", "Motivation for moving to the theoretical dataset")
    b.paragraph(
        "The pilot dataset was small, strongly imbalanced by phase, and assembled from different experiments, alloy families, temperatures, shells, and reporting conventions. The 24 BCC rows and 82 HCP rows were too limited for reliable phase-specific learning. Even within FCC, apparently strong cluster results varied sharply across validation folds. The main lesson was that a more uniform and much larger source was needed before detailed feature interpretation could be attempted."
    )
    b.paragraph(
        "In the second semester, the study therefore moved to the DFT dataset for high-entropy materials reported by Li and co-workers [6,7]. This source provides initial FCC and BCC configurations, a common descriptor workflow, and shell-resolved aggregate SRO labels. It also introduces a different limitation: many descriptors are specific to the source and may encode configuration construction. The final thesis treats the pilot and theoretical studies as consecutive stages rather than merging their incompatible targets."
    )

    b.section("1.6", "Objectives of the UGP")
    b.paragraph("The final objectives were:")
    for item in (
        "to document the scientific meaning and limitations of the 84k SRO labels;",
        "to build a validated FCC/BCC database with feature provenance and initial-state leakage controls;",
        "to compare composition, phase, elemental, and initial-structure information under grouped validation;",
        "to compare unified and phase-specific FCC/BCC models without claiming causality from phase;",
        "to identify a compact high-performance feature set and a separate minimal cross-source database schema;",
        "to audit potential HCP sources and exclude labels that could not be validated; and",
        "to perform a small static-DFT extension on four selected Co-Cr configurations without treating it as a general statistical study.",
    ):
        b.bullet(item)

    # Chapter 2
    b.chapter(2, "Material and Methods")
    b.section("2.1", "Overall project workflow")
    b.paragraph(
        f"The two-semester workflow is summarized in Figure {FIG_NO['workflow']}. The first semester established the basic data-cleaning and modelling workflow on a small literature-derived dataset. The second semester separated source audit, target validation, database construction, exploratory analysis, grouped model selection, interpretation, and final reproducibility checks. Existing figures and numerical tables were generated by deterministic project scripts; the thesis assembly did not rerun model training."
    )
    b.add_figure("workflow", max_height=3.0)

    b.section("2.2", "First-semester experimental data and ML workflow")
    b.paragraph(
        "Each first-semester row described one reported SRO observation for an alloy composition, phase, element pair, shell, and temperature when available. Extraction metadata and missing-value markers were cleaned. Element fractions, phase indicators, shell index, mixing enthalpy, ideal configurational entropy, electronegativity differences, radius statistics, and size mismatch were used as predictors. PCA and K-means were used to inspect structure in the feature space. Random Forest and XGBoost were then tested on the combined data, on phase subsets, and on clusters. The exercise identified instability rather than a final deployable model."
    )

    b.section("2.3", "Theoretical data-source inventory")
    b.paragraph(
        "Seven source families were inventoried in the second semester. Table 2 lists the most relevant sources and explains their role. The primary 84k source was the only dataset admitted to the final validated ML response. Rao–Curtin material [8] remained useful for FCC/BCC theoretical context, while CrCoNi and HfTiZr sources [9–11] were audited mainly for possible HCP extension."
    )
    b.add_table(
        "Main theoretical sources considered in the second semester",
        ("Source", "Coverage", "SRO status", "Use in this study"),
        (
            ("84k HEA DFT [6,7]", "FCC/BCC; Al–Co–Cr–Cu–Fe–Mn–Ni", "Validated aggregate WC summaries", "Primary EDA and ML dataset"),
            ("Rao–Curtin [8]", "FCC/BCC model alloys", "Pair probabilities and SRO-related outputs", "Context; not merged"),
            ("MLP-cSRO CrCoNi [9]", "FCC/HCP/liquid", "255 HCP frames; reference arrays unavailable", "Provisional HCP audit"),
            ("CrCoNi ColabFit [10]", "CrCoNi structures", "No explicit SRO labels", "Candidate structure source"),
            ("CMS-EAM [11]", "FCC/BCC/HCP planned systems", "No compact validated HCP WC table locally", "Candidate HfTiZr extension"),
        ),
        (1.45, 1.55, 1.8, 1.65),
        font_size=7.9,
    )

    b.section("2.4", "Primary 84k dataset")
    b.paragraph(
        "The original source contains 84,024 structures. A total of 227 rows lack the matched initial structure and SRO information required for this study. The validated join therefore contains 83,797 configurations. They cover 40,425 FCC and 43,372 BCC structures across the Al–Co–Cr–Cu–Fe–Mn–Ni chemical domain. These are computational configurations; they are not independent experiments, and many share alloy systems and generation procedures."
    )
    b.paragraph(
        "The small input sample in Table 3 uses the four later DFT-selected configurations only to show the standardized identifiers and target format. It is not the statistical basis of the ML study."
    )
    b.add_table(
        "Illustrative standardized input rows from the four DFT-selected configurations",
        ("Configuration ID", "Phase", "System", "Composition", "Atoms", "Target"),
        (
            ("gra62121526", "FCC", "Co–Cr", "Co0.5Cr0.5", 2, "0.000000"),
            ("gra62121527", "FCC", "Co–Cr", "Co0.5Cr0.5", 2, "0.333333"),
            ("gra64001864", "BCC", "Co–Cr", "Co0.5Cr0.5", 2, "0.000000"),
            ("gra62121595", "BCC", "Co–Cr", "Co0.5Cr0.5", 2, "1.000000"),
        ),
        (1.6, 0.7, 0.75, 1.55, 0.65, 1.2),
        font_size=8.1,
    )

    b.section("2.5", "SRO target definition and validation")
    b.paragraph(
        "The source stores four shell summaries. The available scripts and supplied files were inspected to establish that the columns summarize Warren–Cowley coefficients for unique unlike-element pairs in the initial structure. The first-shell primary target was reconstructed independently for selected records and checked against the source summaries. The resulting target is an aggregate magnitude, not a signed pair-resolved response."
    )
    b.paragraph(
        "This distinction controls the scientific interpretation. A large target indicates that at least some unlike-pair statistics depart strongly from randomness, but it does not say which pair orders or avoids, nor whether different signed pair contributions compete. Pair-resolved future work will require the original pair arrays or a validated recalculation from structures."
    )

    b.section("2.6", "Data standardization and quality control")
    b.paragraph(
        "The pipeline validates identifiers, joins initial descriptor and SRO tables one-to-one, standardizes phase labels, canonicalizes compositions, constructs a shell-long SRO table, and records feature provenance. Four local Parquet products represent structures, shell-long SRO, features, and the final ML table. These processed files are reproducible but intentionally excluded from Git because of size. Quality checks found complete feature values for all retained modeling rows."
    )
    b.paragraph(
        "The feature audit also identified constants, near-zero-variance descriptors, and strongly correlated pairs. Twenty-four features were constant, 29 were near-zero variance, and 426 aggregate feature pairs had absolute Pearson correlation of at least 0.95. These checks motivated the FULL and BALANCED definitions used later."
    )

    b.section("2.7", "Feature engineering")
    b.paragraph(
        "A total of 348 candidate numerical predictors were assembled. Every feature was labelled by origin: direct source, composition-derived, elemental-reference-derived, structure-derived, or externally enriched. Table 4 summarizes the main scientific families. The library includes both transferable composition statistics and detailed source-specific structure descriptors."
    )
    b.add_table(
        "Main feature families and their origin",
        ("Feature family", "Examples", "Typical origin"),
        (
            ("Composition", "element fractions, pair fractions, number of elements", "direct/composition-derived"),
            ("Entropy", "ideal configurational entropy, normalized entropy", "composition-derived"),
            ("Elemental statistics", "atomic number, mass, radius, melting point", "elemental-reference-derived"),
            ("Chemical/electronic", "electronegativity, VEC, local valence differences", "elemental-reference-derived"),
            ("Atomic size", "radius spread, atomic-size mismatch", "composition/elemental-derived"),
            ("Initial geometry", "packing efficiency, neighbour-distance variation", "structure-derived"),
            ("Symmetry", "initial space group and local symmetry statistics", "structure-derived"),
            ("Supplied descriptors", "thermodynamic and Matminer-style descriptors", "direct/source-specific"),
        ),
        (1.5, 3.0, 1.95),
        font_size=8.0,
    )

    b.section("2.8", "Leakage control")
    b.paragraph(
        "Only composition, phase, elemental-reference information, and initial/pre-relaxation structural descriptors were admitted by default. Final or relaxed DFT outcomes would reveal information generated after the starting configuration and could make prediction unrealistically easy. Table 5 records the main exclusions."
    )
    b.add_table(
        "Leakage-control policy for the default ML predictors",
        ("Excluded information", "Reason"),
        (
            ("final/relaxed energy and energy-derived outcomes", "post-relaxation result; not available for a new initial configuration"),
            ("final volume and relaxed lattice descriptors", "post-relaxation structural response"),
            ("final space group or final symmetry", "relaxation outcome"),
            ("final forces and pressure", "computed DFT outcomes"),
            ("final magnetization", "computed electronic outcome"),
            ("direct SRO fields and target proxies", "would expose the response itself"),
        ),
        (2.6, 3.85),
        font_size=8.2,
    )
    b.paragraph(
        "Initial geometry was retained because the prediction task is configuration-level rather than composition-only. However, initial space group, atom count, local topology, and related fingerprints can also identify ordered cells, SQS choices, or configuration-generation procedures. The study therefore reports their predictive value and separately tests transferability risk through feature-set and descriptor-group removal."
    )

    b.section("2.9", "EDA and redundancy analysis")
    b.paragraph(
        "EDA covered phase counts, alloy-system and element coverage, target distributions, missingness, feature variance, Pearson correlation, Spearman rank association, mutual information, and feature–feature redundancy. These screens were used to understand the source and construct the BALANCED set. They were not interpreted as causal tests."
    )

    b.section("2.10", "Machine-learning models")
    b.paragraph(
        "The screened regression families are listed in Table 6. They range from simple baselines to ensemble tree models. HistGradientBoosting was ultimately selected through grouped inner validation. The thesis does not repeat general algorithm theory; the important methodological point is that preprocessing, variance filtering, and model fitting occurred inside the training pipeline."
    )
    b.add_table(
        "Regression models screened in the second-semester study",
        ("Model family", "Role in comparison"),
        (
            ("Median DummyRegressor", "non-informative baseline"),
            ("Linear regression", "unregularized linear baseline"),
            ("Ridge and ElasticNet", "regularized linear baselines"),
            ("Random Forest", "bagged nonlinear trees"),
            ("Extra Trees", "randomized tree ensemble"),
            ("Gradient Boosting", "sequential boosting baseline"),
            ("HistGradientBoosting", "efficient nonlinear boosted-tree model"),
            ("SVR (bounded subset)", "computationally limited kernel baseline"),
        ),
        (2.4, 4.05),
        font_size=8.3,
    )

    b.section("2.11", "Validation strategy")
    b.paragraph(
        "Three outer evaluations were compared. The random-configuration split is an optimistic baseline. The composition-grouped split holds out exact compositions. The main alloy-system split holds out complete chemical systems, so no alloy-system group appears in both train and test. Table 7 gives the verified sizes."
    )
    b.add_table(
        "Outer validation strategies for the unified model",
        ("Split", "Train rows", "Test rows", "Purpose"),
        (
            ("Random configuration", "67,037", "16,760", "optimistic row-level baseline"),
            ("Composition grouped", "68,318", "15,479", "tests unseen exact compositions"),
            ("Alloy-system held out", "71,117", "12,680", "main test on unseen chemical systems"),
        ),
        (1.65, 1.0, 0.95, 2.85),
        font_size=8.2,
    )
    b.paragraph(
        "Within the outer training partition, shuffled three-fold GroupKFold by alloy system was used for model and feature-set comparison. Outer-test metrics were not used to select the model or feature count. The compact set was chosen from training-partition rankings and grouped inner validation, and was evaluated once on the untouched outer test. Five deterministic alloy-system allocations were later used as a robustness check without repeating a large hyperparameter search."
    )

    b.section("2.12", "Feature ablation and interpretation")
    b.paragraph(
        "Interpretation combined held-out permutation importance, physical feature-group ablation, targeted removal of configuration-sensitive descriptors, and a small number of partial-dependence checks. Feature importance was treated as conditional predictive information. Correlated descriptors can share or substitute for information, so an individual ranking was not taken as a causal mechanism."
    )

    b.section("2.13", "Compact model selection")
    b.paragraph(
        "The earlier 19-feature preliminary set performed poorly and was not retained. A new hierarchy was constructed: FULL (324 predictors), BALANCED (198), COMPACT_HIGH_PERFORMANCE (10), and MINIMAL_COMMON (18). Candidate compact sizes of 10, 20, 30, 50, 75, 100, and 150 were tested using training-only rankings and grouped validation. The smallest set meeting the performance criterion was selected."
    )

    b.section("2.14", "HCP audit")
    b.paragraph(
        "The MLP-cSRO CrCoNi materials contained 255 provisional equiatomic HCP configurations. They were not admitted as validated labels because the public material checked did not include the author HCP Warren–Cowley reference arrays or a fully verified topology mapping. Ninety-eight configurations also had an ambiguous thirteenth-to-twelfth neighbour-distance ratio below 1.02, making the first-shell boundary sensitive. No HCP model was trained."
    )

    b.section("2.15", "DFT extension methodology")
    b.paragraph(
        "A small first-principles extension used four exact two-atom Co-Cr configurations from the source: low- and high-SRO examples in FCC and BCC. Static spin-polarized SCF calculations were run with Quantum ESPRESSO 7.6, PBE-compatible SSSP pseudopotentials, ecutwfc = 55 Ry, ecutrho = 440 Ry, a 12 × 12 × 12 Monkhorst–Pack grid, Marzari–Vanderbilt smearing with degauss = 0.02 Ry, and conv_thr = 10⁻⁸. No structural relaxation, density-of-states, or band calculation was performed."
    )
    b.paragraph(
        "The final 55-to-65 Ry cutoff difference was 1.772 meV per atom for the checked structure, so 55 Ry was retained for this preliminary comparison. Energies were normalized per atom and referenced only within each fixed-composition phase pair. The four calculations were intended to demonstrate a possible energetic distinction between selected local arrangements, not to determine a universal SRO–energy relation."
    )

    # Chapter 3
    b.chapter(3, "Results and Discussion")
    b.section("3.1", "Semester-1 findings and limitations")
    b.paragraph(
        "Table 8 summarizes the main first-semester regression results. On the full 437-row dataset, Random Forest and XGBoost gave only moderate R² values of 0.349 and 0.356. The FCC subset was more promising, and a single Random Forest split in one FCC cluster reached R² = 0.740. However, five-fold validation of that same cluster gave mean R² = 0.337 with large variation. The apparent improvement was therefore not stable."
    )
    b.add_table(
        "Selected first-semester machine-learning results",
        ("Dataset or subset", "Model", "R²", "RMSE", "Interpretation"),
        (
            ("Full combined", "Random Forest", "0.349", "0.133", "moderate mixed-data result"),
            ("Full combined", "XGBoost", "0.356", "0.132", "slightly above RF"),
            ("FCC full", "Random Forest", "0.510", "0.121", "improved phase subset"),
            ("FCC full", "XGBoost", "0.660", "0.101", "best full-phase pilot result"),
            ("FCC cluster 1", "Random Forest", "0.740", "0.090", "best single split"),
            ("FCC cluster 1, 5-fold", "Random Forest", "0.337 mean", "—", "unstable across folds"),
        ),
        (1.45, 1.25, 0.7, 0.75, 2.3),
        font_size=7.9,
    )
    b.paragraph(
        "The pilot study was still useful. It established the data-cleaning workflow, showed that phase separation mattered, and revealed that cluster performance must be checked across folds. Its central outcome was a limitation: a small heterogeneous literature table cannot support reliable general SRO modelling simply by adding more algorithms. This directly motivated the larger and more uniform second-semester dataset."
    )

    b.section("3.2", "Final theoretical dataset")
    b.paragraph(
        f"The validated theoretical database contains 83,797 configurations. Figure {FIG_NO['phase_counts']} shows 40,425 FCC and 43,372 BCC observations; the validated HCP count is zero. The phase balance is suitable for an FCC/BCC comparison, but the records remain dominated by one theoretical workflow."
    )
    b.add_figure("phase_counts", max_height=3.4)
    b.paragraph(
        "All retained modeling rows have complete candidate feature values. The shell-long table contains 335,188 rows, corresponding to four shell summaries for each validated configuration. The final ML target uses only shell one, while the other shell summaries remain available for future analysis."
    )

    b.section("3.3", "SRO distribution")
    b.paragraph(
        f"The overall mean primary target is 0.3345. As Figure {FIG_NO['target_distribution']} shows, the FCC and BCC distributions overlap but are shifted. FCC has mean 0.2640 and BCC mean 0.4002. The distribution difference is described more carefully in Section 3.11 because chemistry and configuration coverage differ between phases."
    )
    b.add_figure("target_distribution", max_height=3.7)

    b.section("3.4", "Main correlations and redundancy")
    b.paragraph(
        f"Initial space-group number has the strongest reported aggregate linear and monotonic association with the target: Pearson r = 0.4753 and Spearman ρ = 0.5931. Figure {FIG_NO['spearman']} shows the leading rank associations. The largest mutual-information screening statistic is 1.7996 for the descriptor named 5-norm. These are useful screening results, not causal effects."
    )
    b.add_figure("spearman", max_height=3.9)
    b.paragraph(
        f"The feature library is also highly redundant. Figure {FIG_NO['redundancy']} shows strong relationships even within a selected portable subset, while the full audit found 426 feature pairs with |r| ≥ 0.95. Redundancy explains why FULL did not outperform BALANCED and why individual importance ranks must be interpreted with caution."
    )
    b.add_figure("redundancy", max_height=4.1)

    b.section("3.5", "Model comparison")
    b.paragraph(
        f"Figure {FIG_NO['model_comparison']} compares unified alloy-held-out R² values. Tree ensembles were substantially stronger than the linear baselines. HistGradientBoosting with the BALANCED feature set was selected using grouped inner cross-validation; no outer-test metric was used for model selection. The frozen selected specification was then evaluated on the untouched alloy-system test."
    )
    b.add_figure("model_comparison", max_height=3.9)
    b.paragraph("The main test metrics are given in Table 9.")
    b.add_table(
        "Final alloy-system-held-out metrics for the selected BALANCED models",
        ("Cohort", "Model", "Predictors", "R²", "MAE", "RMSE"),
        (
            ("Unified", "HistGradientBoosting", 198, "0.8997", "0.0535", "0.0764"),
            ("FCC", "HistGradientBoosting", 198, "0.9058", "0.0348", "0.0534"),
            ("BCC", "HistGradientBoosting", 198, "0.9154", "0.0563", "0.0808"),
        ),
        (0.8, 1.8, 0.8, 0.85, 0.85, 1.35),
        font_size=8.3,
    )
    b.paragraph(
        "The BCC R² is slightly higher in this single split, but its MAE and RMSE are larger because the BCC target has a broader scale. Repeated splits later show nearly equal mean R² for FCC and BCC, so the data do not support the statement that BCC is universally easier to predict."
    )

    b.section("3.6", "Generalization under grouped splits")
    b.paragraph(
        f"Unified R² decreases from 0.9266 under a random configuration split to 0.9161 under composition holdout and 0.8997 under alloy-system holdout (Figure {FIG_NO['split_comparison']}). The decrease is expected because the grouped tests reduce overlap in chemical identity. The alloy-system value is the main result because complete chemical systems are unseen during fitting. It remains an in-domain result for the Al–Co–Cr–Cu–Fe–Mn–Ni source, not universal extrapolation to arbitrary elements."
    )
    b.add_figure("split_comparison", max_height=3.6)
    b.add_table(
        "Unified performance across outer split strategies",
        ("Outer split", "R²", "MAE", "RMSE"),
        (
            ("Random configuration", "0.9266", "0.0508", "0.0731"),
            ("Composition grouped", "0.9161", "0.0534", "0.0760"),
            ("Alloy-system held out", "0.8997", "0.0535", "0.0764"),
        ),
        (2.45, 1.3, 1.3, 1.4),
        font_size=8.4,
    )

    b.section("3.7", "Unified versus phase-specific models")
    b.paragraph(
        f"The unified model tracks the held-out target well over the main range (Figure {FIG_NO['predicted_unified']}). Residual spread increases toward extreme target values, which is considered in Section 3.12."
    )
    b.add_figure("predicted_unified", max_height=4.2)
    b.paragraph(
        f"Phase-specific training provides a useful but unequal improvement. For FCC held-out rows, R² increases from 0.8668 when scored with the unified model to 0.9058 with the FCC model. For BCC rows, it increases from 0.9038 to 0.9154. Figure {FIG_NO['phase_models']} shows that the FCC gain is larger. Separate phase models are justified when the goal is best phase-level accuracy or interpretation, but they do not prove distinct causal mechanisms."
    )
    b.add_figure("phase_models", max_height=3.5)

    b.section("3.8", "Feature-set ablation")
    b.paragraph(
        f"Feature-set ablation is one of the clearest scientific results. Composition-only grouped-CV R² is 0.0262, and adding phase raises it to only 0.1764. Composition plus initial structure reaches 0.8783, close to the BALANCED value of 0.8803 (Figure {FIG_NO['feature_sets']}). The initial structural description therefore supplies most of the configuration-level predictive information within this source."
    )
    b.add_figure("feature_sets", max_height=3.7)
    b.add_table(
        "Key feature-set results from grouped inner validation",
        ("Feature definition", "Predictors", "Mean CV R²", "Interpretation"),
        (
            ("Composition only", 204, "0.0262", "weak for configuration-level differences"),
            ("Composition + phase", 205, "0.1764", "phase alone adds limited information"),
            ("Composition + initial structure", 320, "0.8783", "captures configuration information"),
            ("BALANCED", 198, "0.8803", "best selected compact/redundancy balance"),
        ),
        (2.1, 0.8, 1.0, 2.55),
        font_size=8.1,
    )
    b.paragraph(
        "This result must be stated carefully. It does not show that space group or another structural descriptor causes SRO. It shows that the initial configuration contains information strongly associated with the SRO value calculated from that same configuration. Part of the gain may come from transferable local geometry, while part may encode ordered versus SQS cells, atom count, or other source-generation choices."
    )

    b.section("3.9", "Compact high-performance model")
    b.paragraph(
        f"Training-only refinement selected the smallest tested accepted set: ten predictors. Its mean inner grouped-CV R² is 0.8636, compared with 0.8803 for BALANCED, and the acceptance threshold was 0.8503 (Figure {FIG_NO['compact_refinement']}). The outer alloy-system R² is 0.8917, MAE is 0.0537, and RMSE is 0.0794. The absolute R² loss relative to BALANCED is only about 0.0081."
    )
    b.add_figure("compact_refinement", max_height=3.6)
    b.add_table(
        "Exact compact high-performance predictor list",
        ("No.", "Predictor"),
        tuple(
            enumerate(
                (
                    "space_group_number_ini",
                    "configurational_entropy_j_mol_k",
                    "max packing efficiency",
                    "NIONS",
                    "range neighbor distance variation",
                    "configurational_entropy_normalized",
                    "minimum local difference in NsUnfilled",
                    "mean local difference in SpaceGroupNumber",
                    "mean local difference in NsValence",
                    "avg_dev local difference in NsValence",
                ),
                start=1,
            )
        ),
        (0.65, 5.8),
        font_size=8.2,
    )
    b.paragraph(
        "The compact list is an efficient predictive recommendation for the present theoretical source. It is not the same as the 18-field minimal common database recommendation, which emphasizes composition, provenance, phase, temperature when genuinely available, metric, pair, shell, and simple transferable descriptors for every future SRO record."
    )

    b.section("3.10", "Feature interpretation")
    b.paragraph(
        f"Permutation importance identifies initial space group as the leading held-out feature in the unified, FCC, and BCC models (Figure {FIG_NO['importance']}). Configurational entropy, atom count, packing and neighbour geometry, and local valence or unfilled-electron differences also appear among the leading predictors. These rankings are conditional on the fitted model and the correlated BALANCED feature set."
    )
    b.add_figure("importance", max_height=4.0)
    b.paragraph(
        f"Physical group ablation gives a more stable summary (Figure {FIG_NO['group_ablation']}). Removing symmetry decreases unified grouped-CV R² by 0.0666. Removing structural geometry decreases it by 0.0246, configurational entropy by 0.0220, and electronic/VEC/periodic descriptors by 0.0126. The main values are listed in Table 13."
    )
    b.add_figure("group_ablation", max_height=3.7)
    b.add_table(
        "Largest unified physical feature-group ablation effects",
        ("Removed group", "Features removed", "ΔR²", "ΔMAE"),
        (
            ("Symmetry", 11, "−0.0666", "+0.0172"),
            ("Structural geometry", 6, "−0.0246", "+0.0086"),
            ("Configurational entropy", 2, "−0.0220", "+0.0074"),
            ("Electronic/VEC/periodic", 80, "−0.0126", "+0.0032"),
            ("Elemental thermophysical", 25, "−0.0043", "+0.0007"),
            ("Electronegativity", 12, "−0.0034", "+0.0007"),
        ),
        (2.4, 1.15, 1.3, 1.6),
        font_size=8.2,
    )
    b.paragraph(
        f"Targeted sensitivity supports the same caution. Removing space_group_number_ini changes outer R² by −0.0830 for the unified model, −0.0751 for FCC, and −0.0805 for BCC. Figure {FIG_NO['configuration_sensitivity']} shows the effect of related removals. The decrease demonstrates strong predictive information, but not whether that information is universal structural physics or a signature of the dataset construction."
    )
    b.add_figure("configuration_sensitivity", max_height=3.6)

    b.section("3.11", "FCC versus BCC behaviour")
    b.paragraph(
        f"The BCC mean aggregate SRO magnitude is 0.4002, compared with 0.2640 for FCC. The BCC-minus-FCC difference is 0.1362, Cohen’s d is 0.5253, and the Kolmogorov–Smirnov statistic is 0.2334. Figure {FIG_NO['fcc_bcc']} combines the descriptive target contrast and model results."
    )
    b.add_figure("fcc_bcc", max_height=3.8)
    b.add_table(
        "Verified FCC/BCC comparison",
        ("Quantity", "FCC", "BCC", "Comparison"),
        (
            ("Validated observations", "40,425", "43,372", "similar phase counts"),
            ("Mean target", "0.2640", "0.4002", "BCC–FCC = 0.1362"),
            ("Outer R²", "0.9058", "0.9154", "single-split BCC slightly higher"),
            ("Outer MAE", "0.0348", "0.0563", "larger absolute BCC error"),
            ("Five-split mean R²", "0.9046", "0.9042", "nearly equal"),
            ("Five-split R² SD", "0.0128", "0.0287", "BCC less stable"),
        ),
        (1.85, 1.05, 1.05, 2.5),
        font_size=8.1,
    )
    b.paragraph(
        "Thus, BCC configurations have higher aggregate SRO magnitude in this dataset. The comparison is not evidence that the BCC crystal structure by itself causes higher SRO, because chemical systems, compositions, and configuration-generation procedures may differ between phase subsets. The repeated-split results also show that average predictability is almost the same, although BCC performance varies more across held-out systems."
    )

    b.section("3.12", "Robustness and error analysis")
    b.paragraph(
        f"Across five deterministic alloy-system allocations, unified mean R² is 0.8946 ± 0.0187, FCC mean R² is 0.9046 ± 0.0128, and BCC mean R² is 0.9042 ± 0.0287 (Figure {FIG_NO['robustness']}). The original split is therefore not a single lucky result. The larger BCC standard deviation shows that its score depends more strongly on which alloy systems are held out."
    )
    b.add_figure("robustness", max_height=3.6)
    b.add_table(
        "Repeated alloy-system split robustness",
        ("Cohort", "Seeds", "Mean R²", "SD R²", "Mean MAE", "Mean RMSE"),
        (
            ("Unified", 5, "0.8946", "0.0187", "0.0569", "0.0824"),
            ("FCC", 5, "0.9046", "0.0128", "0.0375", "0.0576"),
            ("BCC", 5, "0.9042", "0.0287", "0.0615", "0.0892"),
        ),
        (1.0, 0.7, 1.05, 1.05, 1.25, 1.4),
        font_size=8.2,
    )
    b.paragraph(
        f"Error is not uniform across the target range. Figure {FIG_NO['error_decile']} shows larger errors in difficult target regions, especially near extremes with fewer close analogues in training. High-error cases also occur in some rare held-out systems and sparse portions of compact-feature space. These observations limit the model to the represented chemical and configuration domain."
    )
    b.add_figure("error_decile", max_height=3.6)

    b.section("3.13", "HCP status")
    b.paragraph(
        "The validated HCP count remains zero. The 255 provisional CrCoNi configurations are useful leads, but they lack the author WC reference arrays and fully validated topology mapping required for inclusion. They were therefore excluded rather than assigned reconstructed values with unresolved shell boundaries. The present conclusions apply only to validated FCC and BCC configurations."
    )

    b.section("3.14", "DFT extension results")
    b.paragraph(
        "All four production SCF calculations reached the requested electronic criterion and ended with JOB DONE. Table 16 reports the per-atom energies and within-phase relative energies. The absolute energies are not compared across FCC and BCC; only structures with the same phase, composition, and atom count are referenced to one another."
    )
    b.add_table(
        "Targeted static-DFT results for the four selected Co-Cr configurations",
        ("Phase", "Label", "Configuration", "SRO", "Energy/atom (eV)", "Relative (meV/atom)"),
        (
            ("FCC", "low", "gra62121526", "0.000000", "−3224.251885", "106.954"),
            ("FCC", "high", "gra62121527", "0.333333", "−3224.358840", "0.000"),
            ("BCC", "low", "gra64001864", "0.000000", "−3224.170645", "0.000"),
            ("BCC", "high", "gra62121595", "1.000000", "−3224.027269", "143.376"),
        ),
        (0.65, 0.6, 1.25, 0.8, 1.65, 1.5),
        font_size=7.9,
    )
    b.paragraph(
        f"For the selected FCC pair, the higher-SRO structure is lower by 106.954 meV per atom. For the selected BCC pair, the lower-SRO structure is lower by 143.376 meV per atom. Figure {FIG_NO['dft_energy']} makes the opposite trends clear. The calculation therefore supports only the limited statement that selected structures with identical chemistry but different local ordering can have different static energies. Four configurations are insufficient to establish a universal SRO–energy trend."
    )
    b.add_figure("dft_energy", max_height=3.8)

    b.section("3.15", "Overall progression of the UGP")
    b.paragraph(
        "Table 17 summarizes how the project changed across the two semesters and the DFT extension. The main advance was not only the larger dataset. It was the move from heterogeneous row-level modelling to an explicitly defined target, provenance-preserving features, leakage controls, grouped validation, and uncertainty about transferability."
    )
    b.add_table(
        "Progression of the two-semester project",
        ("Stage", "Data scale", "Main methods", "Main outcome"),
        (
            ("Semester 1", "437 literature-derived observations", "cleaning, correlation, PCA, clustering, RF, XGBoost", "useful exploration; unstable general modelling"),
            ("Semester 2", "83,797 validated FCC/BCC configurations", "target audit, feature engineering, grouped ML, ablation, robustness", "strong in-source alloy-held-out prediction and compact model"),
            ("DFT extension", "4 selected Co-Cr configurations", "static spin-polarized QE SCF", "measurable pair-specific energy differences; no general trend"),
        ),
        (1.15, 1.65, 2.0, 1.65),
        font_size=7.9,
    )

    # Chapter 4
    b.chapter(4, "Conclusions and Future Work")
    b.section("4.1", "Main conclusions")
    conclusions = (
        "The first-semester literature-derived dataset was useful for developing the workflow, but its 437 heterogeneous and phase-imbalanced observations did not support stable general SRO prediction.",
        "A validated theoretical dataset of 83,797 configurations was constructed, consisting of 40,425 FCC and 43,372 BCC observations. No HCP labels passed the validation requirements.",
        "The primary target is the mean absolute first-neighbour Warren–Cowley coefficient across unique unlike pairs. It is an aggregate magnitude and does not retain pair identity or sign.",
        "HistGradientBoosting with 198 BALANCED predictors achieved the main alloy-system-held-out unified result of R² = 0.8997, MAE = 0.0535, and RMSE = 0.0764. Phase-specific R² values were 0.9058 for FCC and 0.9154 for BCC.",
        "Performance was stable across five deterministic group allocations, with unified mean R² = 0.8946 ± 0.0187.",
        "Composition-only grouped-CV R² was 0.0262, whereas composition plus initial structure reached 0.8783. Initial configuration information is therefore essential for configuration-level prediction in this source.",
        "A ten-feature compact model retained most of the 198-feature performance, with outer R² = 0.8917.",
        "Symmetry, initial structural geometry, configurational entropy, and electronic/VEC/periodic descriptors supplied the largest conditional predictive contributions. Their source dependence limits immediate transfer to unrelated experimental datasets.",
        "BCC target magnitude was higher than FCC in this dataset (0.4002 versus 0.2640), but phase was not assigned a causal effect because chemistry and configuration distributions differ.",
        "The four-configuration DFT extension found measurable and opposite within-pair energy trends in FCC and BCC. It remains a targeted demonstration, not the central thesis conclusion.",
    )
    for item in conclusions:
        b.numbered(item)

    b.section("4.2", "Limitations")
    for item in (
        "The primary target is aggregate and absolute; pair identity and ordering sign are lost.",
        "All validated ML labels come from one theoretical workflow, so source-held-out transfer has not been demonstrated.",
        "The 84k source has no genuine observation temperature, so temperature-dependent equilibrium SRO cannot be learned.",
        "Initial symmetry and structural fingerprints may encode configuration-generation signatures in addition to physical geometry.",
        "The chemical domain is restricted to Al–Co–Cr–Cu–Fe–Mn–Ni.",
        "Configurations share alloy systems, compositions, and generation procedures; grouped validation reduces but cannot remove all dependence.",
        "Feature importance and ablation quantify predictive association, not causation.",
        "The validated HCP count is zero, and the DFT extension contains only four configurations.",
    ):
        b.bullet(item)

    b.section("4.3", "Future work")
    for item in (
        "Obtain the MLP-cSRO HCP Warren–Cowley reference arrays and topology calculation used by the authors, then validate the existing 255 CrCoNi frames.",
        "Add an independent HfTiZr HCP configuration/WC/temperature bundle and retain real trajectory or run identifiers.",
        "Extend the target to signed, pair-resolved, shell-resolved SRO rather than relying only on aggregate magnitude.",
        "Recompute a common set of structure descriptors across independent sources and perform source-held-out validation.",
        "Add genuine temperature-dependent records without assigning temperature when it is absent.",
        "Test whether the compact structure-sensitive predictors remain useful across different SQS, Monte Carlo, supercell, and experimental workflows.",
        "Expand the targeted DFT comparison to more compositions and independently selected configurations before discussing general energetic trends.",
    ):
        b.bullet(item)

    # References
    b.page_break()
    b.doc.add_heading("References", level=1)
    b.add_references(
        (
            "R. Zhang et al., “Short-range order and its impact on the CrCoNi medium-entropy alloy,” Nature, vol. 581, pp. 283–287, 2020.",
            "K. Sheriff, Y. Cao, T. Smidt, and R. Freitas, “Quantifying chemical short-range order in metallic alloys,” Proceedings of the National Academy of Sciences, vol. 121, e2322962121, 2024.",
            "J. B. Staunton et al., “A theoretical treatment of atomic short-range order and magnetism in iron-rich b.c.c. alloys,” Journal of Physics: Condensed Matter, vol. 9, pp. 1281–1300, 1997.",
            "W. Schweika and H.-G. Haubold, “Neutron-scattering and Monte Carlo study of short-range order and atomic interaction in Ni-Cr,” Physical Review B, vol. 37, pp. 9240–9248, 1988.",
            "R. Bucher et al., “Short-Range Order in Ni-Rich Ni-Ti Studied by Diffuse Neutron Scattering,” physica status solidi (a), vol. 175, pp. 527–536, 1999.",
            "K. Li, K. Choudhary, B. DeCost, M. Greenwood, and J. Hattrick-Simpers, “Efficient first principles based modeling via machine learning: from simple representations to high entropy materials,” Journal of Materials Chemistry A, 2024, doi: 10.1039/D4TA00982G.",
            "K. Li et al., “DFT dataset for high entropy materials,” Zenodo, record 10854500, 2024, doi: 10.5281/zenodo.10854500.",
            "Y. Rao and W. A. Curtin, “Analytical models of short-range order in FCC and BCC alloys,” Materials Cloud Archive, 2021, doi: 10.24435/materialscloud:qa-ba.",
            "Y. Cao, K. Sheriff, and R. Freitas, “Capturing Short-Range Order in High-Entropy Alloys with Machine Learning Potentials,” npj Computational Materials, 2025, doi: 10.1038/s41524-025-01722-2.",
            "Y. Cao, K. Sheriff, and R. Freitas, “CrCoNi_Cao_2022 / ColabFit dataset,” 2024, doi: 10.60732/76208b62.",
            "S. Mubassira et al., “Chemical short-range order and its influence on selected properties of non-dilute random alloys,” Computational Materials Science, 2025, doi: 10.1016/j.commatsci.2024.113587.",
            "A. I. Bhatti et al., “High-Entropy-Alloys computational toolkit,” Computational Materials Science, 2024, doi: 10.1016/j.commatsci.2024.113196.",
        )
    )

    b.save()
    return b


if __name__ == "__main__":
    thesis = build_thesis()
    print(f"Wrote {DOCX_PATH}")
    print(f"Figures: {thesis.figure_no}; Tables: {thesis.table_no}")
