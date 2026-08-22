# Thesis handoff: machine learning of chemical short-range order

This document is the final writing-oriented handoff for the undergraduate thesis. It consolidates validated project outputs only; it does not add new analysis, citations, or physical claims. Repository paths are given exactly so every result can be traced to its numerical source.

## 1. Research objective

The project objective was to construct a provenance-preserving, leakage-controlled database of metallic-alloy chemical short-range order (SRO), determine the scientific meaning of the available labels, and evaluate whether aggregate first-neighbour SRO magnitude can be predicted from composition, elemental-reference, phase, and initial/pre-relaxation structure descriptors. A secondary objective was to distinguish predictors that work well within the present theoretical source from descriptors that can be reproduced across future sources. Sources: `README.md`, `reports/project_plan.md`, `reports/feature_transferability.md`.

The validated scope is FCC and BCC alloys drawn from the Al–Co–Cr–Cu–Fe–Mn–Ni chemical domain. Source: `reports/study_limitations.md`.

## 2. Dataset sources

- **84k HEA theoretical dataset:** the sole source of validated labels used for EDA and ML. Its source files, publication/repository provenance, joins, and column conventions are documented in `SOURCES.md`, `sources.yaml`, `reports/data_inventory.md`, and `reports/sro_definition_84k.md`.
- **MLP-cSRO CrCoNi source:** contains provisional HCP configurations, but locally available material lacks the author Warren–Cowley reference arrays and validated topology mapping. It was audited but not merged into the validated database. Source: `reports/hcp_data_status.md`.
- **Rao–Curtin, cSRO_lattice, ColabFit CrCoNi, and CMS-EAM HfTiZr materials:** inspected as contextual or candidate sources; none supplied a validated compact HCP configuration-plus-label bundle suitable for integration. Sources: `SOURCES.md`, `sources.yaml`, `reports/hcp_data_status.md`.

## 3. Final dataset size

The final validated ML dataset contains **83,797 observations**. Source: `thesis_outputs/tables/phase3/phase_counts.csv`; corroboration: `reports/phase6_metrics.json` and `reports/data_quality_report.md`.

The shell-long normalized SRO table contains **335,188 rows**, corresponding to four shell summaries per validated structure. Source: `logs/pipeline_log.md` under “Phase 3: processed database and feature engineering”; table definition: `data_dictionary.md`.

## 4. FCC/BCC/HCP coverage

The validated phase counts are **40,425 FCC**, **43,372 BCC**, and **0 HCP** observations. Source: `thesis_outputs/tables/phase3/phase_counts.csv`; figure: `thesis_outputs/figures/phase4/phase_counts_hcp_exclusion.png`.

All primary conclusions therefore apply to validated FCC and BCC data only. Source: `reports/hcp_data_status.md`.

## 5. Exact SRO target definition

The primary target is `target_mean_abs_sro_shell1`. It is the arithmetic mean of the absolute values of first-neighbour Warren–Cowley coefficients over all unique unlike-element pairs represented in a structure. Source: `reports/sro_definition_84k.md`; field definition: `data_dictionary.md`.

For unlike species \(i\) and \(j\), the underlying pair coefficient follows the Warren–Cowley convention \(\alpha_{ij}^{(1)}=1-P(j\mid i,1)/c_j\), after symmetrization over pair direction as documented for this source. The ML target aggregates \(|\alpha_{ij}^{(1)}|\) across unlike pairs. Source and reconstruction evidence: `reports/sro_definition_84k.md` and `tests/test_hea84k_ingestion.py`.

The target is an **aggregate magnitude**, not a signed pair-specific coefficient. It cannot identify which pair orders, whether an individual pair favours ordering or segregation, or how different pair tendencies compete. Source: `reports/sro_definition_84k.md`; limitation: `reports/study_limitations.md`.

## 6. Data preprocessing

