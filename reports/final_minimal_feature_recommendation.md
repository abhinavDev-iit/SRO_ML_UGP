# Final minimal feature recommendations

## 1. MINIMAL_COMMON_DATASET_FEATURES

Every future SRO record should store, without fabricating missing values:

- stable record/configuration identifier;
- source type, citation/URL/version, source record identifier, provenance and calculation/measurement method;
- alloy system, canonical composition and per-element fractions;
- phase and phase-validation method;
- temperature and pressure only when genuinely reported;
- SRO metric name and convention, signed/magnitude status, value, uncertainty if supplied, element pair, neighbour shell, coordination/topology definition and aggregation rule;
- configuration/trajectory/family grouping identifiers needed to represent dependence;
- atom count and structure availability;
- number of elements, configurational entropy, and versioned elemental-reference statistics for atomic number/mass/radius, size mismatch, electronegativity, VEC and melting point.

This is a database-design recommendation. Missing temperature or pair resolution must remain explicitly null, not inferred.

## 2. COMPACT_ML_FEATURES

Within the present 84k source, the smallest tested strong predictor set contains ten features listed in `results/feature_sets/compact_high_performance.txt`. It achieves unified alloy-held-out R² 0.8917 versus 0.8997 for 198 BALANCED features. The set contains space group, entropy, packing, atom count, neighbour variation and four local electronic/symmetry-difference descriptors.

This is a predictive recommendation for the current theoretical domain, not the cross-source schema. Most compact ML predictors require the initial configuration or encode how it was constructed. For cross-source modeling, first benchmark the 18-feature phase-independent `minimal_common.txt` portability baseline, then add consistently recomputed structure features under explicit source-held-out validation.
