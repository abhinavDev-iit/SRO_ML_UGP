"""Build the editable supervisor progress report from validated repository outputs.

This module performs no machine-learning analysis. It reads the existing reports,
CSV summaries, feature lists, and PNG figures and assembles them into a traceable
academic DOCX. The PDF is exported from Word by ``export_report_pdf.ps1``.
"""

from __future__ import annotations

import csv
import json
import math
import numbers
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
DELIVERABLES = ROOT / "deliverables"
ASSETS = DELIVERABLES / "report_assets"
DOCX_PATH = DELIVERABLES / "SRO_ML_Project_Progress_Report.docx"
FIGURE_INVENTORY_PATH = DELIVERABLES / "report_figure_inventory.csv"
EVIDENCE_MAP_PATH = DELIVERABLES / "report_evidence_map.md"

NAVY = "17365D"
BLUE = "2E5D8A"
MID_BLUE = "4F81BD"
PALE_BLUE = "DCE6F1"
LIGHT_BLUE = "EAF1F8"
LIGHT_GRAY = "F2F4F7"
MID_GRAY = "697386"
DARK = "222222"
WHITE = "FFFFFF"
CAUTION = "FFF4CE"
RISK = "FDE9E7"

# Named style override to the narrative_proposal preset. The user explicitly
# requires A4; the tighter academic rhythm keeps a figure-rich technical report
# readable without using undersized text.
PAGE_WIDTH = Cm(21.0)
PAGE_HEIGHT = Cm(29.7)
MARGIN = Cm(1.9)
CONTENT_WIDTH_IN = (21.0 - 2 * 1.9) / 2.54
CONTENT_WIDTH_DXA = int(round(CONTENT_WIDTH_IN * 1440))


@dataclass(frozen=True)
class FigureSpec:
    key: str
    path: str
    section: str
    caption: str
    source: str


FIGURES: list[FigureSpec] = [
    FigureSpec("workflow", "deliverables/report_assets/workflow_diagram.png", "2. Overall Workflow", "End-to-end workflow used in the project. This is a report schematic, not an experimental result.", "Created for this report from the documented Phase 1-6 pipeline in logs/pipeline_log.md."),
    FigureSpec("phase_counts", "thesis_outputs/figures/phase4/phase_counts_hcp_exclusion.png", "4. Primary 84k Dataset", "Validated FCC/BCC coverage and explicit exclusion of provisional HCP configurations.", "thesis_outputs/tables/phase4/phase_counts.csv; reports/hcp_data_status.md."),
    FigureSpec("alloy_frequency", "thesis_outputs/figures/phase4/alloy_system_frequency.png", "8. Dataset Characteristics and EDA", "Most represented chemical systems in the validated FCC/BCC cohort. Counts are configurations, not independent experiments.", "thesis_outputs/tables/phase4/alloy_system_counts.csv."),
    FigureSpec("element_frequency", "thesis_outputs/figures/phase4/element_frequency.png", "8. Dataset Characteristics and EDA", "Element coverage across validated configurations.", "thesis_outputs/tables/phase4/element_counts.csv."),
    FigureSpec("component_count", "thesis_outputs/figures/phase4/component_count_distribution.png", "8. Dataset Characteristics and EDA", "Distribution of the number of constituent elements per validated configuration.", "thesis_outputs/tables/phase4/component_counts.csv."),
    FigureSpec("feature_groups", "thesis_outputs/figures/phase4/feature_group_counts.png", "7. Extensive Feature Engineering", "Distribution of candidate predictors across the Phase 4 scientific feature taxonomy.", "thesis_outputs/tables/phase4/feature_group_counts.csv."),
    FigureSpec("feature_provenance", "thesis_outputs/figures/phase4/feature_provenance_counts.png", "7. Extensive Feature Engineering", "Feature counts by provenance class.", "thesis_outputs/tables/phase4/origin_counts.csv."),
    FigureSpec("feature_availability", "thesis_outputs/figures/phase4/feature_availability_distribution.png", "6. Database Standardization and Quality Control", "Feature availability in the validated FCC/BCC database.", "thesis_outputs/tables/phase4/feature_quality.csv."),
    FigureSpec("missingness", "thesis_outputs/figures/phase4/missing_data_pattern_summary.png", "6. Database Standardization and Quality Control", "Missing-data audit for the candidate feature matrix.", "thesis_outputs/tables/phase3/feature_missingness.csv."),
    FigureSpec("target_distribution", "thesis_outputs/figures/phase4/target_distribution_by_phase.png", "8. Dataset Characteristics and EDA", "Distribution of aggregate first-neighbour SRO magnitude for FCC and BCC configurations.", "thesis_outputs/tables/phase4/target_statistics.csv."),
    FigureSpec("target_boxplot", "thesis_outputs/figures/phase4/target_phase_boxplot.png", "19. FCC versus BCC SRO Behaviour", "FCC/BCC target comparison. Visual outliers are suppressed in the box rendering but retained in numerical analysis.", "thesis_outputs/tables/phase4/phase_target_comparison.csv."),
    FigureSpec("pearson", "thesis_outputs/figures/phase4/top_abs_pearson_r.png", "9. Correlation and Association Analysis", "Largest aggregate absolute Pearson correlations with the primary target.", "results/tables/phase4/feature_target_associations.csv."),
    FigureSpec("spearman", "thesis_outputs/figures/phase4/top_abs_spearman_rho.png", "9. Correlation and Association Analysis", "Largest aggregate absolute Spearman rank correlations with the primary target.", "results/tables/phase4/feature_target_associations.csv."),
    FigureSpec("mi_all", "thesis_outputs/figures/phase4/top_mutual_information.png", "9. Correlation and Association Analysis", "Leading aggregate mutual-information screening statistics.", "results/tables/phase4/feature_target_associations.csv."),
    FigureSpec("mi_fcc", "thesis_outputs/figures/phase4/top_mi_fcc.png", "9. Correlation and Association Analysis", "Leading FCC-only mutual-information screening statistics.", "results/tables/phase4/feature_target_associations.csv."),
    FigureSpec("mi_bcc", "thesis_outputs/figures/phase4/top_mi_bcc.png", "9. Correlation and Association Analysis", "Leading BCC-only mutual-information screening statistics.", "results/tables/phase4/feature_target_associations.csv."),
    FigureSpec("phase_assoc", "thesis_outputs/figures/phase4/fcc_bcc_association_comparison.png", "9. Correlation and Association Analysis", "Comparison of leading FCC and BCC Spearman associations.", "thesis_outputs/tables/phase4/phase_association_comparison.csv."),
    FigureSpec("nonlinear", "thesis_outputs/figures/phase4/nonlinear_interpretable_feature_panels.png", "9. Correlation and Association Analysis", "Descriptive nonlinear trends for selected interpretable composition and elemental descriptors.", "data/processed/ml_dataset.parquet; src/analysis/phase4.py."),
    FigureSpec("redundancy", "thesis_outputs/figures/phase4/selected_feature_redundancy_heatmap.png", "10. Feature Redundancy Analysis", "Pearson redundancy map for the preliminary portable descriptor set.", "results/tables/phase4/feature_feature_pearson_matrix.csv; src/analysis/phase4.py."),
    FigureSpec("model_r2", "thesis_outputs/figures/phase5/model_r2_comparison_unified.png", "12. Model Comparison", "Unified alloy-held-out R-squared across screened model and feature-set configurations.", "thesis_outputs/tables/model_comparison_all.csv."),
    FigureSpec("model_mae", "thesis_outputs/figures/phase5/model_mae_comparison_unified.png", "12. Model Comparison", "Unified alloy-held-out mean absolute error across screened configurations.", "thesis_outputs/tables/model_comparison_all.csv."),
    FigureSpec("model_rmse", "thesis_outputs/figures/phase5/model_rmse_comparison_unified.png", "12. Model Comparison", "Unified alloy-held-out root mean squared error across screened configurations.", "thesis_outputs/tables/model_comparison_all.csv."),
    FigureSpec("model_fcc", "thesis_outputs/figures/phase5/model_comparison_fcc.png", "12. Model Comparison", "FCC-only alloy-held-out model comparison.", "thesis_outputs/tables/model_comparison_fcc.csv."),
    FigureSpec("model_bcc", "thesis_outputs/figures/phase5/model_comparison_bcc.png", "12. Model Comparison", "BCC-only alloy-held-out model comparison.", "thesis_outputs/tables/model_comparison_bcc.csv."),
    FigureSpec("split_comparison", "thesis_outputs/figures/phase5/random_vs_grouped_validation.png", "13. Generalization Results", "Random/configuration, composition-held-out, and alloy-system-held-out evaluation of the frozen best pipeline.", "thesis_outputs/tables/grouped_validation_results.csv."),
    FigureSpec("phase_models", "thesis_outputs/figures/phase5/unified_vs_phase_specific.png", "14. Unified Versus Phase-Specific Models", "Unified and phase-specific performance on identical held-out phase rows.", "thesis_outputs/tables/unified_vs_phase_specific_metrics.csv."),
    FigureSpec("feature_sets", "thesis_outputs/figures/phase5/feature_set_comparison.png", "15. Feature-Set Ablation", "Unified HistGradientBoosting performance across feature-set and physical ablation definitions.", "thesis_outputs/tables/feature_set_model_comparison.csv."),
    FigureSpec("compact_refinement", "thesis_outputs/figures/compact_feature_refinement.png", "16. Compact High-Performance Model", "Training-only grouped-validation curve used to select the compact feature count.", "results/tables/phase6/compact_feature_count_validation.csv."),
    FigureSpec("importance_all", "thesis_outputs/figures/phase5/feature_importance_unified.png", "17. Feature Importance and Physical Feature Groups", "Unified held-out permutation importance, expressed as increase in MAE.", "thesis_outputs/tables/feature_importance_unified.csv."),
    FigureSpec("importance_fcc", "thesis_outputs/figures/phase5/feature_importance_fcc.png", "17. Feature Importance and Physical Feature Groups", "FCC held-out permutation importance.", "thesis_outputs/tables/feature_importance_fcc.csv."),
    FigureSpec("importance_bcc", "thesis_outputs/figures/phase5/feature_importance_bcc.png", "17. Feature Importance and Physical Feature Groups", "BCC held-out permutation importance.", "thesis_outputs/tables/feature_importance_bcc.csv."),
    FigureSpec("group_ablation", "thesis_outputs/figures/feature_group_ablation.png", "17. Feature Importance and Physical Feature Groups", "Change in grouped-validation R-squared after removing each physical feature group from BALANCED.", "thesis_outputs/tables/feature_group_ablation.csv."),
    FigureSpec("partial_dependence", "thesis_outputs/figures/focused_partial_dependence.png", "17. Feature Importance and Physical Feature Groups", "Focused partial-dependence summaries for selected descriptors. Curves are descriptive model associations, not causal response functions.", "reports/model_interpretation.md."),
    FigureSpec("configuration_sensitivity", "thesis_outputs/figures/configuration_descriptor_sensitivity.png", "18. Space-Group and Configuration Sensitivity", "Unified sensitivity to removing selected configuration-sensitive descriptors or descriptor groups.", "results/tables/phase6/configuration_descriptor_sensitivity.csv."),
    FigureSpec("fcc_bcc_final", "thesis_outputs/figures/fcc_bcc_final_comparison.png", "19. FCC versus BCC SRO Behaviour", "Comparison of phase target means and phase-specific predictive performance.", "thesis_outputs/tables/phase4/phase_target_comparison.csv; thesis_outputs/tables/best_model_metrics.csv."),
    FigureSpec("robustness", "thesis_outputs/figures/model_robustness.png", "20. Robustness Analysis", "Alloy-held-out R-squared across five deterministic group allocations.", "thesis_outputs/tables/model_robustness_summary.csv."),
    FigureSpec("pred_all", "thesis_outputs/figures/phase5/predicted_vs_actual_unified.png", "12. Model Comparison", "Unified observed versus predicted SRO magnitude on held-out alloy systems.", "results/tables/phase5/best_predictions_all.csv."),
    FigureSpec("pred_fcc", "thesis_outputs/figures/phase5/predicted_vs_actual_fcc.png", "14. Unified Versus Phase-Specific Models", "FCC observed versus predicted SRO magnitude on held-out alloy systems.", "results/tables/phase5/best_predictions_fcc.csv."),
    FigureSpec("pred_bcc", "thesis_outputs/figures/phase5/predicted_vs_actual_bcc.png", "14. Unified Versus Phase-Specific Models", "BCC observed versus predicted SRO magnitude on held-out alloy systems.", "results/tables/phase5/best_predictions_bcc.csv."),
    FigureSpec("residual_all", "thesis_outputs/figures/phase5/residual_plot_unified.png", "21. Error and Extrapolation Analysis", "Unified residuals versus predictions for unseen alloy systems.", "results/tables/phase5/best_predictions_all.csv."),
    FigureSpec("residual_dist", "thesis_outputs/figures/phase5/residual_distribution_unified.png", "21. Error and Extrapolation Analysis", "Distribution of unified outer-test residuals.", "results/tables/phase5/best_predictions_all.csv."),
    FigureSpec("residual_fcc", "thesis_outputs/figures/phase5/residual_plot_fcc.png", "21. Error and Extrapolation Analysis", "FCC-specific residual structure.", "results/tables/phase5/best_predictions_fcc.csv."),
    FigureSpec("residual_bcc", "thesis_outputs/figures/phase5/residual_plot_bcc.png", "21. Error and Extrapolation Analysis", "BCC-specific residual structure.", "results/tables/phase5/best_predictions_bcc.csv."),
    FigureSpec("error_decile", "thesis_outputs/figures/error_by_target_decile.png", "21. Error and Extrapolation Analysis", "Mean absolute error across observed-target deciles.", "results/tables/phase6/error_group_summary.csv."),
    FigureSpec("extrapolation", "thesis_outputs/figures/extrapolation_feature_ranges.png", "21. Error and Extrapolation Analysis", "Fraction of held-out rows outside training 1st-99th percentile intervals for compact predictors.", "results/tables/phase6/feature_extrapolation_audit.csv."),
]