The preprocessing pipeline performs deterministic ID validation, one-to-one joining of initial descriptors and SRO labels, composition canonicalization, phase normalization, shell-long SRO normalization, leakage-field exclusion, and Parquet schema/quality validation. Sources: `src/ingestion/hea84k.py`, `src/pipeline/phase3.py`, `reports/ingestion_84k.md`, `reports/data_quality_report.md`.

Four principal local products are generated: `data/processed/structures.parquet`, `data/processed/sro_long.parquet`, `data/processed/features.parquet`, and `data/processed/ml_dataset.parquet`. They are reproducible but intentionally ignored by Git. Sources: `README.md`, `.gitignore`, `reports/reproducibility_audit.md`.

The validated join retains **83,797 of 83,797 expected modeling observations**. Source: `reports/data_quality_report.md`; audit metrics: `reports/phase3_metrics.json`.

## 7. Feature engineering

The feature library contains **348 candidate numerical predictors**, each with recorded origin and availability class. Source: `thesis_outputs/tables/phase4/feature_group_mapping.csv`; summary: `reports/phase4_metrics.json`.

Feature families include composition fractions, component count, configurational entropy, atomic-number/mass/radius statistics, atomic-size mismatch, electronegativity and pair-difference statistics, VEC and pair-VEC descriptors, melting-point statistics, supplied thermodynamic descriptors, and initial structural/symmetry descriptors. Sources: `data_dictionary.md`, `reports/feature_groups.md`, `thesis_outputs/tables/phase4/feature_group_counts.csv`.

Feature origin is classified as direct source, composition-derived, elemental-reference-derived, structure-derived, or externally enriched. Transferability is separately classified as universally derivable, structure derivable, source/method specific, or potential configuration encoding. Sources: `results/tables/phase6/feature_transferability_mapping.csv`, `reports/feature_transferability.md`.

## 8. Leakage controls

Default ML predictors exclude final energy, relaxed/final volume, final symmetry, relaxed structures, force/pressure/magnetization outcomes, direct SRO fields, target fields, and direct ordering-parameter proxies. Sources: `reports/ml_data_validation.md`, `src/ml/phase5.py`, `tests/test_phase5.py`, `tests/test_phase6.py`.

Only initial/pre-relaxation descriptors are admitted by default. Initial geometry remains scientifically sensitive because it may encode the occupation/configuration used to calculate SRO; it was therefore subjected to explicit feature-set, single-feature, and physical-group ablation. Sources: `reports/configuration_descriptor_sensitivity.md`, `reports/feature_ablation_analysis.md`, `thesis_outputs/tables/feature_group_ablation.csv`.

Constant filtering and scaling are fitted inside each sklearn pipeline rather than before splitting. Source: `src/ml/phase5.py`; validation: `tests/test_phase5.py`.

## 9. EDA findings

The complete engineered predictor matrix has **0% feature missingness** for the validated 84k modeling rows. Source: `thesis_outputs/tables/phase3/feature_missingness.csv`; summary: `reports/data_quality_report.md`.

Phase 4 identified **24 constant features**, **29 near-zero-variance features**, and **426 aggregate feature pairs with absolute Pearson correlation at least 0.95**. Sources: `thesis_outputs/tables/phase4/feature_quality.csv`, `thesis_outputs/tables/phase4/highly_correlated_feature_pairs.csv`, `reports/feature_redundancy.md`.

The overall mean primary target is **0.3345**; FCC and BCC means are reported separately below. Source: `thesis_outputs/tables/phase4/target_statistics.csv`.

Recommended EDA figures are the phase-count, phase-target distribution, association-ranking, and redundancy figures listed in Section 22. Source: `thesis_outputs/final_figure_manifest.md`.

## 10. Correlation findings

`space_group_number_ini` has the strongest aggregate linear and monotonic association reported in Phase 4: **Pearson r = 0.4753** and **Spearman ρ = 0.5931**. Sources: `results/tables/phase4/feature_target_associations.csv`, `reports/eda_analysis.md`; figures: `thesis_outputs/figures/phase4/top_abs_pearson_r.png` and `thesis_outputs/figures/phase4/top_abs_spearman_rho.png`.

