# Phase 4 feature redundancy audit

The full numerical library contains 348 predictors, of which 24 are constant and 29 meet the conservative near-zero-variance rule in the aggregate cohort. The all-data Pearson matrix contains **426 pairs with |r| ≥ 0.95**. There are **9 exact duplicate-column groups**.

High correlation is expected among alternate summaries of the same elemental property (minimum/maximum/range/mean/mode), between reconstructed descriptors and their supplied Magpie counterparts, among pair-fraction constraints, and between complementary phase indicators. `highly_correlated_feature_pairs.csv` preserves all pairs. The displayed heatmap is restricted to the portable preliminary set so it remains readable.

Known deterministic relationships include `configurational_entropy_j_mol_k = R * configurational_entropy_kb_per_atom`, `phase_FCC + phase_BCC = 1` in the two-phase cohort, `0-norm = nelements = composition_number_of_elements`, and a unit-sum constraint across all composition fractions (and separately across random-pair fractions). These relationships motivate pruning but do not invalidate the underlying physical quantities.

Redundancy is not evidence that a descriptor is physically invalid. For the balanced preliminary set, one representative per |r| ≥ 0.95 neighborhood is retained using a deterministic priority combining portability and aggregate Spearman/MI screening. This rule is preliminary and must be frozen inside training folds if altered in Phase 5.

Exact duplicate groups:

- `0-norm`, `composition_number_of_elements`, `nelements`
- `MagpieData avg_dev NfUnfilled`, `MagpieData avg_dev NfValence`, `MagpieData maximum NfUnfilled`, `MagpieData maximum NfValence`, `MagpieData mean NfUnfilled`, `MagpieData mean NfValence`, `MagpieData minimum GSbandgap`, `MagpieData minimum NfUnfilled`, `MagpieData minimum NfValence`, `MagpieData mode NfUnfilled`, `MagpieData mode NfValence`, `MagpieData range NfUnfilled`, `MagpieData range NfValence`, `avg_dev local difference in NfUnfilled`, `avg_dev local difference in NfValence`, `frac f valence electrons`, `maximum local difference in NfUnfilled`, `maximum local difference in NfValence`, `mean local difference in NfUnfilled`, `mean local difference in NfValence`, `minimum local difference in NfUnfilled`, `minimum local difference in NfValence`, `range local difference in NfUnfilled`, `range local difference in NfValence`
- `MagpieData maximum GSbandgap`, `MagpieData range GSbandgap`
- `MagpieData range NsUnfilled`, `MagpieData range NsValence`
- `avg_dev local difference in NsUnfilled`, `avg_dev local difference in NsValence`
- `maximum local difference in NsUnfilled`, `maximum local difference in NsValence`
- `mean local difference in NsUnfilled`, `mean local difference in NsValence`
- `minimum local difference in NsUnfilled`, `minimum local difference in NsValence`
- `range local difference in NsUnfilled`, `range local difference in NsValence`
