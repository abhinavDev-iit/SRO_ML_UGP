# Data dictionary - current standardized 84k stage

This dictionary covers fields created or explicitly governed by the current ingestion stage. The complete 292-column raw manifest is in `reports/data_inventory_metrics.json`.

| Column/group | Definition | Units | Origin | Missing meaning | ML safety |
|---|---|---|---|---|---|
| `fid` / `source_structure_id` | immutable source-native structure identifier | none | directly reported | invalid record | grouping key, not predictor |
| `source_id` | `hea_84k_dft_2023` | none | provenance registry | invalid record | grouping only |
| `chemical_system` | alphabetized element set supplied by source | none | directly reported | unknown chemistry | categorical/compositional use |
| `formula` | integer-count formula for the initial cell | none | directly reported | invalid composition | parse, do not use raw as numeric |
| `composition_fractions_json` | normalized element-to-atomic-fraction mapping derived from `formula` | fraction | mathematically derived | parse failure is fatal | safe pre-relaxation |
| `phase` | normalized FCC/BCC label from source `lattice` | none | source metadata | `UNKNOWN` | safe pre-relaxation |
| `NIONS` / `number_of_atoms` | atoms in periodic cell | count | directly reported | invalid structure | safe but may encode ordered/SQS regime |
| `nelements` | number of constituent elements | count | directly reported | invalid composition | safe pre-relaxation |
| `space_group_number_ini` | initial unrelaxed space-group number | none | directly reported/initial structure analysis | unresolved symmetry | pre-relaxation; assess redundancy |
| initial local/Matminer descriptors | descriptors calculated from `structure_ini` | descriptor-specific | calculated from initial structure | source calculation failure | provisionally allowed; arrangement-sensitive ablation required |
| `mean abs SRO1` | mean of absolute WC alpha over unique unlike pairs in first neighbour shell | dimensionless | calculated from initial structure | not missing in current source | recommended aggregate target; never predictor |
| `mean abs SRO2`–`4` | analogous mean magnitude for shells 2–4 | dimensionless | calculated from initial structure | not missing | secondary targets |
| `mean/max/min/std/range SROn` | signed WC-alpha statistics across unlike pairs | dimensionless | calculated from initial structure | not missing | target/analysis only |
| `mean/max/min/std/range abs SROn` | magnitude statistics across unlike-pair alpha | dimensionless | calculated from initial structure | not missing | target/analysis only |
| `mean ordering parameter shell 1`–`3` | Matminer ChemicalOrdering structure features; distinct from SRO CSV labels | dimensionless | calculated from initial structure | not missing | excluded by default as direct target-family leakage |
| `Ef_per_atom`, `e_above_hull`, `e_per_atom` | final relaxed DFT energy outcomes | eV/atom | directly reported after DFT | unavailable outcome | excluded from pre-relaxation ML |
| `volume_per_atom` | final relaxed atomic volume | A^3/atom | final relaxed structure | unavailable outcome | excluded from pre-relaxation ML |
| `space_group_number` | final relaxed symmetry | none | final relaxed structure | unresolved final symmetry | excluded from pre-relaxation ML |
| `magmom`, `max_FORCE`, `pressure` | final calculation outputs/diagnostics | source-specific | DFT output | unavailable outcome | excluded from pre-relaxation ML |

## Phase 3 processed database