The largest reported aggregate mutual-information ranking statistic is **1.7996** for `5-norm`. Sources: `results/tables/phase4/feature_target_associations.csv`, `reports/eda_analysis.md`; figure: `thesis_outputs/figures/phase4/top_mutual_information.png`.

These values are screening associations, not causal effects. Mutual-information magnitude also depends on the estimator and deterministic sample used. Sources: `reports/eda_analysis.md`, `reports/study_limitations.md`.

## 11. Feature selection

The final hierarchy is:

- **FULL:** **324 predictors** after leakage/constant quality filtering. Source: `results/feature_sets/full.txt`.
- **BALANCED:** **198 predictors** after Phase 4 redundancy control; this is the best-performing Phase 5 feature set. Sources: `results/feature_sets/balanced.txt`, `thesis_outputs/tables/best_model_metrics.csv`.
- **COMPACT_HIGH_PERFORMANCE:** **10 predictors** selected using training-partition rankings and grouped inner validation. Sources: `results/feature_sets/compact_high_performance.txt`, `results/tables/phase6/compact_feature_count_validation.csv`.
- **MINIMAL_COMMON:** **18 phase-independent composition/elemental predictors** retained as a portability baseline, not as the best predictive set. Sources: `results/feature_sets/minimal_common.txt`, `reports/final_minimal_feature_recommendation.md`.

The earlier **19-feature MINIMAL_PRELIMINARY** set is not retained as the predictive recommendation because its Phase 5 performance was poor. Sources: `thesis_outputs/tables/phase4/preliminary_feature_sets.csv`, `results/tables/phase5/model_results_all.csv`, `reports/final_feature_set.md`.

## 12. ML models tested

The tested regression families were median DummyRegressor, LinearRegression, Ridge, ElasticNet, RandomForest, ExtraTrees, GradientBoosting, HistGradientBoosting, and a computationally bounded SVR baseline. Exact configurations and results are in `src/ml/phase5.py`, `results/tables/phase5/model_results_all.csv`, `thesis_outputs/tables/model_comparison_fcc.csv`, and `thesis_outputs/tables/model_comparison_bcc.csv`.

Optional XGBoost, LightGBM, and SHAP packages were not installed and were not presented as completed model families. Source: `reports/reproducibility_audit.md`; run record: `logs/pipeline_log.md`.

## 13. Validation strategy

The principal outer evaluation holds out complete alloy systems. With deterministic seed **42**, the primary split contains **71,117 training rows**, **12,680 test rows**, **196 training alloy systems**, **50 held-out alloy systems**, and **zero alloy-system overlap**. Source: `results/tables/phase5/split_audit.csv`.

Model and feature-set comparison uses shuffled three-fold alloy-system GroupKFold within the outer training partition. Source: `reports/ml_split_strategy.md`; implementation: `src/ml/phase5.py`.

Unified HistGradientBoosting R² is **0.9266** under random/configuration splitting, **0.9161** under composition holdout, and **0.8997** under alloy-system holdout. Source: `thesis_outputs/tables/grouped_validation_results.csv`; figure: `thesis_outputs/figures/phase5/random_vs_grouped_validation.png`.

Across five deterministic alloy-system allocations, unified mean R² is **0.8946 ± 0.0187**, FCC mean R² is **0.9046 ± 0.0128**, and BCC mean R² is **0.9042 ± 0.0287**. Source: `thesis_outputs/tables/model_robustness_summary.csv`; figure: `thesis_outputs/figures/model_robustness.png`.

## 14. Final model metrics

All final best models use HistGradientBoosting with the BALANCED feature set:

| Cohort | Predictors | Outer R² | MAE | RMSE | Exact source |
|---|---:|---:|---:|---:|---|
| Unified | 198 | 0.8997 | 0.0535 | 0.0764 | `thesis_outputs/tables/best_model_metrics.csv` |
| FCC | 198 | 0.9058 | 0.0348 | 0.0534 | `thesis_outputs/tables/best_model_metrics.csv` |
| BCC | 198 | 0.9154 | 0.0563 | 0.0808 | `thesis_outputs/tables/best_model_metrics.csv` |

