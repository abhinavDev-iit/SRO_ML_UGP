# Supervisor progress report evidence map

This map links major report statements to the authoritative repository output used during generation. It is an audit aid and is not a substitute for literature citations.

| Report section | Statement/result | Repository source | Figure/table source | Caveat |
|---|---|---|---|---|
| Executive Summary | 83,797 validated rows: 40,425 FCC, 43,372 BCC, 0 validated HCP | thesis_outputs/tables/phase3/phase_counts.csv | phase_counts_hcp_exclusion.png | HCP candidates are excluded, not counted as labels. |
| 3. Data Sources | Seven source families; 46,123 files; 10.1245 GB raw inventory | reports/data_inventory_metrics.json; SOURCES.md | Table 2 | Simulation files are not independent datasets. |
| 5. SRO Target | Mean absolute first-neighbour Warren-Cowley coefficient across unlike pairs | reports/sro_definition_84k.md | Equation 1 | Aggregate target loses sign and pair identity. |
| 7. Feature Engineering | 348 candidate numerical predictors with provenance | thesis_outputs/tables/phase4/feature_group_mapping.csv | feature_group_counts.png | Availability is source-specific. |
| 8. EDA | Overall mean 0.3345; FCC 0.2640; BCC 0.4002 | thesis_outputs/tables/phase4/target_statistics.csv; phase_target_comparison.csv | target_distribution_by_phase.png | Phase comparison is descriptive and confounded. |
| 9. Association | space_group_number_ini: Pearson 0.4753, Spearman 0.5931 | results/tables/phase4/feature_target_associations.csv | top_abs_pearson_r.png; top_abs_spearman_rho.png | Association is not causation; configuration signatures are possible. |
| 10. Redundancy | 24 constants, 29 near-zero-variance features, 426 highly correlated pairs | results/tables/phase4/feature_quality.csv; highly_correlated_feature_pairs.csv | selected_feature_redundancy_heatmap.png | Correlated groups make individual importance non-additive. |
| 13. Generalization | R2 0.9266 random, 0.9161 composition-held-out, 0.8997 alloy-held-out | thesis_outputs/tables/grouped_validation_results.csv | random_vs_grouped_validation.png | Alloy-held-out is the principal result. |
| 12. Model Comparison | HistGradientBoosting/BALANCED: unified 0.8997/0.0535/0.0764 R2/MAE/RMSE | thesis_outputs/tables/best_model_metrics.csv | predicted_vs_actual_unified.png | Performance is within the represented theoretical domain. |
| 14. Phase Models | FCC R2 0.9058; BCC R2 0.9154 | thesis_outputs/tables/best_model_metrics.csv | predicted_vs_actual_fcc.png; predicted_vs_actual_bcc.png | Raw error scales differ by target spread. |
| 15. Feature Ablation | Composition-only grouped-CV R2 0.0262; composition + initial structure 0.8783 | thesis_outputs/tables/feature_set_model_comparison.csv | feature_set_comparison.png | Structural descriptors may encode configuration generation. |
| 16. Compact Model | 10 predictors; outer unified R2 0.8917 | results/tables/phase6/compact_feature_count_validation.csv; compact_outer_test_metrics.csv | compact_feature_refinement.png | In-source predictive set, not a universal schema. |
| 17. Feature Groups | Largest unified group losses: symmetry -0.0666, geometry -0.0246, entropy -0.0220 | thesis_outputs/tables/feature_group_ablation.csv | feature_group_ablation.png | Conditional predictive contribution only. |
| 18. Configuration Sensitivity | Removing initial space group changes outer R2 by -0.0830 unified | results/tables/phase6/configuration_descriptor_sensitivity.csv | configuration_descriptor_sensitivity.png | May include dataset-construction information. |
| 19. FCC/BCC | BCC-FCC mean difference 0.1362; Cohen's d 0.5253 | thesis_outputs/tables/phase4/phase_target_comparison.csv | fcc_bcc_final_comparison.png | No causal phase claim. |
| 20. Robustness | Five-split unified mean R2 0.8946 +/- 0.0187 | thesis_outputs/tables/model_robustness_summary.csv | model_robustness.png | BCC has larger split variability. |
| 21. Error Analysis | 95th-percentile absolute-error threshold 0.1682; 634 high-error rows | reports/phase6_metrics.json | error_by_target_decile.png | Extreme targets and held-out chemistry are harder. |
| 22. HCP | 255 provisional CrCoNi configurations; 0 validated HCP labels | reports/hcp_data_status.md; reports/mlp_csro_cfg_inventory.json | phase_counts_hcp_exclusion.png | Missing author WC arrays/topology mapping. |

## Artifact inventories

- Figure inventory: `deliverables\report_figure_inventory.csv`
- Table sources are listed under each Word table and in `thesis_outputs/final_table_manifest.md`.
- No HCP record is treated as validated.
- No new ML model was trained for this report.
