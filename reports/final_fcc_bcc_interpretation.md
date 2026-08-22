# Final FCC–BCC interpretation

## Verified target contrast

Across all validated rows, mean aggregate first-shell SRO magnitude is 0.2640 for FCC and 0.4002 for BCC. The BCC-minus-FCC difference is 0.1362; Cohen's d is 0.5253 and the two-sample KS statistic is 0.2334. Thus BCC values are systematically higher **in this dataset**. Composition, configuration generation, cell sizes and chemical-system coverage differ, so this is not evidence that BCC structure alone causes higher SRO.

## Predictability and shared descriptors

The seed-42 phase-specific BALANCED models achieve R² 0.9058/MAE 0.0348/RMSE 0.0534 for FCC and 0.9154/0.0563/0.0808 for BCC. BCC has slightly higher R², but larger absolute errors because its target distribution is broader and larger. Across five alloy splits the means are effectively equal (FCC 0.9046; BCC 0.9042), while BCC is less stable (SD 0.0287 versus 0.0128). It is therefore not robust to call one phase intrinsically more predictable.

Both phases rank initial space group, configurational entropy, atom count, normalized entropy, local valence/unfilled-electron differences and the 5-norm highly. FCC gives more importance to neighbour-distance variation and relative cell-size dispersion. BCC gives more importance to unfilled-state, space-group-difference, electronegativity and magnetic-moment local differences. These are predictive associations subject to correlated-feature and workflow confounding.

Group ablation agrees that symmetry is dominant in both phases, with a larger FCC grouped-CV loss (ΔR² −0.0901) than BCC (−0.0574). Entropy and electronic/VEC/periodic groups are important in both. Structural geometry has a larger conditional loss in FCC (−0.0104) than BCC (−0.0042), whereas explicit composition removal is larger in BCC (−0.0094) than FCC (−0.0063). These conditional differences are modest outside the symmetry group and are not additive.

## Unified versus separate models

For FCC test rows, a phase-specific model improves R² from 0.8668 to 0.9058 and MAE from 0.0438 to 0.0348. For BCC, R² improves from 0.9038 to 0.9154 and MAE from 0.0621 to 0.0563. Separate models therefore provide a meaningful FCC benefit and a smaller BCC benefit at the current sample sizes. Separate models are justified for interpretation and best in-domain accuracy, while the unified model remains useful as the compact deployment baseline.

Relevant artifacts: `phase4/phase_target_comparison.csv`, `phase5/unified_vs_phase_specific_metrics.csv`, phase-specific importance tables, `thesis_outputs/figures/fcc_bcc_final_comparison.png`, and `thesis_outputs/figures/phase5/unified_vs_phase_specific.png`.