Saved prediction tables independently reproduce these metrics. Sources: `results/tables/phase5/best_predictions_all.csv`, `results/tables/phase5/best_predictions_fcc.csv`, `results/tables/phase5/best_predictions_bcc.csv`; validation: `tests/test_phase5.py`.

## 15. FCC versus BCC comparison

Mean aggregate first-shell SRO magnitude is **0.2640 for FCC** and **0.4002 for BCC**. The BCC-minus-FCC difference is **0.1362**, Cohen’s d is **0.5253**, and the KS statistic is **0.2334**. Source: `thesis_outputs/tables/phase4/phase_target_comparison.csv`; figure: `thesis_outputs/figures/fcc_bcc_final_comparison.png`.

BCC SRO magnitude is therefore systematically higher in this dataset, but phase is not assigned a causal effect because composition and configuration distributions may differ. Source: `reports/final_fcc_bcc_interpretation.md`.

For FCC rows, phase-specific modeling improves R² from **0.8668** for the unified model to **0.9058**. For BCC rows, it improves R² from **0.9038** to **0.9154**. Source: `thesis_outputs/tables/unified_vs_phase_specific_metrics.csv`; figure: `thesis_outputs/figures/phase5/unified_vs_phase_specific.png`.

The phase-specific benefit is larger for FCC, while the repeated-split results do not support calling either phase intrinsically more predictable. Source: `reports/final_fcc_bcc_interpretation.md`; repeated metrics: `thesis_outputs/tables/model_robustness_summary.csv`.

## 16. Compact 10-feature model result

Training-only nested refinement selected the smallest tested accepted set at **10 predictors**. Its mean inner grouped-CV R² is **0.8636**, compared with **0.8803** for the 198-feature BALANCED baseline; the acceptance threshold was **0.8503**. Source: `results/tables/phase6/compact_feature_count_validation.csv`; figure: `thesis_outputs/figures/compact_feature_refinement.png`.

On the untouched outer alloy-system test, the compact unified model achieves **R² = 0.8917**, **MAE = 0.0537**, and **RMSE = 0.0794**. The compact FCC and BCC R² values are **0.9038** and **0.9061**, respectively. Source: `results/tables/phase6/compact_outer_test_metrics.csv`; independent predictions: `results/tables/phase6/compact_outer_predictions_all.csv`, `results/tables/phase6/compact_outer_predictions_fcc.csv`, and `results/tables/phase6/compact_outer_predictions_bcc.csv`.

The exact compact predictors are:

1. `space_group_number_ini`
2. `configurational_entropy_j_mol_k`
3. `max packing efficiency`
4. `NIONS`
5. `range neighbor distance variation`
6. `configurational_entropy_normalized`
7. `minimum local difference in NsUnfilled`
8. `mean local difference in SpaceGroupNumber`
9. `mean local difference in NsValence`
10. `avg_dev local difference in NsValence`

Source for the exact ordered list: `results/feature_sets/compact_high_performance.txt`.

## 17. Most important feature groups

Unified group ablation starts from grouped-CV **R² = 0.8803** and **MAE = 0.0640**. Removing symmetry gives **ΔR² = −0.0666** and **ΔMAE = +0.0172**; removing structural geometry gives **−0.0246/+0.0086**; removing configurational entropy gives **−0.0220/+0.0074**; removing electronic/VEC/periodic descriptors gives **−0.0126/+0.0032**. Source: `thesis_outputs/tables/feature_group_ablation.csv`; figure: `thesis_outputs/figures/feature_group_ablation.png`.

Phase-resolved symmetry removal gives **ΔR² = −0.0901 for FCC** and **−0.0574 for BCC**. Source: `thesis_outputs/tables/feature_group_ablation.csv`; interpretation: `reports/feature_group_interpretation.md`.