EVIDENCE = [
    ("Executive Summary", "83,797 validated rows: 40,425 FCC, 43,372 BCC, 0 validated HCP", "thesis_outputs/tables/phase3/phase_counts.csv", "phase_counts_hcp_exclusion.png", "HCP candidates are excluded, not counted as labels."),
    ("3. Data Sources", "Seven source families; 46,123 files; 10.1245 GB raw inventory", "reports/data_inventory_metrics.json; SOURCES.md", "Table 2", "Simulation files are not independent datasets."),
    ("5. SRO Target", "Mean absolute first-neighbour Warren-Cowley coefficient across unlike pairs", "reports/sro_definition_84k.md", "Equation 1", "Aggregate target loses sign and pair identity."),
    ("7. Feature Engineering", "348 candidate numerical predictors with provenance", "thesis_outputs/tables/phase4/feature_group_mapping.csv", "feature_group_counts.png", "Availability is source-specific."),
    ("8. EDA", "Overall mean 0.3345; FCC 0.2640; BCC 0.4002", "thesis_outputs/tables/phase4/target_statistics.csv; phase_target_comparison.csv", "target_distribution_by_phase.png", "Phase comparison is descriptive and confounded."),
    ("9. Association", "space_group_number_ini: Pearson 0.4753, Spearman 0.5931", "results/tables/phase4/feature_target_associations.csv", "top_abs_pearson_r.png; top_abs_spearman_rho.png", "Association is not causation; configuration signatures are possible."),
    ("10. Redundancy", "24 constants, 29 near-zero-variance features, 426 highly correlated pairs", "results/tables/phase4/feature_quality.csv; highly_correlated_feature_pairs.csv", "selected_feature_redundancy_heatmap.png", "Correlated groups make individual importance non-additive."),
    ("13. Generalization", "R2 0.9266 random, 0.9161 composition-held-out, 0.8997 alloy-held-out", "thesis_outputs/tables/grouped_validation_results.csv", "random_vs_grouped_validation.png", "Alloy-held-out is the principal result."),
    ("12. Model Comparison", "HistGradientBoosting/BALANCED: unified 0.8997/0.0535/0.0764 R2/MAE/RMSE", "thesis_outputs/tables/best_model_metrics.csv", "predicted_vs_actual_unified.png", "Performance is within the represented theoretical domain."),
    ("14. Phase Models", "FCC R2 0.9058; BCC R2 0.9154", "thesis_outputs/tables/best_model_metrics.csv", "predicted_vs_actual_fcc.png; predicted_vs_actual_bcc.png", "Raw error scales differ by target spread."),
    ("15. Feature Ablation", "Composition-only grouped-CV R2 0.0262; composition + initial structure 0.8783", "thesis_outputs/tables/feature_set_model_comparison.csv", "feature_set_comparison.png", "Structural descriptors may encode configuration generation."),
    ("16. Compact Model", "10 predictors; outer unified R2 0.8917", "results/tables/phase6/compact_feature_count_validation.csv; compact_outer_test_metrics.csv", "compact_feature_refinement.png", "In-source predictive set, not a universal schema."),
    ("17. Feature Groups", "Largest unified group losses: symmetry -0.0666, geometry -0.0246, entropy -0.0220", "thesis_outputs/tables/feature_group_ablation.csv", "feature_group_ablation.png", "Conditional predictive contribution only."),
    ("18. Configuration Sensitivity", "Removing initial space group changes outer R2 by -0.0830 unified", "results/tables/phase6/configuration_descriptor_sensitivity.csv", "configuration_descriptor_sensitivity.png", "May include dataset-construction information."),
    ("19. FCC/BCC", "BCC-FCC mean difference 0.1362; Cohen's d 0.5253", "thesis_outputs/tables/phase4/phase_target_comparison.csv", "fcc_bcc_final_comparison.png", "No causal phase claim."),
    ("20. Robustness", "Five-split unified mean R2 0.8946 +/- 0.0187", "thesis_outputs/tables/model_robustness_summary.csv", "model_robustness.png", "BCC has larger split variability."),
    ("21. Error Analysis", "95th-percentile absolute-error threshold 0.1682; 634 high-error rows", "reports/phase6_metrics.json", "error_by_target_decile.png", "Extreme targets and held-out chemistry are harder."),
    ("22. HCP", "255 provisional CrCoNi configurations; 0 validated HCP labels", "reports/hcp_data_status.md; reports/mlp_csro_cfg_inventory.json", "phase_counts_hcp_exclusion.png", "Missing author WC arrays/topology mapping."),
]


