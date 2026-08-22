# Phase 4 figure captions

1. **Phase coverage and HCP exclusion** (`phase_counts_hcp_exclusion.png`). Validated analysis counts are 40,425 FCC and 43,372 BCC. The 255 HCP configurations are shown only as an excluded provisional category; validated HCP count is zero.
2. **Alloy-system frequency** (`alloy_system_frequency.png`). Twenty-five most represented chemical systems in the validated FCC/BCC cohort; configuration counts do not imply independent experimental samples.
3. **Element frequency** (`element_frequency.png`). Number of validated configurations containing each of the eight source elements.
4. **Component-count distribution** (`component_count_distribution.png`). Coverage by number of constituent elements derived from normalized composition.
5. **Feature-group counts** (`feature_group_counts.png`). Distribution of the 348 predictors across the physically motivated Phase 4 taxonomy.
6. **Feature provenance counts** (`feature_provenance_counts.png`). Counts by direct, composition-derived, elemental-reference-derived, and initial-structure-derived origin.
7. **Feature availability** (`feature_availability_distribution.png`). Availability across the validated FCC/BCC database; every candidate predictor is complete.
8. **Missing-data summary** (`missing_data_pattern_summary.png`). Zero missing cells among 348 predictors and 83,797 rows; structurally unavailable temperature is not treated as a candidate predictor.
9. **Target distribution by phase** (`target_distribution_by_phase.png`). Density histograms of aggregate mean absolute first-shell Warren–Cowley SRO for FCC and BCC configurations.
10. **Target phase boxplot** (`target_phase_boxplot.png`). Robust phase comparison with visual outliers suppressed but retained in every numerical analysis.
11. **Top Pearson associations** (`top_abs_pearson_r.png`). Twenty largest aggregate absolute linear correlations; these are unadjusted associations, not causal effects.
12. **Top Spearman associations** (`top_abs_spearman_rho.png`). Twenty largest aggregate absolute rank correlations. Initial symmetry leads the ranking and is interpreted as a structure/regime signal.
13. **Top mutual-information associations** (`top_mutual_information.png`). Aggregate five-neighbour MI rankings from a deterministic 20,000-row stratified sample; magnitude is estimator-dependent.
14. **FCC mutual information** (`top_mi_fcc.png`). Leading nonlinear screening associations in FCC only.
15. **BCC mutual information** (`top_mi_bcc.png`). Leading nonlinear screening associations in BCC only.
16. **FCC/BCC association comparison** (`fcc_bcc_association_comparison.png`). FCC versus BCC Spearman coefficients for 30 leading phase-specific associations; distance from the diagonal indicates phase instability.
17. **Interpretable nonlinear panels** (`nonlinear_interpretable_feature_panels.png`). Hexbin density and binned-median trends for entropy, size mismatch, electronegativity, VEC, and melting-point descriptors; patterns are descriptive.
18. **Selected-feature redundancy heatmap** (`selected_feature_redundancy_heatmap.png`). Pearson matrix for the 19 portable preliminary descriptors, illustrating remaining physical and mathematical covariance without displaying the unreadable 324-feature full matrix.

All PNGs are generated at 300 dpi. [LITERATURE SUPPORT REQUIRED] for any thesis claim connecting these empirical associations to specific microscopic mechanisms.

## Phase 5 figures

1. **Unified model R² comparison** (`model_r2_comparison_unified.png`). Outer alloy-system-held-out R² for screened model families and feature sets; selection used inner grouped CV.
2. **Unified model MAE comparison** (`model_mae_comparison_unified.png`). Outer MAE for the same configurations; lower is better.
3. **Unified model RMSE comparison** (`model_rmse_comparison_unified.png`). Outer RMSE, emphasizing large residuals.
4. **FCC model comparison** (`model_comparison_fcc.png`). FCC-only alloy-held-out R² across screened configurations.
5. **BCC model comparison** (`model_comparison_bcc.png`). BCC-only alloy-held-out R² across screened configurations.
6. **Unified versus phase-specific** (`unified_vs_phase_specific.png`). Best CV-selected model result for pooled and phase-specific cohorts; exact same-row comparison is tabulated separately.
7. **Feature-set ablation** (`feature_set_comparison.png`). Best unified HistGradientBoosting performance across FULL, BALANCED, MINIMAL and physical ablation sets.
8. **Random versus grouped validation** (`random_vs_grouped_validation.png`). Random, composition-held-out and alloy-system-held-out R² for the frozen best pipeline; the alloy result is primary.
9. **Unified observed versus predicted** (`predicted_vs_actual_unified.png`). Density of outer-test predictions against aggregate first-shell SRO magnitude.
10. **FCC observed versus predicted** (`predicted_vs_actual_fcc.png`). FCC-specific outer-test predictions.
11. **BCC observed versus predicted** (`predicted_vs_actual_bcc.png`). BCC-specific outer-test predictions.
12. **Unified residual plot** (`residual_plot_unified.png`). Observed-minus-predicted residual versus prediction for unseen alloy systems.
13. **Unified residual distribution** (`residual_distribution_unified.png`). Distribution of unified outer-test residuals.
14. **FCC residual plot** (`residual_plot_fcc.png`). FCC-specific residual structure.
15. **BCC residual plot** (`residual_plot_bcc.png`). BCC-specific residual structure.
16. **Unified permutation importance** (`feature_importance_unified.png`). Held-out MAE increase after deterministic feature permutation; correlated descriptors share/reallocate importance.
17. **FCC permutation importance** (`feature_importance_fcc.png`). FCC-specific held-out permutation importance.
18. **BCC permutation importance** (`feature_importance_bcc.png`). BCC-specific held-out permutation importance.

All Phase 5 PNGs are 300 dpi. Model importance is not causality. [LITERATURE SUPPORT REQUIRED] for microscopic explanations.