Initial space group is the leading held-out permutation feature in unified, FCC, and BCC models. Removing it changes outer R² by **−0.0830 unified**, **−0.0751 FCC**, and **−0.0805 BCC**. Sources: `results/tables/phase5/feature_importance_all.csv`, `results/tables/phase5/feature_importance_fcc.csv`, and `results/tables/phase5/feature_importance_bcc.csv`; removal results: `results/tables/phase6/configuration_descriptor_sensitivity.csv`.

These are conditional predictive contributions, not causal effects. Source: `reports/model_interpretation.md`.

## 18. Main scientific findings

1. Aggregate first-shell SRO magnitude is predictable within the represented 84k theoretical domain under complete alloy-system holdout: unified R² is **0.8997**. Source: `thesis_outputs/tables/best_model_metrics.csv`.
2. The seed-specific result is robust across repeated alloy allocations: unified mean R² is **0.8946 ± 0.0187**. Source: `thesis_outputs/tables/model_robustness_summary.csv`.
3. Composition-only information is inadequate for configuration-level prediction: grouped-CV R² is **0.0262**, whereas composition plus initial structure reaches **0.8783**. Source: `results/tables/phase5/model_results_all.csv`; figure: `thesis_outputs/figures/phase5/feature_set_comparison.png`.
4. Initial symmetry/geometry, configurational entropy, and electronic/valence descriptors provide the strongest conditional predictive information. Source: `thesis_outputs/tables/feature_group_ablation.csv`; interpretation: `reports/feature_group_interpretation.md`.
5. BCC has higher aggregate SRO magnitude than FCC in this dataset: **0.4002 versus 0.2640**, with **d = 0.5253**. Source: `thesis_outputs/tables/phase4/phase_target_comparison.csv`.
6. A **10-feature** model retains most BALANCED performance, with outer R² **0.8917 versus 0.8997**. Sources: `results/tables/phase6/compact_outer_test_metrics.csv`, `thesis_outputs/tables/best_model_metrics.csv`.
7. Configuration-sensitive features dominate the compact model, so the best in-source predictors are not identical to the minimal cross-source database schema. Sources: `results/feature_sets/compact_high_performance.txt`, `reports/feature_transferability.md`, `reports/final_minimal_feature_recommendation.md`.

## 19. Limitations

- The target aggregates absolute unlike-pair values and loses sign and pair identity. Source: `reports/study_limitations.md`.
- All validated labels come from one theoretical workflow, so source-held-out transfer has not been demonstrated. Source: `reports/study_limitations.md`.
- No validated HCP response is available. Source: `reports/hcp_data_status.md`.
- Initial symmetry and structural fingerprints may encode configuration-generation signatures in addition to physical structure. Sources: `reports/configuration_descriptor_sensitivity.md`, `reports/feature_transferability.md`.
- The chemical domain is restricted to Al–Co–Cr–Cu–Fe–Mn–Ni. Source: `reports/study_limitations.md`.
- Observations share alloy systems, compositions, and generation procedures; grouped validation reduces but cannot eliminate all dependence. Source: `reports/ml_split_strategy.md`.
- The 84k target has no genuine observation temperature, so temperature-dependent SRO cannot be learned from it. Sources: `reports/sro_definition_84k.md`, `reports/study_limitations.md`.
- Feature importance, ablation, and partial dependence describe predictive association, not causation. Sources: `reports/model_interpretation.md`, `reports/study_limitations.md`.
- Phase 4 whole-dataset EDA informed BALANCED, so Phase 5 should be presented as exploratory rather than pristine confirmatory evaluation. Source: `reports/study_limitations.md`.

## 20. HCP status

The validated HCP count is **0**, while **255 provisional equiatomic CrCoNi HCP configurations** have been identified. Source: `reports/hcp_data_status.md`; inventory: `reports/mlp_csro_cfg_inventory.json`.

The provisional frames contain **144 atoms** and originate from five reported **500 K** Monte Carlo trajectories, but the exact trajectory grouping is not locally recoverable without author metadata. Source: `reports/hcp_data_status.md`.

