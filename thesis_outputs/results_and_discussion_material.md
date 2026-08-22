# Results and discussion material

## 1. Dataset construction

The validated database contains 83,797 theoretical observations joined one-to-one from initial/pre-relaxation descriptors and SRO labels: 40,425 FCC and 43,372 BCC. Final energies, relaxed volumes/symmetry/structures and direct ordering proxies are excluded. Figures: `phase_counts_hcp_exclusion.png`. Tables: `phase_counts.csv`, Phase 3 QA summaries. Caveat: one source workflow dominates.

## 2. Dataset characteristics

The feature library contains 348 numerical candidates with recorded provenance and 0% missingness; 24 are constant, 29 near-zero variance and 426 pairs have |Pearson r| ≥0.95. Figures: feature group/provenance/availability and missingness plots. Caveat: complete values reflect a uniform computational source, not cross-source availability.

## 3. FCC/BCC SRO distributions

Mean aggregate first-shell magnitude is 0.2640 FCC and 0.4002 BCC; difference 0.1362, Cohen's d 0.5253, KS=0.2334. Figures: `target_distribution_by_phase.png`, `target_phase_boxplot.png`, `fcc_bcc_final_comparison.png`. Interpretation: BCC is higher in this dataset; chemistry/configuration confounding prevents a structural causal claim. **[LITERATURE SUPPORT REQUIRED]**

## 4. Correlation analysis

Initial space-group number has the strongest aggregate linear/monotonic association (Pearson r=0.4753; Spearman ρ=0.5931); the 5-norm gives the largest mutual-information ranking statistic (1.7996). Figures: top Pearson/Spearman/MI plots. Caveat: association is not causation and MI magnitude is estimator/sample dependent.

## 5. Feature redundancy

The 348-feature library is highly redundant. Phase 4 constructed FULL_CLEAN (324), BALANCED (198) and a 19-feature preliminary portability set. Figure: `selected_feature_redundancy_heatmap.png`. Caveat: Phase 4 whole-dataset EDA makes downstream BALANCED evaluation exploratory.

## 6. Machine-learning methodology

The principal split holds out 50 alloy systems (12,680 rows), trains on 196 systems (71,117 rows), has zero group overlap and uses three-fold alloy-system GroupKFold internally. Constant filtering and scaling are fitted inside pipelines. HistGradientBoosting hyperparameters are fixed for Phase 6. Tables: split audit and grouped validation. **[LITERATURE SUPPORT REQUIRED]**

## 7. Model performance

HistGradientBoosting with BALANCED is best: unified R²/MAE/RMSE 0.8997/0.0535/0.0764; FCC 0.9058/0.0348/0.0534; BCC 0.9154/0.0563/0.0808. Figures: predicted-versus-actual and model comparison. BCC R² is slightly higher but absolute errors are larger.

## 8. Generalization tests

Unified R² decreases from 0.9266 random/configuration to 0.9161 composition-held-out and 0.8997 alloy-system-held-out. Across five alloy allocations unified mean R² is 0.8946±0.0187. Figures: `random_vs_grouped_validation.png`, `model_robustness.png`. The strongest defensible result is alloy-system holdout, within represented chemistry.

## 9. Feature-set ablation and compact refinement

Composition-only grouped-CV R² is 0.0262; composition+phase 0.1764; composition+initial structure 0.8783; BALANCED 0.8803. Training-only nested refinement selects ten predictors (CV R² 0.8636) and achieves untouched outer R² 0.8917. Figures: feature-set and compact-refinement plots. The old 19-feature preliminary set is rejected as the predictive recommendation.

## 10. Structural versus compositional information

The large structural increment shows configuration-sensitive information is essential in this dataset. Symmetry removal gives ΔCV R² −0.0666 and geometry removal −0.0246. This may combine transferable structural signal with configuration-generation signatures. Figures: group ablation and configuration sensitivity. **[LITERATURE SUPPORT REQUIRED]**

## 11. FCC versus BCC comparison

Phase-specific modeling improves FCC R² from 0.8668 unified-model scoring to 0.9058 and BCC from 0.9038 to 0.9154. FCC gains more. Five-seed means are nearly equal, while BCC is less stable. Separate models are useful for phase interpretation and best accuracy, not evidence of distinct causal mechanisms.

## 12. Feature importance

Space group and configurational entropy lead all cohorts. Atom count, packing/neighbor geometry, normalized entropy, and local valence/unfilled-electron differences follow. Importance rankings and ablations are conditional and correlated. Figures: Phase 5 importance plots; focused partial dependence.

## 13. Physical interpretation

Entropy, electronic differences and initial topology are plausible ordering correlates, but project evidence establishes statistical association and predictive information only. Physical mechanisms require controlled calculations and verified literature. **[LITERATURE SUPPORT REQUIRED]**

## 14. Model limitations

The target removes pair/sign information; data are theoretical and temperature-free; structure descriptors may encode generation identity; observations are dependent; the chemical domain is Al–Co–Cr–Cu–Fe–Mn–Ni; importance is not causal.

## 15. HCP limitation

Validated HCP observations are zero. The 255 provisional CrCoNi frames lack author WC references and validated topology mapping. No HCP model is reported. Conclusions apply to FCC/BCC only.

## 16. Future extension

Obtain compact MLP-cSRO HCP WC references first, then a chemically independent HfTiZr HCP structure/WC/temperature bundle. Recompute universal descriptors consistently and perform source-held-out validation before cross-source claims.