class ReportBuilder:
    def __init__(self) -> None:
        self.doc = Document()
        self.figure_no = 0
        self.table_no = 0
        self.figure_numbers: dict[str, int] = {}
        self.table_titles: list[str] = []
        self._configure_document()

    def _configure_document(self) -> None:
        doc = self.doc
        sec = doc.sections[0]
        sec.page_width = PAGE_WIDTH
        sec.page_height = PAGE_HEIGHT
        sec.top_margin = MARGIN
        sec.bottom_margin = Cm(1.65)
        sec.left_margin = MARGIN
        sec.right_margin = MARGIN
        sec.header_distance = Cm(0.7)
        sec.footer_distance = Cm(0.65)
        sec.different_first_page_header_footer = True

        styles = doc.styles
        normal = styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10.5)
        normal.font.color.rgb = RGBColor.from_string(DARK)
        normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        normal.paragraph_format.space_after = Pt(4)
        normal.paragraph_format.line_spacing = 1.15
        normal.paragraph_format.widow_control = True

        heading_tokens = {
            "Heading 1": (15, NAVY, 14, 6),
            "Heading 2": (12.5, BLUE, 10, 4),
            "Heading 3": (11, NAVY, 8, 3),
        }
        for name, (size, color, before, after) in heading_tokens.items():
            style = styles[name]
            style.font.name = "Calibri"
            style.font.bold = True
            style.font.size = Pt(size)
            style.font.color.rgb = RGBColor.from_string(color)
            style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
            style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
            style.paragraph_format.space_before = Pt(before)
            style.paragraph_format.space_after = Pt(after)
            style.paragraph_format.keep_with_next = True

        caption = styles["Caption"]
        caption.font.name = "Calibri"
        caption.font.size = Pt(9)
        caption.font.italic = True
        caption.font.color.rgb = RGBColor.from_string(DARK)
        caption.paragraph_format.space_before = Pt(2)
        caption.paragraph_format.space_after = Pt(2)
        caption.paragraph_format.keep_with_next = True

        for list_name in ("List Bullet", "List Number"):
            style = styles[list_name]
            style.font.name = "Calibri"
            style.font.size = Pt(10.5)
            style.paragraph_format.space_after = Pt(3)
            style.paragraph_format.line_spacing = 1.15

        # Predefine Word's TOC result styles so the live field stays compact
        # enough to avoid a nearly blank continuation page after refresh.
        for toc_name, left_indent in (("toc 1", 0.0), ("toc 2", 0.22)):
            try:
                style = styles[toc_name]
            except KeyError:
                style = styles.add_style(toc_name, WD_STYLE_TYPE.PARAGRAPH)
            style.font.name = "Calibri"
            style.font.size = Pt(8.5)
            style.paragraph_format.left_indent = Inches(left_indent)
            style.paragraph_format.space_before = Pt(0)
            style.paragraph_format.space_after = Pt(0)
            style.paragraph_format.line_spacing = 1.0

        self._set_header_footer(sec)
        self._set_core_properties()

    def _set_core_properties(self) -> None:
        props = self.doc.core_properties
        props.title = "Data-Driven Analysis and Machine-Learning Prediction of Chemical Short-Range Order in Metallic Alloys"
        props.subject = "UGP Phase-II comprehensive progress and technical review"
        props.author = "Abhinav Choudhary"
        props.keywords = "SRO, Warren-Cowley, machine learning, FCC, BCC, HEA"
        props.comments = "Generated from validated repository outputs; no new ML analysis."

    def _set_header_footer(self, section) -> None:
        header = section.header
        p = header.paragraphs[0]
        p.text = "SRO ML Project | Comprehensive Progress and Technical Review"
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.style = self.doc.styles["Normal"]
        p.paragraph_format.space_after = Pt(0)
        r = p.runs[0]
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(MID_GRAY)
        self._bottom_border(p, "B7C9DD", 6)

        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        r = p.add_run("Page ")
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(MID_GRAY)
        self._add_field(p, "PAGE")

    @staticmethod
    def _bottom_border(paragraph, color: str, size: int) -> None:
        p_pr = paragraph._p.get_or_add_pPr()
        p_bdr = p_pr.find(qn("w:pBdr"))
        if p_bdr is None:
            p_bdr = OxmlElement("w:pBdr")
            p_pr.append(p_bdr)
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), str(size))
        bottom.set(qn("w:space"), "3")
        bottom.set(qn("w:color"), color)
        p_bdr.append(bottom)

    @staticmethod
    def _add_field(paragraph, instruction: str) -> None:
        run = paragraph.add_run()
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = instruction
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        text = OxmlElement("w:t")
        text.text = ""
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run._r.extend([fld_begin, instr, fld_sep, text, fld_end])

    def add_title_page(self) -> None:
        doc = self.doc
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Cm(3.0)
        p.paragraph_format.space_after = Pt(8)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Data-Driven Analysis and Machine-Learning Prediction of\nChemical Short-Range Order in Metallic Alloys")
        r.bold = True
        r.font.name = "Calibri"
        r.font.size = Pt(23)
        r.font.color.rgb = RGBColor.from_string(NAVY)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(26)
        r = p.add_run("UGP Phase-II - Comprehensive Progress and Technical Review Report")
        r.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = RGBColor.from_string(BLUE)

        self.add_callout(
            "Purpose of this report",
            "Transparent supervisor review of the completed database construction, scientific validation, exploratory analysis, grouped machine-learning results, feature interpretation, limitations, and next decisions. This is not the final undergraduate thesis.",
            LIGHT_BLUE,
        )

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(30)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Prepared by\nAbhinav Choudhary\nDepartment of Metallurgical Engineering\nIIT (BHU), Varanasi")
        r.font.size = Pt(12)
        r.bold = True
        r.font.color.rgb = RGBColor.from_string(DARK)

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(24)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Under the guidance of\nProf. Vikas Jindal")
        r.font.size = Pt(12)
        r.bold = True

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(34)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(date.today().strftime("%d %B %Y"))
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor.from_string(MID_GRAY)
        doc.add_page_break()

    def add_toc(self) -> None:
        self.doc.add_heading("Table of Contents", level=1)
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        self._add_field(p, 'TOC \\o "1-3" \\h \\z \\u')
        note = self.doc.add_paragraph("The table of contents is a live Word field and is refreshed during PDF export.")
        note.alignment = WD_ALIGN_PARAGRAPH.CENTER
        note.runs[0].italic = True
        note.runs[0].font.size = Pt(8)
        note.runs[0].font.color.rgb = RGBColor.from_string(MID_GRAY)
        self.doc.add_page_break()

    def add_callout(self, label: str, text: str, fill: str = LIGHT_BLUE) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.15)
        p.paragraph_format.right_indent = Cm(0.15)
        p.paragraph_format.space_before = Pt(5)
        p.paragraph_format.space_after = Pt(7)
        p.paragraph_format.keep_together = True
        p_pr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), fill)
        p_pr.append(shd)
        p_bdr = OxmlElement("w:pBdr")
        for side in ("top", "left", "bottom", "right"):
            border = OxmlElement(f"w:{side}")
            border.set(qn("w:val"), "single")
            border.set(qn("w:sz"), "4")
            border.set(qn("w:space"), "5")
            border.set(qn("w:color"), "D7E2EE")
            p_bdr.append(border)
        p_pr.append(p_bdr)
        r = p.add_run(label + ": ")
        r.bold = True
        r.font.color.rgb = RGBColor.from_string(NAVY)
        p.add_run(text)

    def add_para(self, text: str, *, bold_lead: str | None = None, source: str | None = None) -> None:
        p = self.doc.add_paragraph()
        if bold_lead and text.startswith(bold_lead):
            r = p.add_run(bold_lead)
            r.bold = True
            p.add_run(text[len(bold_lead):])
        else:
            p.add_run(text)
        if source:
            self.add_source(source)

    def add_source(self, source: str) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = False
        r = p.add_run("Repository evidence: " + source)
        r.font.size = Pt(7.5)
        r.font.italic = True
        r.font.color.rgb = RGBColor.from_string(MID_GRAY)

    def add_bullets(self, items: Iterable[str], numbered: bool = False) -> None:
        style = "List Number" if numbered else "List Bullet"
        for item in items:
            p = self.doc.add_paragraph(style=style)
            p.add_run(item)

    def add_table(
        self,
        title: str,
        rows: Sequence[Sequence[object]],
        headers: Sequence[str],
        widths: Sequence[float],
        source: str,
        formats: dict[int, str] | None = None,
        font_size: float = 8.2,
    ) -> int:
        if not math.isclose(sum(widths), CONTENT_WIDTH_IN, abs_tol=0.04):
            raise ValueError(f"Table widths must sum to {CONTENT_WIDTH_IN:.3f} in: {title}")
        self.table_no += 1
        number = self.table_no
        cap = self.doc.add_paragraph(style="Caption")
        cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
        cap.add_run(f"Table {number}. {title}")
        cap.paragraph_format.keep_with_next = True

        table = self.doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        self._set_table_geometry(table, widths)
        table.style = "Table Grid"
        hdr = table.rows[0]
        self._repeat_table_header(hdr)
        for j, header in enumerate(headers):
            cell = hdr.cells[j]
            cell.text = str(header)
            self._shade_cell(cell, PALE_BLUE)
            self._format_cell(cell, font_size=font_size, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        for row in rows:
            cells = table.add_row().cells
            for j, value in enumerate(row):
                text = self._format_value(value, formats.get(j) if formats else None)
                cells[j].text = text
                align = WD_ALIGN_PARAGRAPH.CENTER if self._is_short_value(text) else WD_ALIGN_PARAGRAPH.LEFT
                self._format_cell(cells[j], font_size=font_size, bold=False, align=align)
        # Newly appended rows receive Word defaults; reapply the fixed grid to
        # every cell so the rendered table remains inside the A4 text area.
        self._set_table_geometry(table, widths)
        self.add_source(source)
        self.table_titles.append(title)
        return number

    @staticmethod
    def _format_value(value: object, spec: str | None) -> str:
        if pd.isna(value):
            return "NA"
        if spec and isinstance(value, numbers.Number):
            return format(value, spec)
        return str(value)

    @staticmethod
    def _is_short_value(text: str) -> bool:
        if len(text) <= 14:
            return True
        try:
            float(text)
            return True
        except ValueError:
            return False

    @staticmethod
    def _format_cell(cell, font_size: float, bold: bool, align) -> None:
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        ReportBuilder._set_cell_margins(cell, 80, 110, 80, 110)
        for p in cell.paragraphs:
            p.alignment = align
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(font_size)
                r.bold = bold

    @staticmethod
    def _set_table_geometry(table, widths: Sequence[float]) -> None:
        table.autofit = False
        tbl_pr = table._tbl.tblPr
        tbl_w = tbl_pr.find(qn("w:tblW"))
        if tbl_w is None:
            tbl_w = OxmlElement("w:tblW")
            tbl_pr.append(tbl_w)
        tbl_w.set(qn("w:type"), "dxa")
        tbl_w.set(qn("w:w"), str(sum(int(round(w * 1440)) for w in widths)))
        tbl_ind = tbl_pr.find(qn("w:tblInd"))
        if tbl_ind is None:
            tbl_ind = OxmlElement("w:tblInd")
            tbl_pr.append(tbl_ind)
        tbl_ind.set(qn("w:type"), "dxa")
        tbl_ind.set(qn("w:w"), "110")
        grid = table._tbl.tblGrid
        for child in list(grid):
            grid.remove(child)
        for width in widths:
            col = OxmlElement("w:gridCol")
            col.set(qn("w:w"), str(int(round(width * 1440))))
            grid.append(col)
        for row in table.rows:
            for cell, width in zip(row.cells, widths):
                dxa = str(int(round(width * 1440)))
                tc_pr = cell._tc.get_or_add_tcPr()
                tc_w = tc_pr.find(qn("w:tcW"))
                if tc_w is None:
                    tc_w = OxmlElement("w:tcW")
                    tc_pr.append(tc_w)
                tc_w.set(qn("w:type"), "dxa")
                tc_w.set(qn("w:w"), dxa)
                cell.width = Inches(width)

    @staticmethod
    def _set_cell_margins(cell, top: int, start: int, bottom: int, end: int) -> None:
        tc = cell._tc
        tc_pr = tc.get_or_add_tcPr()
        tc_mar = tc_pr.first_child_found_in("w:tcMar")
        if tc_mar is None:
            tc_mar = OxmlElement("w:tcMar")
            tc_pr.append(tc_mar)
        for m, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
            node = tc_mar.find(qn(f"w:{m}"))
            if node is None:
                node = OxmlElement(f"w:{m}")
                tc_mar.append(node)
            node.set(qn("w:w"), str(value))
            node.set(qn("w:type"), "dxa")

    @staticmethod
    def _shade_cell(cell, fill: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = tc_pr.find(qn("w:shd"))
        if shd is None:
            shd = OxmlElement("w:shd")
            tc_pr.append(shd)
        shd.set(qn("w:fill"), fill)

    @staticmethod
    def _repeat_table_header(row) -> None:
        tr_pr = row._tr.get_or_add_trPr()
        tbl_header = OxmlElement("w:tblHeader")
        tbl_header.set(qn("w:val"), "true")
        tr_pr.append(tbl_header)

    def add_figure(self, key: str, width: float | None = None, max_height: float = 5.55) -> int:
        spec = next(s for s in FIGURES if s.key == key)
        path = ROOT / spec.path
        if not path.exists():
            raise FileNotFoundError(path)
        self.figure_no += 1
        number = self.figure_no
        self.figure_numbers[key] = number
        with Image.open(path) as image:
            ratio = image.width / image.height
        if width is None:
            width = min(CONTENT_WIDTH_IN - 0.12, max_height * ratio)
            width = max(3.8, width)
        if width / ratio > max_height:
            width = max_height * ratio
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path), width=Inches(width))
        # Give every inline scientific figure a meaningful accessibility
        # description directly in DrawingML. Word exposes this as alt text.
        for doc_pr in p._p.xpath(".//wp:docPr"):
            doc_pr.set("name", f"Figure {number}: {spec.key}")
            doc_pr.set("descr", spec.caption)
        cap = self.doc.add_paragraph(style="Caption")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.add_run(f"Figure {number}. {spec.caption}")
        self.add_source(spec.source)
        return number

    def add_section_break(self) -> None:
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        section.page_width = PAGE_WIDTH
        section.page_height = PAGE_HEIGHT
        section.top_margin = MARGIN
        section.bottom_margin = Cm(1.65)
        section.left_margin = MARGIN
        section.right_margin = MARGIN
        section.header_distance = Cm(0.7)
        section.footer_distance = Cm(0.65)
        section.header.is_linked_to_previous = True
        section.footer.is_linked_to_previous = True

    def save(self) -> None:
        DELIVERABLES.mkdir(parents=True, exist_ok=True)
        self.doc.save(DOCX_PATH)


def create_workflow_diagram(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 2400, 980
    image = Image.new("RGB", (width, height), "#" + WHITE)
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    bold_path = Path("C:/Windows/Fonts/arialbd.ttf")
    font = ImageFont.truetype(str(font_path), 35)
    bold = ImageFont.truetype(str(bold_path), 39)
    small = ImageFont.truetype(str(font_path), 27)
    steps = [
        "Raw theoretical\nsources", "Provenance and\nscientific validation", "Standardized\ndatabase",
        "Extensive feature\nengineering", "EDA and\nquality control", "Association and\nredundancy",
        "Grouped machine\nlearning", "FCC/BCC\nphase models", "Interpretation and\nrobustness",
        "Compact feature\nrecommendations",
    ]
    cols = 5
    box_w, box_h = 390, 175
    x_gap, y_gap = 65, 205
    x0, y0 = 75, 145
    coords = []
    for i, label in enumerate(steps):
        row, col = divmod(i, cols)
        if row == 1:
            col = cols - 1 - col
        x = x0 + col * (box_w + x_gap)
        y = y0 + row * (box_h + y_gap)
        coords.append((x, y))
        fill = LIGHT_BLUE if i < 6 else "E7F1E8"
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=26, fill="#" + fill, outline="#" + BLUE, width=5)
        lines = label.split("\n")
        line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
        total_h = sum(line_heights) + 12 * (len(lines) - 1)
        ty = y + (box_h - total_h) / 2
        for line, lh in zip(lines, line_heights):
            bbox = draw.textbbox((0, 0), line, font=font)
            tx = x + (box_w - (bbox[2] - bbox[0])) / 2
            draw.text((tx, ty), line, font=font, fill="#" + NAVY)
            ty += lh + 12
    for i in range(len(coords) - 1):
        x, y = coords[i]
        nx, ny = coords[i + 1]
        if y == ny:
            start = (x + box_w + 8, y + box_h / 2)
            end = (nx - 8, ny + box_h / 2)
        else:
            start = (x + box_w / 2, y + box_h + 8)
            end = (nx + box_w / 2, ny - 8)
        draw.line((start, end), fill="#" + MID_BLUE, width=9)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        ah = 22
        points = [end, (end[0] - ah * math.cos(angle - 0.55), end[1] - ah * math.sin(angle - 0.55)), (end[0] - ah * math.cos(angle + 0.55), end[1] - ah * math.sin(angle + 0.55))]
        draw.polygon(points, fill="#" + MID_BLUE)
    title = "Validated project workflow"
    bbox = draw.textbbox((0, 0), title, font=bold)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, 48), title, font=bold, fill="#" + NAVY)
    note = "Schematic of the completed analysis pipeline; not an experimental result"
    bbox = draw.textbbox((0, 0), note, font=small)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, height - 62), note, font=small, fill="#" + MID_GRAY)
    image.save(path, dpi=(300, 300))