Distance-ranked topology is not accepted as validation because **98 of 255 configurations** have a thirteenth-to-twelfth-neighbour distance ratio below **1.02**, making the first-shell boundary ambiguous under displacement. Source: `reports/hcp_data_status.md`; numerical audit: `reports/phase3_metrics.json`.

The missing items are the author six-component HCP `LOP_*.npy` Warren–Cowley references or an equivalent reference table, plus the exact ideal-HCP shell/topology mapping. No HCP model was trained. Source: `reports/hcp_data_status.md`; exclusion tests: `tests/test_mlp_hcp.py` and `tests/test_phase6.py`.

## 21. Future work

1. Obtain the compact MLP-cSRO HCP WC reference arrays and topology calculation used by the authors, then validate the already-local CrCoNi configurations. Source: `reports/hcp_data_status.md`.
2. Add a chemically independent HfTiZr HCP bundle containing configurations, pair-resolved WC outputs, genuine temperature/run metadata, and trajectory grouping. Source: `reports/hcp_data_status.md`.
3. Extend the database to signed, pair-resolved, shell-resolved targets instead of relying only on aggregate magnitude. Source: `reports/study_limitations.md`.
4. Recompute structure descriptors with versioned code across independent sources and perform source-held-out validation. Sources: `reports/feature_transferability.md`, `reports/final_minimal_feature_recommendation.md`.
5. Add genuine temperature-dependent records without inferring missing temperature. Sources: `reports/final_minimal_feature_recommendation.md`, `reports/study_limitations.md`.
6. Test whether configuration-sensitive predictors retain value under different SQS, Monte Carlo, supercell, and experimental workflows. Source: `reports/configuration_descriptor_sensitivity.md`.

## 22. Exact filenames of every thesis-recommended figure

All recommended files below are 300 dpi. Source manifest: `thesis_outputs/final_figure_manifest.md`; resolution validation: `tests/test_phase4.py`, `tests/test_phase5.py`, and `tests/test_phase6.py`.

1. `thesis_outputs/figures/phase4/phase_counts_hcp_exclusion.png`
2. `thesis_outputs/figures/phase4/target_distribution_by_phase.png`
3. `thesis_outputs/figures/phase4/top_abs_spearman_rho.png`
4. `thesis_outputs/figures/phase4/selected_feature_redundancy_heatmap.png`
5. `thesis_outputs/figures/phase5/model_r2_comparison_unified.png`
6. `thesis_outputs/figures/phase5/random_vs_grouped_validation.png`
7. `thesis_outputs/figures/phase5/predicted_vs_actual_unified.png`
8. `thesis_outputs/figures/phase5/predicted_vs_actual_fcc.png`
9. `thesis_outputs/figures/phase5/predicted_vs_actual_bcc.png`
10. `thesis_outputs/figures/phase5/feature_set_comparison.png`
11. `thesis_outputs/figures/phase5/feature_importance_unified.png`
12. `thesis_outputs/figures/feature_group_ablation.png`
13. `thesis_outputs/figures/model_robustness.png`
14. `thesis_outputs/figures/compact_feature_refinement.png`
15. `thesis_outputs/figures/fcc_bcc_final_comparison.png`
16. `thesis_outputs/figures/error_by_target_decile.png`

## 23. Exact filenames of every thesis-recommended table

Source manifest: `thesis_outputs/final_table_manifest.md`.

1. `thesis_outputs/tables/phase3/phase_counts.csv`
2. `thesis_outputs/tables/phase4/feature_group_counts.csv`
3. `thesis_outputs/tables/phase4/target_statistics.csv`
4. `thesis_outputs/tables/phase4/phase_target_comparison.csv`
5. `thesis_outputs/tables/model_comparison_all.csv`
6. `thesis_outputs/tables/grouped_validation_results.csv`
7. `thesis_outputs/tables/best_model_metrics.csv`
8. `thesis_outputs/tables/unified_vs_phase_specific_metrics.csv`
9. `thesis_outputs/tables/model_robustness_summary.csv`
10. `thesis_outputs/tables/feature_group_ablation.csv`
11. `results/tables/phase6/compact_feature_count_validation.csv`
12. `results/feature_sets/compact_high_performance.txt`

