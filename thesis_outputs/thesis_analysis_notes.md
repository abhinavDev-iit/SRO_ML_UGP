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

## Phase 5 safeguards

Use composition- or alloy-system-grouped outer validation, report FCC and BCC errors separately, and compare the three frozen preliminary sets. Run explicit composition-only versus initial-structure-feature ablations. Fit preprocessing and any revised redundancy filtering inside training folds. Retain an untouched grouped test cohort and do not use HCP until WC validation succeeds.
