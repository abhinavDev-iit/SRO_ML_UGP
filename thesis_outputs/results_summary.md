# Phase 4 results summary

| Numerical result | Figure | Table | Cautious interpretation |
|---|---|---|---|
| 83,797 validated rows: 40,425 FCC, 43,372 BCC, 0 validated HCP | `phase_counts_hcp_exclusion.png` | `phase_counts.csv` | FCC/BCC coverage is substantial; HCP generalization cannot yet be assessed. |
| 246 alloy systems, 9,633 normalized compositions, 11,354 formula labels | `alloy_system_frequency.png` | `alloy_system_counts.csv`; `composition_coverage_by_phase_system.csv` | Many rows share chemistry, requiring grouped validation. |
| Target mean 0.3345, median 0.2708, skewness 1.106, 1,036 Tukey outliers | `target_distribution_by_phase.png` | `target_statistics.csv` | Extremes are retained as plausible bounded SRO configurations; optional transforms require sensitivity analysis. |
| BCC/FCC target means 0.4002/0.2640; Cohen's d 0.525; KS distance 0.233 | `target_phase_boxplot.png` | `phase_target_comparison.csv` | Phase distributions differ descriptively, but coverage confounding prevents causal attribution. |
| Strongest aggregate Pearson: `space_group_number_ini`, r=0.4753 | `top_abs_pearson_r.png` | `feature_target_associations.csv` | Initial symmetry is a strong regime/configuration signal, not automatically a mechanistic predictor. |
| Strongest aggregate Spearman: `space_group_number_ini`, rho=0.5931 | `top_abs_spearman_rho.png` | `feature_target_associations.csv` | Monotonic association exceeds linear association; group leakage and structure sensitivity need ablation. |
| Strongest aggregate MI: `5-norm`, MI=1.7996 | `top_mutual_information.png` | `feature_target_associations.csv` | MI is a sample/estimator-dependent ranking statistic, not an effect size. |
| 24 constants; 29 NZV predictors; 426 pairs with |r| >= 0.95 | `selected_feature_redundancy_heatmap.png` | `highly_correlated_feature_pairs.csv`; `feature_quality.csv` | Alternate statistics and composition constraints create substantial mathematical redundancy. |
| Preliminary sets: FULL_CLEAN 324, BALANCED 198, MINIMAL 19 | `selected_feature_redundancy_heatmap.png` | `preliminary_feature_sets.csv` | Sets are hypotheses for Phase 5 comparison, not final selected features. |
| 255 HCP CrCoNi configurations remain provisional and excluded | `phase_counts_hcp_exclusion.png` | `phase_counts.csv` | Missing author WC arrays/topology validation prevents scientific use as labels. |

[LITERATURE SUPPORT REQUIRED] for microscopic explanations of phase-specific descriptor trends.

## Phase 5 model results

| Numerical result | Model / validation | Figure | Table | Cautious interpretation |
|---|---|---|---|---|
| Unified R² 0.8997; MAE 0.0535; RMSE 0.0764 | HistGradientBoosting/BALANCED; alloy-system held out | `predicted_vs_actual_unified.png` | `best_model_metrics.csv` | Strong prediction for unseen source alloy systems, conditional on available initial descriptors. |
| FCC R² 0.9058; MAE 0.0348; RMSE 0.0534 | FCC HistGradientBoosting/BALANCED | `predicted_vs_actual_fcc.png` | `model_comparison_fcc.csv` | FCC has lower raw errors partly because its target spread is smaller. |
| BCC R² 0.9154; MAE 0.0563; RMSE 0.0808 | BCC HistGradientBoosting/BALANCED | `predicted_vs_actual_bcc.png` | `model_comparison_bcc.csv` | BCC has higher R² but also larger raw errors and target spread. |
| FCC phase-specific R² 0.9058 vs unified-on-FCC 0.8668; BCC 0.9154 vs 0.9038 | identical held-out alloy systems | `unified_vs_phase_specific.png` | `unified_vs_phase_specific_metrics.csv` | Separate phase models improve both phases, especially FCC. |
| Unified R²: random 0.9266, composition-held-out 0.9161, alloy-held-out 0.8997 | same CV-selected pipeline re-fitted per split | `random_vs_grouped_validation.png` | `grouped_validation_results.csv` | Random splitting is optimistic; alloy grouping is the primary scientific result. |
| Grouped-CV R²: composition 0.0262; +phase 0.1764; +initial structure 0.8783 | HistGradientBoosting ablation | `feature_set_comparison.png` | `feature_set_model_comparison.csv` | Most predictive information is configuration-sensitive initial geometry, not composition alone. |
| MINIMAL grouped-CV R² 0.1008 vs BALANCED 0.8803 | HistGradientBoosting | `feature_set_comparison.png` | `feature_set_model_comparison.csv` | The 19-feature portable baseline does not retain most accuracy. |
| Removing initial space group lowers R² 0.0794 unified, 0.0811 FCC, 0.0777 BCC | FULL_CLEAN HistGradientBoosting sensitivity | `feature_importance_unified.png` | `space_group_sensitivity.csv` | Within-phase predictive signal exists, but causality is not established. |
| Top unified permutation features: initial space group, configurational entropy, packing efficiency, atom count | held-out 3,000-row deterministic permutation | `feature_importance_unified.png` | `feature_importance_unified.csv` | Importance is conditional and correlated-feature dependent. [LITERATURE SUPPORT REQUIRED] |
| Validated HCP model count 0 | HCP excluded | `phase_counts_hcp_exclusion.png` | `best_model_metrics.csv` | No HCP performance claim is scientifically permitted. |
