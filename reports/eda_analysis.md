# Phase 4 exploratory data analysis

## Analysis population

Phase 4 contains exactly **83,797** validated observations: **40,425 FCC** and **43,372 BCC**. The **255 provisional HCP configurations are excluded** because validated reference Warren–Cowley arrays remain unavailable. There are 83,797 unique configuration identifiers, 246 chemical systems, 11,354 formula labels, and 9,633 distinct normalized composition vectors.

The target is `target_mean_abs_sro_shell1`: the source-provided mean of the absolute pair-resolved first-shell Warren–Cowley coefficients over the unique unlike pairs. It is an aggregate ordering magnitude, not a signed or pair-specific coefficient.

## Target distribution

Across both phases, the target ranges from **0 to 1.5**, with mean **0.3345**, median **0.2708**, standard deviation **0.2681**, and skewness **1.106**. The 5th/95th percentiles are **0.0000/0.9167**. Tukey's descriptive rule identifies 1,036 upper/lower-tail observations; these are retained because a bounded physical response can have legitimate extreme configurations. 11.29% are at or below 0.05 and 17.40% are at or below 0.10.

The distribution is right-skewed but not so concentrated at zero that a zero-inflated target formulation is indicated. A monotone transform may be tested during Phase 5 as a sensitivity analysis, while predictions and error reporting should remain on the original physically interpretable scale.

## FCC/BCC target comparison

BCC has mean target **0.4002** versus **0.2640** for FCC (difference 0.1362; standardized mean difference 0.525). The two empirical distributions have KS distance 0.233. These are descriptive dataset contrasts, not claims of a causal phase effect, because composition/configuration coverage is not randomized.

## Data quality and duplication

All 348 Phase 3 predictors and the target are complete in the validated FCC/BCC table. There are no duplicate configuration identifiers and no exact duplicate complete feature rows. Exact duplicate *feature columns* are listed in the redundancy report (9 groups); mathematical redundancy is expected for complementary phase indicators and some composition constructions. Near-duplicate observations were not collapsed: repeated formula labels can represent distinct configurations and are scientifically meaningful.

## Interpretation boundary

Correlations and mutual information quantify association, not causal mechanisms. The 83,797 rows are configuration-level observations nested within compositions and alloy systems, so naive random train/test splitting could overstate generalization. Phase 5 should use group-aware splits by composition or alloy system and keep FCC/BCC stratification explicit.

Mutual-information values are used only for ranking. They were estimated with a deterministic, target-quantile-stratified sample of at most 20,000 rows per cohort and five-neighbor regression. Their absolute magnitude is estimator- and sampling-dependent, especially with repeated/discrete composition descriptors, and must not be read as an effect size.
