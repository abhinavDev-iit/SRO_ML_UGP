# Phase 4 thesis analysis notes

## Defensible findings

- The validated database is balanced enough for separate FCC/BCC analysis (40,425/43,372 rows), but it contains no validated HCP label.
- The aggregate target is right-skewed (skewness 1.106) and differs descriptively by phase: BCC mean 0.4002 versus FCC 0.2640, Cohen's d 0.525 and KS distance 0.233.
- Initial space-group number has the largest aggregate Pearson and Spearman association (0.4753 and 0.5931). This likely captures initial-structure/configuration regimes and must not be presented as a causal material law.
- Composition complexity/entropy and composition norms rank repeatedly across linear, monotonic and MI screens. Their mathematical redundancy is explicit.
- The library is highly redundant: 24 constants, 29 near-zero-variance features, nine exact duplicate-column groups, and 426 pairs with |r| >= 0.95.
- FCC/BCC rankings are not identical. Phase-specific models or phase interactions should be compared with pooled phase-aware models in Phase 5.

## Interpretation limits

The label aggregates absolute WC coefficients across unlike pairs, so it erases sign and chemical-pair identity. Each row is a configuration, not an independent alloy experiment; formula, composition, system and generation protocol induce dependence. Correlation and MI therefore support screening and hypothesis generation only. [LITERATURE SUPPORT REQUIRED] before connecting individual elemental descriptors to proposed chemical-bonding or electronic mechanisms.

## Phase 5 results

- The primary outer test holds out 50 alloy systems with zero train/test group overlap. Unified HistGradientBoosting/BALANCED gives R² 0.8997, MAE 0.0535 and RMSE 0.0764.
- Phase-specific pipelines improve identical held-out rows: FCC R² 0.8668 unified to 0.9058 phase-specific; BCC 0.9038 to 0.9154.
- Random-split unified R² is 0.9266, composition-held-out 0.9161 and alloy-system-held-out 0.8997. The hardest result governs conclusions.
- Composition-only grouped-CV R² is 0.0262; adding phase gives 0.1764; adding initial structure gives 0.8783. Strong performance is therefore configuration/structure dependent.
- The 19-feature minimal set has grouped-CV R² 0.1008 and does not retain most performance.
- Removing initial space group lowers held-out R² by about 0.08 in unified, FCC and BCC models. Its signal persists within phase but can encode construction/symmetry regime rather than causal control.
- Permutation importance ranks initial space group first, followed by configurational entropy, packing/neighbor geometry and atom-count/local-difference descriptors. Importance is predictive, not causal. [LITERATURE SUPPORT REQUIRED]
- Best pipelines have moderate train–test gaps (unified 0.9336 vs 0.8997; FCC 0.9515 vs 0.9058; BCC 0.9451 vs 0.9154). Minimal-set SVR and Random Forest baselines show much stronger instability.

## Phase 5 safeguards and Phase 6 boundary

Use composition- or alloy-system-grouped outer validation, report FCC and BCC errors separately, and compare the three frozen preliminary sets. Run explicit composition-only versus initial-structure-feature ablations. Fit preprocessing and any revised redundancy filtering inside training folds. Retain an untouched grouped test cohort and do not use HCP until WC validation succeeds.

Phase 5 is exploratory because Phase 4 EDA inspected the full dataset before the outer test was defined. Phase 6 may interpret robust patterns cautiously, but confirmatory performance ultimately requires a newly isolated source or prospectively frozen external test.
