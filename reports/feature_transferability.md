# Feature transferability

The best predictors *within the present 84k theoretical dataset* are not necessarily features suitable for a future cross-source SRO database.

## Transferability classes

- **A — universally derivable:** composition fractions, component count, configurational entropy, phase label, and statistics/differences derived from a declared elemental reference table. These can be recomputed across sources when composition and reference conventions are preserved.
- **B — structure derivable:** initial-cell geometry or topology available from a standardized structure. Such features are portable only when a comparable pre-ordering configuration and featurization convention exist.
- **C — source/method specific:** supplied computational fields or descriptors tied to one workflow and not reliably reconstructable elsewhere.
- **D — potential configuration encoding:** initial space group, local-difference fingerprints, neighbour-distance variation, packing efficiency, cell-size and related descriptors that can encode occupation/configuration construction. These may contain real structural information while also identifying SQS/ordered-cell regimes.

The full row-level classification, origin, availability class and leakage flags are recorded in `results/tables/phase6/feature_transferability_mapping.csv`.

## Interpretation

`space_group_number_ini`, configurational entropy, atom count, packing efficiency and local-difference descriptors dominate held-out permutation importance. Only configurational entropy is unambiguously universally derivable. The large performance increase from composition-only grouped-CV R² 0.0262 to composition-plus-initial-structure R² 0.8783 shows that this study primarily predicts configuration-sensitive SRO within the 84k construction domain.

For future cross-source records, class A should be mandatory; class B should be calculated with versioned code where structures are available; class C should be optional enrichment; class D should be retained with an explicit warning and tested by source/configuration ablation. Cross-source claims must be based on the intersection of reproducible descriptors, not on the current highest-ranked 84k features.
