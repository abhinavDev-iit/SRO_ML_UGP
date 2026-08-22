# Phase 3 data-quality report

Validation date: 2026-08-22. This report covers the leakage-controlled FCC/BCC database produced by `python run_pipeline.py build-phase3`. It does not describe a trained model.

## Acceptance result

The processed FCC/BCC database is ready for EDA and correlation analysis. The join retains all 83,797 validated initial structures: 40,425 FCC and 43,372 BCC. No HCP observation has been admitted to the validated ML table. The primary target is `target_mean_abs_sro_shell1`, copied from source column `mean abs SRO1` and scientifically interpreted as the mean absolute first-shell Warren–Cowley alpha over the unique unlike-element pairs present in a structure.

## Processed tables

| Local table | Rows | Columns | Purpose |
|---|---:|---:|---|
| `data/processed/structures.parquet` | 83,797 | 12 | provenance, composition, phase and initial-cell identity |
| `data/processed/sro_long.parquet` | 335,188 | 14 | one row per structure and shell, retaining all ten aggregate statistics for shells 1–4 |
| `data/processed/features.parquet` | 83,797 | 349 | `fid` plus 348 leakage-controlled candidate predictors |
| `data/processed/ml_dataset.parquet` | 83,797 | 361 | validated structures, candidate predictors and the primary target |
| `data/processed/hcp_candidates_provisional.parquet` | 255 | 21 | explicitly non-validated HCP audit table; excluded from primary ML |

All processed Parquet files use Zstandard compression and remain local under `.gitignore`. File-level QA found one row group per table, readable schemas, exact expected row counts, unique `fid` keys in the structure/feature/ML tables and four SRO rows per `fid` in the long table.

## Join and target integrity

- The 83,797 initial-feature IDs and 83,797 SRO IDs match as sets and are individually unique.
- No record is dropped by the one-to-one join.
- Phase normalization yields only FCC and BCC.
- The primary target has zero missing values.
- The long table explicitly says `pair_resolution=aggregate_over_unique_unlike_pairs`; it must not be treated as pair-resolved data.
- Temperature is genuinely absent for the 84k source and is stored as null metadata, not fabricated.

## Candidate feature library

There are 348 numeric candidate predictors. Every feature has exactly one row in `reports/tables/feature_provenance.csv` and one of four origins:

| Origin | Feature count | Meaning |
|---|---:|---|
| elemental-reference-derived | 163 | supplied Magpie elemental summaries plus new weighted property/pair features reconstructed from the source convention |
| structure-derived | 126 | descriptors calculated from the initial, pre-relaxation structure only |
| composition-derived | 55 | fractions, entropy, element count, composition norms and pair fractions |
| direct source | 4 | initial cell/source fields and phase indicators |

The library contains composition fractions for Al, Co, Cr, Cu, Fe, Mn, Ni and Si; number of elements; ideal configurational entropy; atomic-number, atomic-mass, covalent-radius, electronegativity, VEC and melting-point statistics; composition-weighted absolute/RMS pair differences; 36 unordered pair-fraction descriptors; covalent-radius-based atomic-size mismatch; supplied elemental summaries; and supplied initial structural descriptors.

The source does not provide a defensible metallic-radius convention. Covalent radius is therefore named explicitly and is not relabelled as metallic radius. No external enrichment was needed in this stage. Supplied final energy/enthalpy-like fields are post-DFT outcomes, so no thermodynamic outcome is included by default.

## Elemental-reference reconstruction QA

The eight elemental values for six properties were recovered by overdetermined least squares from formula fractions and the source's own `MagpieData mean ...` columns. Maximum absolute reconstruction errors across all 83,797 rows range from `1.4e-13` to `1.84e-10`, confirming exact recovery to CSV precision. This preserves the source's elemental-reference convention while enabling transparent pair descriptors.

## Missingness and coverage

All 348 predictor columns are complete: overall feature missingness is 0%, and each major engineered feature has 0% missingness. The absent 84k temperature is metadata and not counted as a candidate feature. Coverage includes 246 alloy systems and eight elements. Chemical systems and repeated ordered/SQS realizations are not statistically independent; future splitting must group by chemical system, composition and related configuration family.

## Leakage controls

The default candidate matrix excludes final energy and relaxed-state fields (`Ef_per_atom`, `e_above_hull`, `e_per_atom`, `magmom`, `max_FORCE`, `pressure`, `volume_per_atom`, final `space_group_number`, final/raw structure objects) and the three supplied `mean ordering parameter shell n` target-family proxies. Initial local-environment descriptors remain available because the requested scenario permits pre-relaxation structure information, but composition-only and structure-aware analyses must be compared separately because occupation-derived descriptors can make SRO prediction partly tautological.

## HCP decision

MLP-cSRO TS-5 minus TS-4 supplies 255 equiatomic 144-atom HCP candidates documented at 500 K. A periodic 12-neighbour reconstruction was attempted and retained only as provisional audit data. Ninety-eight configurations have a minimum 13th/12th distance ratio below 1.02; the minimum is effectively 1.000001. Since the authors' six-component HCP WC arrays/topology reference remain unavailable, distance ranking is not a sufficient validation standard and zero HCP rows are admitted.

The current upstream repository was checked on 2026-08-22. Its compact 5.68 MB `DFTMC_structures.tar.gz` was inspected without bulk extraction; it contains five 108-atom, cubic FCC CrCoNi DFT-MC trajectories and no WC arrays, so it is not an HCP replacement. The next credible compact HCP addition remains a completed HfTiZr bundle with explicit HCP structures, temperature/run metadata and pair-resolved WC values.

## EDA readiness and restrictions

The database is ready for distributions, phase-stratified EDA, missingness checks, redundancy analysis and grouped correlation analysis. It is not yet approved for final model training. Before training, feature redundancy, structure-derived target proximity, group-aware splitting, shell/target choice and cross-source comparability must be resolved.