def write_figure_inventory() -> None:
    with FIGURE_INVENTORY_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["report_figure", "key", "path", "section", "width_px", "height_px", "dpi_x", "dpi_y", "included", "caption"])
        writer.writeheader()
        for i, spec in enumerate(FIGURES, 1):
            path = ROOT / spec.path
            with Image.open(path) as image:
                dpi = image.info.get("dpi", (0, 0))
                writer.writerow({
                    "report_figure": i, "key": spec.key, "path": spec.path, "section": spec.section,
                    "width_px": image.width, "height_px": image.height,
                    "dpi_x": round(float(dpi[0]), 2), "dpi_y": round(float(dpi[1]), 2),
                    "included": "yes", "caption": spec.caption,
                })


def write_evidence_map() -> None:
    lines = [
        "# Supervisor progress report evidence map", "",
        "This map links major report statements to the authoritative repository output used during generation. It is an audit aid and is not a substitute for literature citations.", "",
        "| Report section | Statement/result | Repository source | Figure/table source | Caveat |",
        "|---|---|---|---|---|",
    ]
    for row in EVIDENCE:
        escaped = [str(x).replace("|", "\\|") for x in row]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.extend(["", "## Artifact inventories", "", f"- Figure inventory: `{FIGURE_INVENTORY_PATH.relative_to(ROOT)}`", "- Table sources are listed under each Word table and in `thesis_outputs/final_table_manifest.md`.", "- No HCP record is treated as validated.", "- No new ML model was trained for this report.", ""])
    EVIDENCE_MAP_PATH.write_text("\n".join(lines), encoding="utf-8")


def df(path: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / path)


def rows_from_frame(frame: pd.DataFrame, columns: Sequence[str]) -> list[list[object]]:
    return frame.loc[:, columns].values.tolist()


