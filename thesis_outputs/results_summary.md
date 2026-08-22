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