| Table/field group | Definition | Units | Origin | Missingness | ML role |
|---|---|---|---|---|---|
| `structures.parquet` | one validated FCC/BCC initial structure per `fid` | mixed | direct source + normalized metadata | 0 rows missing; `temperature_K` intentionally null | identifiers/grouping, selected metadata |
| `sro_long.parquet` | one row per `fid` and shell 1–4 with ten aggregate WC statistics | dimensionless | direct source label table | 0% | targets/EDA only |
| `features.parquet` | `fid` plus 348 numeric candidate features | feature-specific | see `reports/tables/feature_provenance.csv` | 0% | candidate predictors; no final selection yet |
| `ml_dataset.parquet` | structures + features + primary target | mixed | validated one-to-one join | 0% predictors/target | EDA/correlation-ready, not final-training-approved |
| `target_mean_abs_sro_shell1` | source `mean abs SRO1` | dimensionless | calculated source label | 0% | recommended scalar target |
| `composition_fraction_<E>` | atomic fraction of element E | fraction | composition-derived from formula | 0% | safe baseline |
| `configurational_entropy_kb_per_atom` | `-sum(c_i ln c_i)` | kB/atom | composition-derived | 0% | safe baseline |
| `configurational_entropy_j_mol_k` | ideal configurational entropy | J mol-1 K-1 | composition-derived | 0% | safe baseline |
| `pair_fraction_<A>_<B>` | unordered random-pair probability (`c_A^2` or `2c_Ac_B`) | fraction | composition-derived | 0% | pair-composition descriptor |
| `derived_<property>_mean/std` | composition-weighted elemental statistic | property-specific | elemental-reference-derived from reconstructed source Magpie convention | 0% | safe composition baseline |
| `pair_<property>_mean_abs_diff/rms_diff` | normalized composition-weighted unlike-pair property difference | property-specific | elemental-reference-derived | 0% | pair descriptor |
| `atomic_size_mismatch_percent` | `100 sqrt(sum c_i(1-r_i/rbar)^2)` using source-convention covalent radius | % | elemental-reference-derived | 0% | size-mismatch descriptor; not metallic radius |
| `phase_FCC`, `phase_BCC` | one-hot initial phase indicators | binary | direct source | 0% | phase-aware analysis |
| HCP provisional WC fields | six unique Cr/Co/Ni pair WC values reconstructed from 12 nearest neighbours | dimensionless | structure-derived, unvalidated | 0% within candidate table | excluded from primary ML |

Feature origins are controlled vocabulary values: `direct source`, `composition-derived`, `elemental-reference-derived`, `structure-derived`, and `externally enriched`. Phase 3 uses the first four; no externally enriched predictor is present.

## Phase 4 analysis artifacts

| Table/field | Definition | Units | Interpretation |
|---|---|---|---|
| `feature_group_mapping.csv` | one row per candidate predictor with physical group, origin, availability class, metadata and proxy-risk flags | none | governs scientific interpretation and cross-source portability |
| `feature_target_associations.csv` | aggregate/FCC/BCC Pearson, Spearman and 5-neighbour mutual-information statistics | mixed | screening only; absolute MI values are estimator-dependent |
| `feature_quality.csv` | cohort-specific missingness, range, variance, unique values and dominant-value fraction | mixed | identifies constants and near-zero-variance predictors |
| `highly_correlated_feature_pairs.csv` | all aggregate predictor pairs satisfying `abs(Pearson r) >= 0.95` | dimensionless | redundancy audit; not a causal relation |
| `preliminary_feature_sets.csv` | membership and rationale for `FULL_CLEAN`, `BALANCED_PRELIMINARY`, and `MINIMAL_PRELIMINARY` | none | preliminary only; must be evaluated inside group-aware Phase 5 validation |
| `target_statistics.csv` | range, moments, percentiles, Tukey outliers and near-zero fractions for all/FCC/BCC | target units | target is dimensionless aggregate first-shell ordering magnitude |

Phase 4 excludes the 24 aggregate-constant predictors from `FULL_CLEAN`; it does not treat the 255 HCP candidate configurations as labelled observations. The 19-feature portable set uses `phase_FCC` for the current two-phase database. If HCP is validated later, phase encoding must become an explicit three-level training-time transformation.

## Phase 5 model-result fields

| Field/group | Definition | Units | Interpretation |
|---|---|---|---|
| `split_strategy` | `random_configuration`, `composition_grouped`, or `alloy_system_grouped` | none | alloy-system grouping is the primary scientific evaluation |
| `cv_*_mean/std` | three-fold inner validation statistic within the outer training set | metric-specific | used for model/feature-set selection; never outer-test metrics |
| `test_mae`, `test_rmse`, `test_r2` | performance on the frozen outer holdout | target units or dimensionless | primary reported generalization result |
| `test_normalized_mae/rmse` | error divided by held-out target standard deviation | dimensionless | supports FCC/BCC comparison despite different target spreads |
| `train_*` | fitted-training performance | metric-specific | compared with CV/test results to diagnose overfitting |
| `permutation_mae_increase` | increase in held-out MAE after deterministic feature permutation | target units | model dependence, not causal importance |
| `prediction`, `residual` | fitted prediction and `observed - prediction` | dimensionless SRO magnitude | outer-test diagnostics only |

Every fitted pipeline begins with training-fold `VarianceThreshold(0)`. Linear, Ridge, Elastic Net, and SVR pipelines fit `StandardScaler` only inside training data. Model binaries remain under ignored `models/phase5/`; tracked `model_metadata_*.json` files contain features, hyperparameters, date and primary metrics.