Full mappings, predictions, importance tables, and hundreds-column data belong in supplementary material rather than the main thesis. Source: `thesis_outputs/final_table_manifest.md`.

## 24. Results requiring literature support

No citations should be inserted until each claim is verified. The complete search map and suggested keywords are in `thesis_outputs/literature_support_needed.md`.

| Project result | Literature support that must be verified | Project evidence |
|---|---|---|
| Warren–Cowley target definition and aggregation | Standard sign convention, pair probability interpretation, shell dependence, and limitations of magnitude aggregation | `reports/sro_definition_84k.md` |
| Entropy is predictively important; entropy-group ΔR² is −0.0220 | Relationship between ideal configurational entropy, mixture complexity, and ordering tendency | `thesis_outputs/tables/feature_group_ablation.csv` |
| Atomic-size descriptors have small conditional ablation loss | Elastic/size-mismatch contributions to chemical ordering after correlated descriptors are considered | `thesis_outputs/tables/feature_group_ablation.csv` |
| Electronic/VEC/periodic group ΔR² is −0.0126 | How valence and electronegativity differences relate to pair ordering in transition-metal alloys | `thesis_outputs/tables/feature_group_ablation.csv` |
| Symmetry-group ΔR² is −0.0666 | Structural-topology descriptors for SRO and risks of SQS/configuration encoding | `thesis_outputs/tables/feature_group_ablation.csv` |
| BCC mean is 0.4002 versus FCC 0.2640 | Comparable controlled FCC/BCC SRO studies; do not cite phase as causal without controlling chemistry | `thesis_outputs/tables/phase4/phase_target_comparison.csv` |
| Split performance decreases from random to alloy-system holdout | Grouped/source-aware validation practices and composition leakage in materials informatics | `thesis_outputs/tables/grouped_validation_results.csv` |
| HCP remains unvalidated | Robust HCP shell/topology calculation under displacement and relevant CrCoNi/HfTiZr reference data | `reports/hcp_data_status.md` |

## 25. Suggested thesis chapter/section placement