def add_executive_summary(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("Executive Summary", level=1)
    builder.add_para("This report presents the completed SRO machine-learning project for supervisor review before thesis preparation. The project moved from a broad inventory of theoretical and software sources to one scientifically validated, leakage-controlled FCC/BCC modeling database. The main objective was not merely to maximize prediction accuracy, but to determine what the available SRO label means, which descriptors carry reproducible information, how validation independence changes performance, and where configuration-specific signals limit transferability.")
    builder.add_para("The validated database contains 83,797 observations: 40,425 FCC and 43,372 BCC. No HCP label passed the required Warren-Cowley reference/topology validation. The primary target, target_mean_abs_sro_shell1, is the mean absolute first-neighbour Warren-Cowley coefficient across unique unlike-element pairs in each configuration. It measures aggregate ordering magnitude and is not a signed pair-specific alpha.", source="thesis_outputs/tables/phase3/phase_counts.csv; reports/sro_definition_84k.md.")
    builder.add_para("A 348-predictor library was assembled from composition, elemental references, supplied thermodynamic quantities, and leakage-safe initial/pre-relaxation structure descriptors. Final DFT outcomes and relaxed descriptors were excluded. The principal evaluation held out complete alloy systems, with grouped cross-validation inside the training partition.", source="thesis_outputs/tables/phase4/feature_group_mapping.csv; results/tables/phase5/split_audit.csv; reports/ml_data_validation.md.")
    builder.add_para("HistGradientBoosting with 198 BALANCED predictors was the best validated configuration. Alloy-system-held-out R-squared/MAE/RMSE were 0.8997/0.0535/0.0764 unified, 0.9058/0.0348/0.0534 FCC, and 0.9154/0.0563/0.0808 BCC. Five repeated alloy allocations gave a unified mean R-squared of 0.8946 with standard deviation 0.0187.", source="thesis_outputs/tables/best_model_metrics.csv; thesis_outputs/tables/model_robustness_summary.csv.")
    builder.add_para("Training-only compact refinement selected 10 predictors. The compact unified model obtained outer R-squared 0.8917, only 0.0081 below BALANCED. However, most compact predictors are initial-structure or configuration-sensitive descriptors. The compact predictor set is therefore distinct from the minimal common database metadata recommended for future cross-source records.", source="results/tables/phase6/compact_feature_count_validation.csv; results/tables/phase6/compact_outer_test_metrics.csv; reports/final_minimal_feature_recommendation.md.")

    summary_rows = [
        ["Validated observations", "83,797", "FCC 40,425; BCC 43,372; HCP 0"],
        ["Primary target", "target_mean_abs_sro_shell1", "Aggregate absolute first-shell WC SRO"],
        ["Candidate / BALANCED / compact", "348 / 198 / 10", "All leakage-controlled"],
        ["Unified best", "R2 0.8997", "MAE 0.0535; RMSE 0.0764"],
        ["FCC best", "R2 0.9058", "MAE 0.0348; RMSE 0.0534"],
        ["BCC best", "R2 0.9154", "MAE 0.0563; RMSE 0.0808"],
        ["Five-split unified robustness", "0.8946 +/- 0.0187", "Mean +/- SD R2"],
        ["Compact model", "10 features; R2 0.8917", "Untouched alloy-held-out test"],
        ["HCP status", "0 validated", "255 provisional CrCoNi frames excluded"],
    ]
    builder.add_table("Executive summary of validated results", summary_rows, ["Item", "Validated result", "Interpretation / scope"], [2.0, 1.75, CONTENT_WIDTH_IN - 3.75], "phase3/4/5/6 compact tables; detailed sources in deliverables/report_evidence_map.md.", font_size=8.4)
    builder.add_callout("Central scientific caution", "Strong performance depends heavily on initial structure and symmetry information. These descriptors are predictive within the 84k theoretical workflow, but may encode cell/configuration-generation signatures and must not be interpreted as causal material laws or assumed to transfer unchanged across sources.", CAUTION)


def add_background_and_workflow(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("1. Project Background and Objective", level=1)
    builder.add_para("Chemical short-range order describes departures from random chemical occupancy over local neighbour shells. In this project it is represented with Warren-Cowley coefficients. SRO is relevant because it provides a compact statistical description of local chemical arrangement, but detailed claims about mechanisms or property effects require verified literature support and are not inferred here from correlation alone.", source="reports/sro_definition_84k.md; thesis_outputs/literature_support_needed.md.")
    builder.add_para("The work began as a broad source and literature-oriented compilation. Inventory showed that sources differed strongly in representation, phase, temperature, pair/shell convention, structure availability, and independence. The project therefore shifted toward constructing one validated theoretical FCC/BCC database from the 84k HEA source, while retaining other sources as contextual or future validation candidates.", source="reports/data_inventory.md; reports/project_plan.md; logs/pipeline_log.md.")
    builder.add_para("The final objectives were to validate the label convention, engineer an extensive but leakage-controlled feature library, characterize the database, compare associations and redundancy, build grouped-validation models, distinguish unified and phase-specific behavior, refine a compact predictor set, and define minimal common metadata for future sources.", source="README.md; THESIS_HANDOFF.md.")

    d.add_heading("2. Overall Workflow", level=1)
    builder.add_para("The completed workflow is summarized in Figure 1. Each arrow denotes a documented transformation or decision gate. Provisional HCP material exits at validation rather than entering modeling.")
    builder.add_figure("workflow", width=CONTENT_WIDTH_IN - 0.05, max_height=3.0)
    builder.add_para("The workflow separates source validation from feature generation, EDA from model selection, and in-source predictive compactness from cross-source database design. Reproduction commands are provided in Appendix G.")


def add_sources(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("3. Data Sources and Data Inventory", level=1)
    builder.add_para("Seven local source families were identified. The raw inventory contains 46,123 files totaling 10.1245 GB (9.429 GiB). These counts include many repeated simulation outputs, potential files, plots, and scripts; they must not be treated as the number of independent scientific datasets or observations.", source="reports/data_inventory_metrics.json; reports/data_inventory.md.")
    source_rows = [
        ["84k HEA DFT", "DFT", "FCC/BCC", "83,797 validated", "Structures, aggregate SRO, descriptors", "10.5281/zenodo.10854500; GitHub", "Yes"],
        ["Rao-Curtin", "Analytical/MC", "FCC/BCC", "Not normalized", "Pair probabilities, reduced sweeps", "10.24435/materialscloud:qa-ba", "No"],
        ["MLP-cSRO CrCoNi", "MLIP/DFT-MC", "FCC/HCP/liquid", "255 provisional HCP", "CFGs, potentials, derived arrays", "10.1038/s41524-025-01722-2", "Audit only"],
        ["cSRO_lattice", "MLIP MC/MD", "Likely FCC", "Not normalized", "Thermal trajectories, WC arrays", "Local snapshot", "No"],
        ["CrCoNi ColabFit", "DFT", "Unresolved", "1,257 structures; no SRO", "Structures, energy, force, stress", "10.60732/76208b62", "No"],
        ["CMS-EAM", "EAM/MC", "FCC/BCC/HCP", "Incomplete local outputs", "Workflow, structures, property summaries", "10.1016/j.commatsci.2024.113587", "No"],
        ["HEA computational toolkit", "Software", "FCC/BCC/HCP capable", "0 data rows", "SRO/SQS calculation utilities", "10.1016/j.commatsci.2024.113196", "Reference only"],
    ]
    builder.add_table("Data-source inventory and incorporation status", source_rows, ["Source", "Class/method", "Phase", "Usable records", "Major fields", "DOI/repository", "Final analysis"], [0.8, 0.8, 0.65, 0.8, 1.15, 1.3, CONTENT_WIDTH_IN - 5.5], "SOURCES.md; sources.yaml; reports/data_inventory_metrics.json; reports/hcp_data_status.md.", font_size=7.0)
    raw = json.loads((ROOT / "reports/data_inventory_metrics.json").read_text(encoding="utf-8"))["tree"]["datasets"]
    raw_rows = [[name, info["file_count"], info["total_bytes"] / 1e9] for name, info in raw.items()]
    builder.add_table("Raw inventory by source family", raw_rows, ["Inventory family", "Files", "Size (GB)"], [3.7, 1.1, CONTENT_WIDTH_IN - 4.8], "reports/data_inventory_metrics.json.", formats={1: ",d", 2: ".3f"})
    builder.add_para("Only the 84k source supplied a complete, one-to-one initial-structure feature table and validated SRO summary table at the required scale. Other sources were excluded because of unresolved conventions, missing SRO labels, correlated trajectory structure, abstract species, incomplete outputs, or missing HCP reference data. These exclusions are scientific decisions, not data-cleaning failures.", source="SOURCES.md; reports/hcp_data_status.md; reports/data_inventory.md.")


def add_primary_dataset_and_target(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("4. Primary 84k Dataset", level=1)
    builder.add_para("The main source originally contains 84,024 structures spanning 253 source chemical systems. Exactly 227 records lack an initial structure/lattice label; the SRO and initial-feature tables therefore share 83,797 keys. The validated subset contains 40,425 FCC and 43,372 BCC configurations.", source="reports/data_inventory_metrics.json; SOURCES.md; reports/data_quality_report.md.")
    builder.add_para("The source offers separate initial and relaxed structure representations. Relaxed/final energy, volume, space group, force, pressure, magnetization, and related outcomes can encode post-relaxation information that would not be available at prediction time. The default ML view therefore uses initial/pre-relaxation descriptors and explicitly excludes final outcomes.", source="reports/ingestion_84k.md; reports/ml_data_validation.md; data_dictionary.md.")
    builder.add_figure("phase_counts", width=4.7, max_height=3.2)
    phase = df("thesis_outputs/tables/phase3/phase_counts.csv")
    builder.add_table("Validated phase counts", rows_from_frame(phase, ["phase", "observations"]), ["Phase", "Observations"], [4.5, CONTENT_WIDTH_IN - 4.5], "thesis_outputs/tables/phase3/phase_counts.csv.", formats={1: ",d"})

    d.add_heading("5. Definition of the SRO Target", level=1)
    builder.add_para("For central species i, neighbour species j, and shell n, the validated convention is:")
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("alpha_ij^(n) = 1 - P(j | i, n) / c_j")
    r.font.name = "Cambria Math"
    r.font.size = Pt(13)
    r.italic = True
    builder.add_para("Here P(j | i, n) is the conditional probability of finding j around i in shell n and c_j is the global fraction of j. Zero denotes random mixing under the convention; sign carries ordering/avoidance information for an individual pair. The source stores summary statistics rather than the underlying pair identities and values.", source="reports/sro_definition_84k.md.")
    builder.add_callout("Primary ML target", "target_mean_abs_sro_shell1 is the arithmetic mean of |alpha_ij^(1)| over unique unlike-element pairs in a configuration. It measures aggregate first-neighbour ordering magnitude. It is not a signed pair-specific Warren-Cowley coefficient.", LIGHT_BLUE)
    builder.add_para("Absolute aggregation was used because it is the source-specific scalar summary that can be independently reproduced from the supplied binary and ternary structures and is defined for every validated row. Its main limitation is loss of chemical-pair identity and sign: different microscopic ordering patterns can map to the same target magnitude.", source="reports/sro_definition_84k.md; tests/test_hea84k_ingestion.py; reports/study_limitations.md.")


def add_quality_and_features(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("6. Database Standardization and Quality Control", level=1)
    builder.add_para("Standardization includes canonical composition fractions, alloy-system labels, phase normalization, provenance fields, record/configuration identifiers, shell-long SRO normalization, unique-key checks, exact one-to-one joins, and explicit feature origins. The processed database is stored locally as structures, SRO-long, features, and ML Parquet tables.", source="reports/normalized_database_schema.md; data_dictionary.md; reports/data_quality_report.md.")
    qc_rows = [
        ["Validated structure/target join", "83,797 / 83,797", "Pass"],
        ["FCC / BCC / validated HCP", "40,425 / 43,372 / 0", "Pass"],
        ["Candidate predictor missingness", "0%", "Pass"],
        ["Duplicate validated configuration IDs", "0", "Pass"],
        ["Final/relaxed leakage fields in default predictors", "0", "Pass"],
        ["Provisional HCP rows in ML database", "0", "Pass"],
    ]
    builder.add_table("Database quality-control summary", qc_rows, ["Check", "Validated result", "Status"], [3.45, 2.0, CONTENT_WIDTH_IN - 5.45], "reports/data_quality_report.md; reports/phase3_metrics.json; tests/test_phase3_outputs.py; tests/test_phase5.py.")
    builder.add_para("Figure 8 reports complete feature availability and Figure 9 confirms zero missing feature cells in the validated matrix. Structurally unavailable temperature is not fabricated or treated as a complete predictor.")
    builder.add_figure("feature_availability", width=5.5, max_height=3.3)
    builder.add_figure("missingness", width=5.4, max_height=3.0)
    builder.add_para("Leakage control does not imply that every initial descriptor is universally transferable. Initial space group, packing, neighbour geometry, and local fingerprints can still encode how source configurations were constructed. That separate concern is tested in Sections 15, 17, and 18.")

    d.add_heading("7. Extensive Feature Engineering", level=1)
    builder.add_para("The final candidate library contains 348 numerical predictors. It combines source-supplied initial descriptors with composition fractions, component count, ideal configurational entropy, atomic number/mass/radius statistics, size mismatch, electronegativity and pair differences, VEC/electronic statistics, melting-point statistics, and initial structural/symmetry descriptors.", source="thesis_outputs/tables/phase4/feature_group_mapping.csv; reports/feature_groups.md; data_dictionary.md.")
    fg = df("thesis_outputs/tables/phase4/feature_group_counts.csv").sort_values("features", ascending=False)
    builder.add_table("Complete feature-category counts", rows_from_frame(fg, ["feature_group", "features"]), ["Feature category", "Predictors"], [5.1, CONTENT_WIDTH_IN - 5.1], "thesis_outputs/tables/phase4/feature_group_counts.csv.", formats={1: ",d"}, font_size=7.8)
    builder.add_figure("feature_groups", width=5.8, max_height=3.8)
    builder.add_figure("feature_provenance", width=4.9, max_height=3.7)
    builder.add_para("Provenance distinguishes direct-source, composition-derived, elemental-reference-derived, structure-derived, and externally enriched features. Transferability classification separately identifies universally derivable fields, structure-derivable descriptors, source/method-specific fields, and potential configuration encoders. This separation is essential when moving from one homogeneous theoretical source to a future multi-source database.", source="results/tables/phase6/feature_transferability_mapping.csv; reports/feature_transferability.md.")


def add_eda_and_association(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("8. Dataset Characteristics and Exploratory Data Analysis", level=1)
    builder.add_para("The validated cohort spans 246 normalized alloy systems, 9,633 normalized compositions, and 11,354 formula labels. Many rows share chemistry, so row count is not an independence count and grouped validation is required.", source="thesis_outputs/results_summary.md; thesis_outputs/tables/phase4/composition_coverage_by_phase_system.csv.")
    builder.add_para("Figures 3-5 summarize alloy-system, element, and component-count coverage.")
    builder.add_figure("alloy_frequency", width=5.7, max_height=3.8)
    builder.add_figure("element_frequency", width=5.25, max_height=3.25)
    builder.add_figure("component_count", width=5.25, max_height=3.15)
    stats_df = df("thesis_outputs/tables/phase4/target_statistics.csv")
    stat_rows = rows_from_frame(stats_df, ["cohort", "n", "mean", "median", "std", "skewness", "tukey_outlier_count"])
    builder.add_table("Primary-target statistics by cohort", stat_rows, ["Cohort", "n", "Mean", "Median", "SD", "Skew", "Tukey outliers"], [0.7, 0.8, 0.8, 0.8, 0.8, 0.8, CONTENT_WIDTH_IN - 4.7], "thesis_outputs/tables/phase4/target_statistics.csv.", formats={1: ",d", 2: ".4f", 3: ".4f", 4: ".4f", 5: ".3f", 6: ",d"}, font_size=7.7)
    builder.add_para("The overall target mean is 0.3345, median 0.2708, and skewness 1.106. Tukey outliers were retained because they are bounded, plausible SRO configurations rather than automatically invalid records.", source="thesis_outputs/tables/phase4/target_statistics.csv; reports/eda_analysis.md.")
    builder.add_figure("target_distribution", width=5.4, max_height=3.5)

    d.add_heading("9. Correlation and Association Analysis", level=1)
    builder.add_para("Pearson correlation measures linear association; Spearman correlation measures monotonic rank association; mutual information screens for broader statistical dependence. None of these establishes causation. Mutual-information values are ranking statistics that depend on sampling and estimator settings.", source="reports/eda_analysis.md; reports/study_limitations.md.")
    assoc = df("results/tables/phase4/feature_target_associations.csv")
    all_assoc = assoc[assoc["cohort"] == "ALL"]
    top_p = all_assoc.nlargest(10, "abs_pearson_r")
    top_s = all_assoc.nlargest(10, "abs_spearman_rho")
    top_m = all_assoc.nlargest(10, "mutual_information")
    builder.add_table("Top aggregate Pearson associations", rows_from_frame(top_p, ["feature", "pearson_r"]), ["Feature", "Pearson r"], [5.35, CONTENT_WIDTH_IN - 5.35], "results/tables/phase4/feature_target_associations.csv.", formats={1: ".4f"}, font_size=7.8)
    builder.add_figure("pearson", width=5.8, max_height=3.7)
    builder.add_table("Top aggregate Spearman associations", rows_from_frame(top_s, ["feature", "spearman_rho"]), ["Feature", "Spearman rho"], [5.35, CONTENT_WIDTH_IN - 5.35], "results/tables/phase4/feature_target_associations.csv.", formats={1: ".4f"}, font_size=7.8)
    builder.add_figure("spearman", width=5.8, max_height=3.7)
    builder.add_table("Top aggregate mutual-information rankings", rows_from_frame(top_m, ["feature", "mutual_information"]), ["Feature", "Mutual information"], [5.35, CONTENT_WIDTH_IN - 5.35], "results/tables/phase4/feature_target_associations.csv.", formats={1: ".4f"}, font_size=7.8)
    builder.add_figure("mi_all", width=5.9, max_height=3.5)
    builder.add_para("Initial space-group number gives the strongest reported aggregate Pearson (0.4753) and Spearman (0.5931) association. The 5-norm gives the largest aggregate mutual-information statistic (1.7996). Initial symmetry is treated as a configuration/regime signal requiring sensitivity analysis, not as a causal law.", source="results/tables/phase4/feature_target_associations.csv; reports/eda_analysis.md.")
    builder.add_para("Phase-specific nonlinear screens and the cross-phase association comparison are shown in Figures 15-17.")
    builder.add_figure("mi_fcc", width=5.9, max_height=3.5)
    builder.add_figure("mi_bcc", width=5.9, max_height=3.5)
    builder.add_figure("phase_assoc", width=4.1, max_height=4.2)
    builder.add_para("Figure 18 displays binned, descriptive nonlinear trends for a small set of interpretable composition/elemental descriptors. These panels are hypothesis-generating and require literature support before any microscopic interpretation.")
    builder.add_figure("nonlinear", width=6.25, max_height=3.75)


def add_redundancy_and_ml_method(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("10. Feature Redundancy Analysis", level=1)
    builder.add_para("The feature library contains 24 constants, 29 near-zero-variance predictors, nine exact duplicate-column groups, and 426 pairs with absolute aggregate Pearson correlation at least 0.95. Redundancy arises from composition constraints, alternate summary statistics, and physically related elemental descriptors.", source="results/tables/phase4/feature_quality.csv; results/tables/phase4/highly_correlated_feature_pairs.csv; thesis_outputs/thesis_analysis_notes.md.")
    feature_sets = [
        ["FULL_CLEAN", 324, "Leakage-clean, nonconstant library"],
        ["BALANCED_PRELIMINARY", 198, "Redundancy-controlled Phase 5 set"],
        ["MINIMAL_PRELIMINARY", 19, "Portable preliminary hypothesis; poor predictive retention"],
    ]
    builder.add_table("Phase 4 preliminary feature sets", feature_sets, ["Feature set", "Predictors", "Purpose"], [2.1, 1.0, CONTENT_WIDTH_IN - 3.1], "thesis_outputs/tables/phase4/preliminary_feature_sets.csv; reports/feature_redundancy.md.")
    builder.add_figure("redundancy", width=5.15, max_height=5.2)
    builder.add_para("Redundancy reduction was performed to limit unstable importance allocation, reduce computational cost, and create interpretable comparison sets. The sets were hypotheses for grouped model comparison rather than claims that removed features were physically unimportant.")

    d.add_heading("11. Machine-Learning Methodology", level=1)
    builder.add_para("The supervised task predicts target_mean_abs_sro_shell1 for pooled FCC+BCC data and separately for FCC and BCC. Models were implemented as sklearn pipelines so constant filtering and, where needed, scaling were fitted only on training data.", source="src/ml/phase5.py; tests/test_phase5.py.")
    builder.add_para("Tested model families were median dummy, ordinary linear regression, Ridge, ElasticNet, Random Forest, Extra Trees, Gradient Boosting, HistGradientBoosting, and a bounded SVR baseline. Hyperparameters and complete comparison rows are preserved in the Phase 5 model tables.", source="src/ml/phase5.py; thesis_outputs/tables/model_comparison_all.csv.")
    split = df("results/tables/phase5/split_audit.csv")
    split_rows = rows_from_frame(split, ["strategy", "seed", "train_rows", "test_rows", "group_column", "train_groups", "test_groups", "group_overlap"])
    builder.add_table("Validation split audit", split_rows, ["Strategy", "Seed", "Train rows", "Test rows", "Grouping", "Train groups", "Test groups", "Overlap"], [1.25, 0.45, 0.72, 0.72, 1.15, 0.72, 0.72, CONTENT_WIDTH_IN - 5.73], "results/tables/phase5/split_audit.csv.", font_size=7.0)
    builder.add_para("Random/configuration splitting allows highly related chemistry to appear on both sides and is retained only as an optimistic baseline. Composition holdout tests unseen stoichiometries. Alloy-system holdout prevents an elemental combination from appearing in both train and test and is the principal scientific generalization result. Model/feature configuration selection uses grouped inner cross-validation inside the outer training partition.", source="reports/ml_split_strategy.md; src/ml/phase5.py.")


def condensed_models(cohort: str) -> pd.DataFrame:
    path = {"ALL": "thesis_outputs/tables/model_comparison_all.csv", "FCC": "thesis_outputs/tables/model_comparison_fcc.csv", "BCC": "thesis_outputs/tables/model_comparison_bcc.csv"}[cohort]
    data = df(path).copy()
    return data.sort_values("cv_r2_mean", ascending=False).head(12)


def add_model_results(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("12. Model Comparison", level=1)
    builder.add_para("Model selection used inner alloy-system-grouped cross-validation; outer results are reported for scientific evaluation rather than used to choose the winner. HistGradientBoosting with BALANCED predictors was selected for unified, FCC, and BCC cohorts.", source="thesis_outputs/tables/best_model_metrics.csv; reports/model_overfitting_analysis.md.")
    for cohort, title in (("ALL", "Unified"), ("FCC", "FCC"), ("BCC", "BCC")):
        data = condensed_models(cohort)
        rows = rows_from_frame(data, ["model", "feature_set", "declared_features", "cv_r2_mean", "test_r2", "test_mae", "test_rmse"])
        builder.add_table(f"{title} model comparison (top grouped-CV configurations)", rows, ["Model", "Feature set", "p", "CV R2", "Test R2", "MAE", "RMSE"], [1.2, 1.65, 0.4, 0.75, 0.75, 0.75, CONTENT_WIDTH_IN - 5.5], f"thesis_outputs/tables/model_comparison_{'all' if cohort == 'ALL' else cohort.lower()}.csv.", formats={2: ",d", 3: ".4f", 4: ".4f", 5: ".4f", 6: ".4f"}, font_size=7.0)
    builder.add_para("Figures 20-24 show unified R-squared/MAE/RMSE comparisons and phase-specific R-squared comparisons. These visualizations retain the wider model screen while the tables above condense the leading configurations.")
    builder.add_figure("model_r2", width=6.3, max_height=3.25)
    builder.add_figure("model_mae", width=6.3, max_height=3.25)
    builder.add_figure("model_rmse", width=6.3, max_height=3.25)
    builder.add_figure("model_fcc", width=6.3, max_height=3.25)
    builder.add_figure("model_bcc", width=6.3, max_height=3.25)
    best = df("thesis_outputs/tables/best_model_metrics.csv")
    best_rows = rows_from_frame(best, ["cohort", "model", "feature_set", "declared_features", "test_r2", "test_mae", "test_rmse"])
    builder.add_table("Final best-model metrics", best_rows, ["Cohort", "Model", "Features", "p", "R2", "MAE", "RMSE"], [0.65, 1.35, 1.45, 0.4, 0.7, 0.7, CONTENT_WIDTH_IN - 5.25], "thesis_outputs/tables/best_model_metrics.csv.", formats={3: ",d", 4: ".4f", 5: ".4f", 6: ".4f"}, font_size=7.5)
    builder.add_para("The final alloy-held-out metrics are unified 0.8997/0.0535/0.0764, FCC 0.9058/0.0348/0.0534, and BCC 0.9154/0.0563/0.0808 for R-squared/MAE/RMSE, respectively.", source="thesis_outputs/tables/best_model_metrics.csv.")
    builder.add_figure("pred_all", width=4.55, max_height=4.5)

    d.add_heading("13. Generalization Results", level=1)
    gen = df("thesis_outputs/tables/grouped_validation_results.csv")
    gen_all = gen[gen["cohort"] == "ALL"]
    builder.add_table("Unified split/generalization comparison", rows_from_frame(gen_all, ["split_strategy", "train_rows_used", "test_rows", "test_r2", "test_mae", "test_rmse"]), ["Split", "Train", "Test", "R2", "MAE", "RMSE"], [1.7, 0.85, 0.75, 0.85, 0.85, CONTENT_WIDTH_IN - 5.0], "thesis_outputs/tables/grouped_validation_results.csv.", formats={1: ",d", 2: ",d", 3: ".4f", 4: ".4f", 5: ".4f"})
    builder.add_figure("split_comparison", width=4.75, max_height=4.0)
    builder.add_para("Unified R-squared decreases from 0.9266 under random/configuration splitting to 0.9161 under composition holdout and 0.8997 under alloy-system holdout. This decrease is expected as chemical independence becomes stricter; the alloy-held-out value governs conclusions.", source="thesis_outputs/tables/grouped_validation_results.csv.")

    d.add_heading("14. Unified Versus Phase-Specific Models", level=1)
    phase = df("thesis_outputs/tables/unified_vs_phase_specific_metrics.csv")
    builder.add_table("Unified versus phase-specific performance on identical phase rows", rows_from_frame(phase, ["phase", "model_scope", "observations", "r2", "mae", "rmse"]), ["Phase", "Model scope", "Rows", "R2", "MAE", "RMSE"], [0.75, 1.4, 0.85, 0.8, 0.8, CONTENT_WIDTH_IN - 4.6], "thesis_outputs/tables/unified_vs_phase_specific_metrics.csv.", formats={2: ",d", 3: ".4f", 4: ".4f", 5: ".4f"})
    builder.add_figure("phase_models", width=4.8, max_height=3.4)
    builder.add_para("For FCC, the phase-specific model improves R-squared from 0.8668 to 0.9058; for BCC it improves from 0.9038 to 0.9154. The FCC benefit is larger. Separate models are justified for phase interpretation and best in-domain accuracy, while the unified model remains the compact deployment baseline.", source="thesis_outputs/tables/unified_vs_phase_specific_metrics.csv; reports/final_fcc_bcc_interpretation.md.")
    builder.add_figure("pred_fcc", width=4.4, max_height=4.3)
    builder.add_figure("pred_bcc", width=4.4, max_height=4.3)


def add_feature_results(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("15. Feature-Set Ablation", level=1)
    fsets = df("thesis_outputs/tables/feature_set_model_comparison.csv")
    hist = fsets[(fsets["cohort"] == "ALL") & (fsets["model"] == "HistGradientBoosting")].sort_values("cv_r2_mean", ascending=False)
    rows = rows_from_frame(hist, ["feature_set", "declared_features", "cv_r2_mean", "test_r2", "test_mae", "test_rmse"])
    builder.add_table("Unified HistGradientBoosting feature-set comparison", rows, ["Feature set", "p", "CV R2", "Test R2", "MAE", "RMSE"], [2.25, 0.5, 0.85, 0.85, 0.8, CONTENT_WIDTH_IN - 5.25], "thesis_outputs/tables/feature_set_model_comparison.csv.", formats={1: ",d", 2: ".4f", 3: ".4f", 4: ".4f", 5: ".4f"}, font_size=7.4)
    builder.add_figure("feature_sets", width=6.35, max_height=3.1)
    builder.add_para("Grouped-CV R-squared is 0.0262 for composition only, 0.1764 for composition plus phase, and 0.8783 for composition plus initial structure, compared with 0.8803 for BALANCED. The weak composition-only result means configuration-level information is essential within this source. It does not prove that the same structural descriptors transfer unchanged to an independent workflow.", source="thesis_outputs/tables/feature_set_model_comparison.csv; reports/feature_ablation_analysis.md.")

    d.add_heading("16. Compact High-Performance Model", level=1)
    builder.add_para("Phase 6 tested predictor counts 10, 20, 30, 50, 75, 100, 150, and 198. Within each outer-training fold, feature ranking was rebuilt from an additional group split of the fold-training data. Subset size was selected from grouped inner validation only, without repeatedly querying the outer test.", source="src/analysis/phase6.py; results/tables/phase6/compact_feature_count_validation.csv.")
    compact_curve = df("results/tables/phase6/compact_feature_count_validation.csv")
    builder.add_table("Compact feature-count selection", rows_from_frame(compact_curve, ["feature_count", "mean_cv_r2", "std_cv_r2", "mean_cv_mae", "balanced_cv_r2", "acceptance_threshold", "selected"]), ["p", "CV R2", "SD", "CV MAE", "BAL R2", "Threshold", "Selected"], [0.45, 0.85, 0.75, 0.85, 0.85, 1.0, CONTENT_WIDTH_IN - 4.75], "results/tables/phase6/compact_feature_count_validation.csv.", formats={0: ",d", 1: ".4f", 2: ".4f", 3: ".4f", 4: ".4f", 5: ".4f"}, font_size=7.4)
    builder.add_figure("compact_refinement", width=5.2, max_height=3.6)
    compact_metrics = df("results/tables/phase6/compact_outer_test_metrics.csv")
    builder.add_table("Compact-model untouched outer metrics", rows_from_frame(compact_metrics, ["cohort", "declared_features", "test_r2", "test_mae", "test_rmse"]), ["Cohort", "p", "R2", "MAE", "RMSE"], [1.2, 0.8, 1.0, 1.0, CONTENT_WIDTH_IN - 4.0], "results/tables/phase6/compact_outer_test_metrics.csv.", formats={1: ",d", 2: ".4f", 3: ".4f", 4: ".4f"})
    compact = (ROOT / "results/feature_sets/compact_high_performance.txt").read_text(encoding="utf-8").splitlines()
    builder.add_table("Exact compact high-performance predictors", [[i, name] for i, name in enumerate(compact, 1)], ["Order", "Feature"], [0.8, CONTENT_WIDTH_IN - 0.8], "results/feature_sets/compact_high_performance.txt.", font_size=8.2)
    builder.add_para("The 10-feature unified model achieves outer R-squared 0.8917, MAE 0.0537, and RMSE 0.0794. Its absolute R-squared loss relative to BALANCED is 0.0081. Simplification is substantial, but the selected variables remain dominated by configuration-sensitive information.", source="results/tables/phase6/compact_outer_test_metrics.csv; thesis_outputs/tables/best_model_metrics.csv; reports/final_feature_set.md.")

    d.add_heading("17. Feature Importance and Physical Feature Groups", level=1)
    builder.add_para("Permutation importance measures how much held-out error increases when one feature is shuffled. It is conditional on the fitted model and is affected by correlated substitutes. Physical-group ablation retrains after removing a whole descriptor family and is more interpretable, but group effects are still non-additive.", source="reports/model_interpretation.md; reports/feature_group_interpretation.md.")
    builder.add_figure("importance_all", width=6.1, max_height=3.35)
    builder.add_figure("importance_fcc", width=6.1, max_height=3.35)
    builder.add_figure("importance_bcc", width=6.1, max_height=3.35)
    ab = df("thesis_outputs/tables/feature_group_ablation.csv")
    ab_main = ab[ab["removed_group"] != "NONE_BASELINE"]
    builder.add_table("Physical feature-group ablation by cohort", rows_from_frame(ab_main, ["cohort", "removed_group", "removed_features", "mean_cv_r2", "delta_r2_vs_baseline", "delta_mae_vs_baseline"]), ["Cohort", "Removed group", "p removed", "CV R2", "Delta R2", "Delta MAE"], [0.65, 2.25, 0.75, 0.8, 0.85, CONTENT_WIDTH_IN - 5.3], "thesis_outputs/tables/feature_group_ablation.csv.", formats={2: ",d", 3: ".4f", 4: ".4f", 5: ".4f"}, font_size=7.0)
    builder.add_figure("group_ablation", width=5.6, max_height=3.6)
    builder.add_para("In the unified model, removing symmetry gives Delta R-squared -0.0666, structural geometry -0.0246, configurational entropy -0.0220, and electronic/VEC/periodic descriptors -0.0126. These groups contribute the strongest conditional predictive information. No causal mechanism is inferred.", source="thesis_outputs/tables/feature_group_ablation.csv.")
    builder.add_figure("partial_dependence", width=5.6, max_height=5.0)

    d.add_heading("18. Space-Group and Configuration Sensitivity", level=1)
    sensitivity = df("results/tables/phase6/configuration_descriptor_sensitivity.csv")
    builder.add_table("Configuration-descriptor sensitivity", rows_from_frame(sensitivity, ["cohort", "sensitivity_test", "removed_features", "baseline_r2", "test_r2", "delta_r2", "delta_mae"]), ["Cohort", "Removal", "p", "Base R2", "Test R2", "Delta R2", "Delta MAE"], [0.6, 2.25, 0.4, 0.75, 0.75, 0.8, CONTENT_WIDTH_IN - 5.55], "results/tables/phase6/configuration_descriptor_sensitivity.csv.", formats={2: ",d", 3: ".4f", 4: ".4f", 5: ".4f", 6: ".4f"}, font_size=6.8)
    builder.add_figure("configuration_sensitivity", width=6.2, max_height=2.9)
    builder.add_para("Removing initial space group lowers outer R-squared by 0.0830 unified, 0.0751 FCC, and 0.0805 BCC. Removing the full symmetry group lowers R-squared by 0.0950, 0.0725, and 0.1000, respectively. The signal persists within phase, yet it may combine transferable structure information with signatures of SQS/ordered-cell construction, atom count, or preprocessing.", source="results/tables/phase6/configuration_descriptor_sensitivity.csv; reports/configuration_descriptor_sensitivity.md.")


def add_phase_robustness_error_hcp(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("19. FCC versus BCC SRO Behaviour", level=1)
    phase_cmp = df("thesis_outputs/tables/phase4/phase_target_comparison.csv")
    builder.add_table("FCC/BCC target-distribution comparison", rows_from_frame(phase_cmp, ["fcc_mean", "bcc_mean", "mean_difference_bcc_minus_fcc", "cohens_d", "ks_statistic"]), ["FCC mean", "BCC mean", "BCC-FCC", "Cohen d", "KS"], [1.2, 1.2, 1.2, 1.2, CONTENT_WIDTH_IN - 4.8], "thesis_outputs/tables/phase4/phase_target_comparison.csv.", formats={0: ".4f", 1: ".4f", 2: ".4f", 3: ".4f", 4: ".4f"})
    builder.add_figure("target_boxplot", width=4.6, max_height=3.8)
    builder.add_figure("fcc_bcc_final", width=6.15, max_height=3.0)
    builder.add_para("Mean aggregate SRO magnitude is 0.2640 for FCC and 0.4002 for BCC; the BCC-FCC difference is 0.1362, Cohen's d is 0.5253, and the KS statistic is 0.2334. BCC is systematically higher in this dataset. This is a dataset association and must not be interpreted as a causal effect of crystal phase because composition and configuration distributions differ.", source="thesis_outputs/tables/phase4/phase_target_comparison.csv; reports/final_fcc_bcc_interpretation.md.")
    builder.add_para("Both phases rank initial space group, configurational entropy, atom count, normalized entropy, and local electronic differences highly. FCC gives relatively more importance to neighbour-distance/cell-size dispersion; BCC gives more importance to unfilled-state, local space-group, electronegativity, and magnetic-moment differences. Repeated-split mean R-squared is nearly identical, although BCC is less stable across which systems are held out.", source="results/tables/phase5/feature_importance_fcc.csv; feature_importance_bcc.csv; thesis_outputs/tables/model_robustness_summary.csv.")

    d.add_heading("20. Robustness Analysis", level=1)
    robust = df("thesis_outputs/tables/model_robustness_summary.csv")
    builder.add_table("Five-split alloy-system-held-out robustness", rows_from_frame(robust, ["cohort", "seeds", "mean_r2", "std_r2", "min_r2", "max_r2", "mean_mae", "mean_rmse"]), ["Cohort", "Seeds", "Mean R2", "SD", "Min", "Max", "Mean MAE", "Mean RMSE"], [0.65, 0.55, 0.8, 0.7, 0.7, 0.7, 0.9, CONTENT_WIDTH_IN - 5.0], "thesis_outputs/tables/model_robustness_summary.csv.", formats={1: ",d", 2: ".4f", 3: ".4f", 4: ".4f", 5: ".4f", 6: ".4f", 7: ".4f"}, font_size=7.2)
    builder.add_figure("robustness", width=5.0, max_height=3.4)
    builder.add_para("Mean R-squared is 0.8946 unified, 0.9046 FCC, and 0.9042 BCC. Standard deviations are 0.0187, 0.0128, and 0.0287. The main conclusions are therefore not dependent on a single favorable seed, while BCC performance is more sensitive to the particular held-out systems.", source="thesis_outputs/tables/model_robustness_summary.csv; reports/model_robustness.md.")

    d.add_heading("21. Error and Extrapolation Analysis", level=1)
    builder.add_para("The unified seed-42 alloy-held-out predictions contain 12,680 rows. The 95th-percentile absolute-error threshold is 0.1682, defining 634 high-error rows. Errors increase toward the highest target decile and are more frequent for BCC rows.", source="reports/phase6_metrics.json; results/tables/phase6/error_group_summary.csv.")
    alloy_err = df("results/tables/phase5/alloy_system_error.csv")
    alloy_all = alloy_err[alloy_err["cohort"] == "ALL"].nlargest(12, "mae")
    builder.add_table("Highest-MAE held-out alloy systems (unified model)", rows_from_frame(alloy_all, ["chemical_system", "observations", "mae", "rmse", "train_observations_same_system"]), ["Held-out system", "Rows", "MAE", "RMSE", "Same-system train rows"], [2.5, 0.75, 0.85, 0.85, CONTENT_WIDTH_IN - 4.95], "results/tables/phase5/alloy_system_error.csv.", formats={1: ".0f", 2: ".4f", 3: ".4f", 4: ",d"}, font_size=7.5)
    builder.add_figure("residual_all", width=4.8, max_height=4.0)
    builder.add_figure("residual_dist", width=4.7, max_height=3.6)
    builder.add_figure("residual_fcc", width=4.8, max_height=4.0)
    builder.add_figure("residual_bcc", width=4.8, max_height=4.0)
    builder.add_figure("error_decile", width=5.1, max_height=3.5)
    extrap = df("results/tables/phase6/feature_extrapolation_audit.csv")
    builder.add_table("Compact-feature extrapolation screen", rows_from_frame(extrap, ["feature", "outside_train_range_fraction", "outside_train_p01_p99_fraction"]), ["Feature", "Outside train range", "Outside train p01-p99"], [4.5, 1.1, CONTENT_WIDTH_IN - 5.6], "results/tables/phase6/feature_extrapolation_audit.csv.", formats={1: ".4f", 2: ".4f"}, font_size=7.3)
    builder.add_figure("extrapolation", width=6.2, max_height=3.3)
    builder.add_para("No compact-feature test value lies outside the literal training minimum/maximum, but joint feature-space extrapolation remains possible. Absolute error has only weak positive association with nearest-training distance and is more strongly associated with target magnitude. The validated domain is Al-Co-Cr-Cu-Fe-Mn-Ni FCC/BCC configurations from the 84k theoretical workflow, not arbitrary metallic alloys.", source="reports/model_error_analysis.md; reports/study_limitations.md.")

    d.add_heading("22. HCP Investigation", level=1)
    builder.add_callout("Validated HCP count", "Zero. No HCP model, metric, or prediction is included in the validated study.", RISK)
    builder.add_para("The MLP-cSRO audit identified 255 provisional equiatomic CrCoNi HCP configurations. They are 144-atom frames associated with five reported 500 K Monte Carlo trajectories. However, the author six-component HCP Warren-Cowley LOP_*.npy reference arrays and exact ideal-HCP shell/topology mapping are absent from the checked repositories.", source="reports/hcp_data_status.md; reports/mlp_csro_cfg_inventory.json.")
    builder.add_para("Naive distance-ranked reconstruction is not accepted because 98 of 255 frames have a thirteenth-to-twelfth-neighbour distance ratio below 1.02, making the first-shell boundary ambiguous under displacement. These values remain provisional and local.", source="reports/hcp_data_status.md; reports/phase3_metrics.json.")
    hcp_rows = [
        ["MLP-cSRO CrCoNi", "255 provisional HCP CFGs", "500 K study context", "Missing author WC arrays and topology validation", "Obtain compact LOP arrays/code"],
        ["CMS-EAM HfTiZr", "Workflow only; 0 usable rows", "300 K documented", "Generated structures/WC table absent", "Obtain complete HfTiZr bundle"],
    ]
    builder.add_table("HCP candidate status and next validation requirement", hcp_rows, ["Candidate", "Local material", "Temperature", "Blocking gap", "Next action"], [1.2, 1.45, 0.9, 1.8, CONTENT_WIDTH_IN - 5.35], "reports/hcp_data_status.md.", font_size=7.5)
    builder.add_para("The preferred immediate next step is to obtain the compact author HCP WC reference arrays/topology code to validate the existing CrCoNi frames. For chemical independence, the next new source should be a completed HfTiZr HCP configuration/WC/temperature bundle.", source="reports/hcp_data_status.md.")


def add_recommendations_summary_limits(builder: ReportBuilder) -> None:
    d = builder.doc
    d.add_heading("23. Final Feature Recommendations", level=1)
    d.add_heading("23.1 Minimal Common Database Feature Set", level=2)
    builder.add_para("This is a database-design recommendation for every future SRO record, independent of whether a high-performing model can use every field.")
    common_rows = [
        ["Identity/provenance", "record ID, source type, citation/URL/version, source record ID, method"],
        ["Chemistry", "alloy system, canonical composition, per-element fractions, component count"],
        ["State", "phase and validation method; temperature/pressure only if genuinely reported"],
        ["SRO label", "metric/convention, value, sign or magnitude status, pair, shell, topology, aggregation, uncertainty"],
        ["Dependence", "configuration family, trajectory/run/replica/group identifiers"],
        ["Structure", "atom count, structure availability, pre/post-relaxation status"],
        ["Universal descriptors", "configurational entropy and versioned elemental-reference statistics"],
    ]
    builder.add_table("Minimal common database fields", common_rows, ["Category", "Recommended fields"], [1.65, CONTENT_WIDTH_IN - 1.65], "reports/final_minimal_feature_recommendation.md.", font_size=8.0)
    d.add_heading("23.2 Compact High-Performance ML Feature Set", level=2)
    builder.add_para("This is the 10-feature configuration-sensitive predictor set listed in Table 20 and `results/feature_sets/compact_high_performance.txt`. It is recommended for simplified modeling within the current theoretical source, not as a universal cross-source schema.")

    d.add_heading("24. Major Results Summary", level=1)
    major = [
        ["Final database", "83,797 rows", "phase_counts.csv"], ["Phase coverage", "40,425 FCC; 43,372 BCC; 0 HCP", "phase_counts.csv"],
        ["Feature library", "348 candidate; 198 BALANCED; 10 compact", "feature_group_mapping.csv; feature lists"],
        ["Best unified", "HGB; R2 0.8997; MAE 0.0535; RMSE 0.0764", "best_model_metrics.csv"],
        ["Best FCC", "HGB; R2 0.9058; MAE 0.0348; RMSE 0.0534", "best_model_metrics.csv"],
        ["Best BCC", "HGB; R2 0.9154; MAE 0.0563; RMSE 0.0808", "best_model_metrics.csv"],
        ["Robustness", "Unified mean R2 0.8946 +/- 0.0187", "model_robustness_summary.csv"],
        ["Feature ablation", "Composition R2 0.0262; +initial structure 0.8783", "feature_set_model_comparison.csv"],
        ["Compact model", "10 features; unified outer R2 0.8917", "compact_outer_test_metrics.csv"],
        ["Phase target contrast", "FCC 0.2640; BCC 0.4002; d 0.5253", "phase_target_comparison.csv"],
        ["Principal limitation", "One theoretical source; aggregate target; 0 validated HCP", "study_limitations.md"],
    ]
    builder.add_table("Comprehensive final-results summary", major, ["Topic", "Validated result", "Primary repository source"], [1.65, 2.75, CONTENT_WIDTH_IN - 4.4], "Exact paths are listed in deliverables/report_evidence_map.md.", font_size=7.6)

    d.add_heading("25. Limitations", level=1)
    builder.add_bullets([
        "The primary target aggregates absolute unlike-pair coefficients and removes sign and pair identity.",
        "All validated labels come from one theoretical 84k workflow; source-held-out transfer has not been tested.",
        "Validated HCP observations remain zero.",
        "Initial symmetry and local structural fingerprints may encode configuration-generation signatures.",
        "The validated chemistry is limited to Al-Co-Cr-Cu-Fe-Mn-Ni FCC/BCC configurations.",
        "Rows share chemistry and generation procedures; alloy-system grouping reduces but cannot remove workflow-level dependence.",
        "The 84k labels lack a genuine observation temperature, so temperature-dependent SRO cannot be learned.",
        "Correlation, permutation importance, group ablation, and partial dependence do not establish causation.",
        "BALANCED was informed by Phase 4 whole-dataset EDA, so the modeling study is exploratory rather than a pristine prospective confirmation.",
        "Generalization outside represented alloy systems and joint feature distributions remains uncertain.",
    ])
    builder.add_source("reports/study_limitations.md; reports/model_interpretation.md; reports/ml_split_strategy.md.")

    d.add_heading("26. Current Conclusions", level=1)
    builder.add_bullets([
        "A large, provenance-preserving theoretical FCC/BCC SRO database was successfully constructed and validated.",
        "Aggregate first-neighbour SRO magnitude is predicted strongly under complete alloy-system holdout within the represented source domain.",
        "Phase-specific models improve identical-row prediction, particularly for FCC, but the improvement is modest relative to the unified model.",
        "Composition alone is insufficient for configuration-level prediction; initial structural information provides most of the predictive gain.",
        "A 10-feature compact model retains nearly all BALANCED outer performance.",
        "Symmetry, structural geometry, configurational entropy, and electronic/VEC/periodic groups carry the strongest conditional predictive information.",
        "Configuration-sensitive predictors require explicit transferability caution and must not be assigned causal control.",
        "HCP SRO remains unresolved and is the clearest data-extension priority.",
    ])
    builder.add_source("reports/final_feature_set.md; reports/model_robustness.md; reports/final_fcc_bcc_interpretation.md; reports/hcp_data_status.md.")

    d.add_heading("27. Recommended Next Steps for Supervisor Discussion", level=1)
    builder.add_para("The following decisions are intentionally left for supervisor review before the final thesis is prepared:")
    builder.add_bullets([
        "Whether aggregate first-shell SRO magnitude is an appropriate main prediction target.",
        "Whether signed pair-resolved Warren-Cowley SRO should become the next target.",
        "Whether configuration-sensitive initial structural descriptors should remain in the final thesis model.",
        "Whether the thesis should emphasize more transferable composition/thermodynamic descriptors despite lower predictive performance.",
        "Whether additional theoretical databases should be integrated before thesis submission.",
        "The priority and practical route for obtaining validated HCP reference data.",
        "Whether future experimental data should be merged into one model or analyzed separately by source type.",
        "Which analyses and figures should be expanded, condensed, or moved to appendices in the final thesis.",
    ], numbered=True)


def add_appendices(builder: ReportBuilder) -> None:
    d = builder.doc
    builder.add_section_break()
    d.add_heading("Appendix A - Detailed Data Source Inventory", level=1)
    builder.add_para("The authoritative human- and machine-readable registries are `SOURCES.md` and `sources.yaml`. Table 2 summarizes incorporation status; this appendix records the main exclusion logic.")
    rows = [
        ["84k HEA", "Accepted", "Complete initial descriptors and aggregate SRO labels; exact convention reproduced"],
        ["Rao-Curtin", "Not integrated", "Abstract species, presentation-oriented workbooks, unresolved normalized row semantics"],
        ["MLP-cSRO", "HCP provisional", "Missing author HCP WC references and topology validation"],
        ["cSRO_lattice", "Not integrated", "Trajectory dependence and unresolved phase/pair/shell normalization"],
        ["ColabFit CrCoNi", "Not integrated", "Potential-training configurations without explicit SRO labels"],
        ["CMS-EAM", "Not integrated", "Workflow present but consolidated generated SRO structures/table absent"],
        ["HEA toolkit", "Reference only", "Software resource; SRO implementation requires validation before use"],
    ]
    builder.add_table("Detailed source decision log", rows, ["Source", "Status", "Scientific reason"], [1.35, 1.2, CONTENT_WIDTH_IN - 2.55], "SOURCES.md; reports/data_inventory.md; reports/hcp_data_status.md.", font_size=7.8)

    d.add_heading("Appendix B - Complete Feature Categories", level=1)
    fg = df("thesis_outputs/tables/phase4/feature_group_counts.csv").sort_values("features", ascending=False)
    builder.add_table("Feature categories and counts", rows_from_frame(fg, ["feature_group", "features"]), ["Feature group", "Predictors"], [5.2, CONTENT_WIDTH_IN - 5.2], "thesis_outputs/tables/phase4/feature_group_counts.csv.", formats={1: ",d"}, font_size=7.7)
    transfer = df("results/tables/phase6/feature_transferability_mapping.csv")
    trans = transfer.groupby("transferability_class", as_index=False).size().rename(columns={"size": "features"})
    builder.add_table("Transferability-class counts", rows_from_frame(trans, ["transferability_class", "features"]), ["Transferability class", "Predictors"], [5.2, CONTENT_WIDTH_IN - 5.2], "results/tables/phase6/feature_transferability_mapping.csv.", formats={1: ",d"})

    d.add_heading("Appendix C - Extended Correlation Rankings", level=1)
    assoc = df("results/tables/phase4/feature_target_associations.csv")
    for cohort in ("ALL", "FCC", "BCC"):
        sub = assoc[assoc["cohort"] == cohort]
        for metric, value_col, title in (("abs_pearson_r", "pearson_r", "Pearson"), ("abs_spearman_rho", "spearman_rho", "Spearman"), ("mutual_information", "mutual_information", "Mutual information")):
            top = sub.nlargest(15, metric)
            builder.add_table(f"Top {cohort} {title} rankings", rows_from_frame(top, ["feature", value_col]), ["Feature", title], [5.25, CONTENT_WIDTH_IN - 5.25], "results/tables/phase4/feature_target_associations.csv.", formats={1: ".4f"}, font_size=7.3)

    d.add_heading("Appendix D - Full Model Comparison", level=1)
    for cohort, path in (("Unified", "thesis_outputs/tables/model_comparison_all.csv"), ("FCC", "thesis_outputs/tables/model_comparison_fcc.csv"), ("BCC", "thesis_outputs/tables/model_comparison_bcc.csv")):
        data = df(path).sort_values("cv_r2_mean", ascending=False)
        builder.add_table(f"Complete {cohort} screened-model comparison", rows_from_frame(data, ["model", "feature_set", "declared_features", "cv_r2_mean", "test_r2", "test_mae", "test_rmse"]), ["Model", "Feature set", "p", "CV R2", "Test R2", "MAE", "RMSE"], [1.15, 1.7, 0.4, 0.75, 0.75, 0.75, CONTENT_WIDTH_IN - 5.5], path + ".", formats={2: ",d", 3: ".4f", 4: ".4f", 5: ".4f", 6: ".4f"}, font_size=6.7)

    d.add_heading("Appendix E - Additional FCC/BCC Figures", level=1)
    builder.add_para("All phase-specific importance, predicted-versus-actual, residual, and association figures have been included in the main scientific flow. No extra debugging or duplicate figures are added here. The complete included inventory is `deliverables/report_figure_inventory.csv`.")

    d.add_heading("Appendix F - Final Feature Lists", level=1)
    minimal = (ROOT / "results/feature_sets/minimal_common.txt").read_text(encoding="utf-8").splitlines()
    compact = (ROOT / "results/feature_sets/compact_high_performance.txt").read_text(encoding="utf-8").splitlines()
    builder.add_table("MINIMAL_COMMON predictor list", [[i, x] for i, x in enumerate(minimal, 1)], ["Order", "Feature"], [0.8, CONTENT_WIDTH_IN - 0.8], "results/feature_sets/minimal_common.txt.", font_size=7.7)
    builder.add_table("COMPACT_HIGH_PERFORMANCE predictor list", [[i, x] for i, x in enumerate(compact, 1)], ["Order", "Feature"], [0.8, CONTENT_WIDTH_IN - 0.8], "results/feature_sets/compact_high_performance.txt.", font_size=7.7)
    builder.add_para("The complete 324-feature FULL and 198-feature BALANCED ordered lists are maintained as `results/feature_sets/full.txt` and `results/feature_sets/balanced.txt`. They are not reproduced as hundreds of main-report rows because the category/mapping tables provide the scientifically useful overview.")

    d.add_heading("Appendix G - Reproducibility Information", level=1)
    builder.add_para("Run the following commands from the repository root after installing `requirements.txt`. Raw and processed data remain local according to `.gitignore`.")
    commands = [
        "python -m unittest discover -s tests -v",
        "python run_pipeline.py ingest-84k --dry-run",
        "python run_pipeline.py build-phase3",
        "python run_pipeline.py analyze-phase4",
        "python run_pipeline.py train-phase5",
        "python run_pipeline.py interpret-phase6",
        "python src/reporting/build_supervisor_report.py",
        "powershell -ExecutionPolicy Bypass -File src/reporting/export_report_pdf.ps1",
        "python src/reporting/audit_supervisor_report.py",
    ]
    for command in commands:
        p = d.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        r = p.add_run(command)
        r.font.name = "Consolas"
        r.font.size = Pt(8.5)
    builder.add_para("Random seeds, split definitions, relative paths, leakage assertions, HCP exclusion, metric recomputation, and 300-dpi figure checks are covered by the repository tests and audit reports.", source="README.md; reports/reproducibility_audit.md; tests/.")

    d.add_heading("Appendix H - Literature Support Still Required", level=1)
    lit_rows = [
        ["Warren-Cowley interpretation", "Sign convention, shell dependence, limitations of magnitude aggregation"],
        ["Configurational entropy", "Relation to composition complexity and ordering tendency"],
        ["Atomic-size mismatch", "Elastic/size contributions to ordering after controlling correlated descriptors"],
        ["Electronic/VEC differences", "Relation of valence/electronegativity differences to pair ordering"],
        ["Structural topology", "Local descriptors for SRO and risk of SQS/configuration signatures"],
        ["FCC versus BCC", "Comparable controlled studies that separate phase from chemistry"],
        ["Grouped validation", "Best practices for composition/source-aware materials-ML evaluation"],
        ["HCP topology", "Robust shell mapping under displacement and reference CrCoNi/HfTiZr data"],
    ]
    builder.add_table("Literature-support map for supervisor review", lit_rows, ["Observed theme", "Claim requiring verified literature"], [2.0, CONTENT_WIDTH_IN - 2.0], "thesis_outputs/literature_support_needed.md.", font_size=7.8)
    builder.add_para("No unverified reference is inserted by this report. The detailed search-keyword map is maintained in `thesis_outputs/literature_support_needed.md`.")


def build_report() -> ReportBuilder:
    DELIVERABLES.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    create_workflow_diagram(ROOT / FIGURES[0].path)
    write_figure_inventory()
    write_evidence_map()
    builder = ReportBuilder()
    builder.add_title_page()
    builder.add_toc()
    add_executive_summary(builder)
    add_background_and_workflow(builder)
    add_sources(builder)
    add_primary_dataset_and_target(builder)
    add_quality_and_features(builder)
    add_eda_and_association(builder)
    add_redundancy_and_ml_method(builder)
    add_model_results(builder)
    add_feature_results(builder)
    add_phase_robustness_error_hcp(builder)
    add_recommendations_summary_limits(builder)
    add_appendices(builder)
    if builder.figure_no != len(FIGURES):
        missing = [spec.key for spec in FIGURES if spec.key not in builder.figure_numbers]
        raise RuntimeError(f"Not all scientific figures were embedded: {missing}")
    builder.save()
    manifest = {
        "docx": str(DOCX_PATH.relative_to(ROOT)),
        "report_generation_date": date.today().isoformat(),
        "figures": builder.figure_no,
        "tables": builder.table_no,
        "appendices": 8,
        "figure_inventory": str(FIGURE_INVENTORY_PATH.relative_to(ROOT)),
        "evidence_map": str(EVIDENCE_MAP_PATH.relative_to(ROOT)),
        "scientific_analysis_performed": False,
    }
    (DELIVERABLES / "report_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return builder


if __name__ == "__main__":
    built = build_report()
    print(json.dumps({"docx": str(DOCX_PATH), "figures": built.figure_no, "tables": built.table_no, "appendices": 8}, indent=2))
