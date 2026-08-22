# Final feature-set refinement

## Protocol

The fixed seed-42 alloy-system split was retained as the untouched outer evaluation. Compact-set ranking and size selection used only its 71,117 training rows. For each of three shuffled GroupKFold folds, a second alloy-system split inside the fold-training partition supplied permutation importance. Candidate sizes 10, 20, 30, 50, 75, 100, 150 and 198 were then evaluated on that fold's validation systems. Outer predictions were generated once after selecting the size.

The 198-feature grouped-CV baseline was R² 0.8803. The acceptance rule was the stricter applicable value of 95% of baseline or an absolute loss of 0.03; here the threshold was 0.8503. Ten features were the smallest tested set meeting it (mean grouped-CV R² 0.8636, SD 0.0290). On the untouched outer set, the unified ten-feature model achieved R² 0.8917, MAE 0.0537 and RMSE 0.0794, compared with 0.8997/0.0535/0.0764 for BALANCED.

## Final hierarchy

- **FULL:** 324 leakage-clean, nonconstant predictors retained after Phase 4 quality filtering.
- **BALANCED:** 198 predictors after redundancy control; the best Phase 5 set.
- **COMPACT_HIGH_PERFORMANCE:** ten training-ranked predictors: `space_group_number_ini`, `configurational_entropy_j_mol_k`, `max packing efficiency`, `NIONS`, `range neighbor distance variation`, `configurational_entropy_normalized`, `minimum local difference in NsUnfilled`, `mean local difference in SpaceGroupNumber`, `mean local difference in NsValence`, and `avg_dev local difference in NsValence`.
- **MINIMAL_COMMON:** 18 phase-independent composition/elemental predictors inherited from the cross-source preliminary set. This is a portability baseline, not the best predictive model.

The compact outer R² values were 0.9038 FCC and 0.9061 BCC. Nine of ten compact predictors are source/configuration-sensitive or structure-derived; this set should not be mistaken for a universally available database schema. Exact ordered names are in `results/feature_sets/`.