| Thesis chapter/section | Results and material to use | Exact project artifacts |
|---|---|---|
| Introduction — motivation | Need to predict and interpret chemical SRO in multicomponent alloys | `reports/project_plan.md`, `README.md` |
| Literature review — SRO definitions | Warren–Cowley definition, sign/shell/pair conventions; add verified external citations | `reports/sro_definition_84k.md`, `thesis_outputs/literature_support_needed.md` |
| Literature review — materials informatics | Grouped validation, descriptor transferability, leakage risks; add verified external citations | `reports/ml_split_strategy.md`, `reports/feature_transferability.md` |
| Methodology — data sources | 84k validated source and excluded/candidate sources | `SOURCES.md`, `sources.yaml`, `reports/data_inventory.md` |
| Methodology — database construction | Join, normalization, schemas, provenance, processed tables | `reports/data_quality_report.md`, `data_dictionary.md`, `reports/normalized_database_schema.md` |
| Methodology — target | Exact aggregate shell-one WC target and caveats | `reports/sro_definition_84k.md` |
| Methodology — feature engineering | Feature families, origin, availability, and final hierarchy | `reports/feature_groups.md`, `results/tables/phase6/feature_transferability_mapping.csv` |
| Methodology — leakage controls | Initial-only policy, excluded final outcomes, pipeline-owned preprocessing | `reports/ml_data_validation.md`, `src/ml/phase5.py` |
| Methodology — modeling and validation | Model families, outer alloy-system split, inner grouped CV, robustness seeds | `reports/ml_split_strategy.md`, `results/tables/phase5/split_audit.csv`, `reports/model_robustness.md` |
| Results — dataset and EDA | Phase coverage, target distributions, missingness, variance, redundancy | Figures 1–4 in `thesis_outputs/final_figure_manifest.md`; Tables 1–4 in `thesis_outputs/final_table_manifest.md` |
| Results — model comparison | Unified model family and feature-set comparisons | Figures 5 and 10; Tables 5 and 7 in the final manifests |
| Results — generalization | Random/composition/alloy-system splits and repeated robustness | Figures 6 and 13; Tables 6 and 9 in the final manifests |
| Results — final predictions | Unified, FCC, and BCC predicted-versus-actual results | Figures 7–9; `thesis_outputs/tables/best_model_metrics.csv` |
| Results — compact refinement | Training-only size choice and compact outer result | Figure 14; `results/tables/phase6/compact_feature_count_validation.csv`; `results/tables/phase6/compact_outer_test_metrics.csv` |
| Discussion — feature interpretation | Permutation importance, physical-group ablation, transferability | Figures 11–12; Table 10; `reports/model_interpretation.md` |
| Discussion — FCC versus BCC | Target contrast, phase-specific benefit, confounding warning | Figure 15; Tables 4 and 8; `reports/final_fcc_bcc_interpretation.md` |
| Discussion — model errors/domain | Error at extreme targets, held-out systems, extrapolation caution | Figure 16; `reports/model_error_analysis.md` |
| Limitations | Aggregate target, theoretical dominance, configuration signatures, chemical domain, importance limits | `reports/study_limitations.md` |
| HCP limitation and future work | Provisional CrCoNi configurations, missing references, HfTiZr recommendation | `reports/hcp_data_status.md` |
| Reproducibility / appendix | Commands, tests, exact feature lists, supplementary tables | `reports/reproducibility_audit.md`, `README.md`, `results/feature_sets/` |

## Key Results to Present to Supervisor

- The validated database contains **83,797 observations: 40,425 FCC, 43,372 BCC, and 0 validated HCP**. Source: `thesis_outputs/tables/phase3/phase_counts.csv`.
- The target is `target_mean_abs_sro_shell1`, the mean absolute first-neighbour Warren–Cowley coefficient across unlike pairs—not a signed pair-specific value. Source: `reports/sro_definition_84k.md`.
- The best unified HistGradientBoosting model with **198 BALANCED predictors** achieves **R² 0.8997, MAE 0.0535, RMSE 0.0764** on completely held-out alloy systems. Source: `thesis_outputs/tables/best_model_metrics.csv`.
- FCC achieves **R² 0.9058** and BCC **R² 0.9154** under the same primary protocol. Source: `thesis_outputs/tables/best_model_metrics.csv`.
- The unified result is stable across repeated alloy allocations: **mean R² 0.8946 ± 0.0187**. Source: `thesis_outputs/tables/model_robustness_summary.csv`.
- Composition alone gives grouped-CV **R² 0.0262**, while composition plus initial structure gives **0.8783**. Source: `results/tables/phase5/model_results_all.csv`.
- A **10-feature compact model** retains strong performance with outer **R² 0.8917**. Sources: `results/feature_sets/compact_high_performance.txt`, `results/tables/phase6/compact_outer_test_metrics.csv`.
- Symmetry, structural geometry, configurational entropy, and electronic/VEC/periodic descriptors are the strongest conditional feature groups. Source: `thesis_outputs/tables/feature_group_ablation.csv`.
- BCC mean aggregate SRO is **0.4002**, compared with **0.2640 for FCC**, but this is a dataset association rather than a demonstrated causal phase effect. Source: `thesis_outputs/tables/phase4/phase_target_comparison.csv`; interpretation: `reports/final_fcc_bcc_interpretation.md`.
- HCP modeling remains scientifically withheld: **255 provisional configurations** exist, but **0 validated HCP WC labels** are available. Source: `reports/hcp_data_status.md`.
- The project is locally reproducible through the documented Phase 3–6 commands, and the final suite passes **34 tests**. Source: `reports/reproducibility_audit.md`.
