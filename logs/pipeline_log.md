# Pipeline log

## 2026-08-22 — Stage 01: raw-data inventory and project planning

- **Input:** complete repository and immutable `data/raw/` tree
- **Operations:** recursive file/type/size inventory; streaming profile of 11 CSV files; ID-set comparison; source documentation/script review; read-only inspection of Rao–Curtin XLSX workbooks; selected relaxed-vs-initial feature comparison; source search for provenance and HCP gaps
- **Outputs:** `reports/data_inventory.md`, `reports/data_inventory_metrics.json`, `reports/normalized_database_schema.md`, `reports/project_plan.md`, `reports/hcp_data_status.md`, `SOURCES.md`, `sources.yaml`
- **Rows before/after:** no data transformation; raw rows unchanged
- **Columns added/removed:** none
- **Assumptions:** none about missing units, phase, SRO convention or temperature; filenames used only as inventory hints unless supported by documentation
- **Warnings:** 84k SRO is aggregate-only; 227 records lack initial structures; relaxed/post-DFT fields can leak; Rao–Curtin semantics incomplete; no validated HCP SRO rows
- **Unresolved:** exact SRO conventions, upstream commits/licenses, Rao–Curtin reduced-parameter mapping, HCP frame counts and validation reference
- **Raw changes:** none

## 2026-08-22 — Stage 02: SRO definition, HCP audit and safe ingestion preparation

- **Input:** 84k publication/Zenodo/official repository and local CSVs; local MLP-cSRO CFG/plotting sources
- **Operations:** reproduced 84k WC alpha summaries directly from binary/ternary initial cells; mapped all 40 SRO columns; counted and hashed CFG blocks across nested training sets; implemented initial-only ingestion policy and unit/integration tests
- **Outputs:** `reports/sro_definition_84k.md`, updated `reports/hcp_data_status.md`, `reports/mlp_csro_cfg_inventory.json`, `reports/ingestion_84k.md`, `src/cleaning/`, `src/ingestion/`, `tests/`, `run_pipeline.py`, `requirements.txt`, `README.md`, `data_dictionary.md`
- **Rows before/after:** 83,797 initial rows and 83,797 SRO rows validate one-to-one; expected usable FCC 40,425 and BCC 43,372; no processed dataset written during this stage
- **Columns:** default initial-only view selects 278 fields; removes final DFT outcome/relaxed fields and three direct ordering proxies
- **Validation:** seven tests passed; independent WC calculations matched supplied binary and ternary SRO summaries for shells 1–4
- **Warnings:** 84k labels are aggregate and temperature-free; exact pair values are absent; 255 HCP CrCoNi CFG blocks lack locally available validated WC labels; arrangement-sensitive features may make prediction tautological
- **Raw changes:** none

## 2026-08-22 — Phase 3: processed database and feature engineering

- **Input:** 83,797 initial/pre-relaxation 84k feature rows, matching aggregate SRO table, local TS-4/TS-5 MLP-cSRO CFGs, and current upstream source metadata
- **Operations:** exact one-to-one FCC/BCC join; shell-long normalization; composition/entropy/pair feature engineering; source-convention elemental-property reconstruction; feature provenance assignment; leakage exclusion; HCP CFG parsing and neighbour-shell audit; Parquet validation; 300 dpi summary figures
- **Outputs:** ignored local `structures.parquet`, `sro_long.parquet`, `features.parquet`, `ml_dataset.parquet`, and provisional HCP audit Parquet; tracked QA report, provenance/reference tables, five figures and five compact CSV summaries
- **Rows before/after:** 83,797 to 83,797 validated ML rows; FCC 40,425; BCC 43,372; validated HCP 0; SRO-long 335,188 rows
- **Features:** 348 numeric candidates; 0% missingness; origins recorded for every feature; no final feature selection performed
- **Validation:** exact IDs/counts; unique keys; readable Parquet metadata; target completeness; source Magpie means reconstructed to maximum absolute error below `2e-10`; 255 HCP candidates all 144-atom/equiatomic; 98 have first-shell gap ratio below 1.02
- **Leakage:** final energies, relaxed volume/symmetry/structures, force/pressure/magnetization outputs and three ordering-parameter proxies excluded
- **HCP:** current 5.68 MB upstream DFT-MC archive inspected; it contains FCC trajectories only. Provisional HCP WC remains excluded pending author reference arrays or a validated topology map.
- **Warnings:** 84k target is shell/pair aggregated and temperature-free; initial arrangement descriptors need composition-only ablation; rows within chemical systems/configuration families are dependent
- **Raw changes:** added ignored 5.68 MB upstream source archive under `data/raw/mlp_csro/upstream_2026-08-22/`; no existing raw file changed
- **Training:** not started

## 2026-08-22 — Phase 4: EDA, association and redundancy analysis

- **Input:** ignored local `ml_dataset.parquet` with 83,797 validated rows and tracked 348-feature provenance table
- **Population:** FCC 40,425; BCC 43,372; HCP 0. All 255 provisional HCP CFG rows excluded by assertion and tests.
- **Operations:** master/FCC/BCC coverage and target characterization; feature taxonomy/portability flags; Pearson and Spearman correlations on every cohort row; deterministic target-quantile-stratified mutual information (maximum 20,000 rows per cohort); exact-duplicate/constant/NZV audit; full aggregate Pearson redundancy matrix; preliminary feature sets; 300 dpi figure generation
- **Target:** `target_mean_abs_sro_shell1`, an aggregate unlike-pair first-shell Warren–Cowley magnitude, never used as a predictor
- **Results:** target mean 0.3345 (FCC 0.2640; BCC 0.4002); 24 constants; 29 NZV features; 426 pairs with |r| >= 0.95; aggregate strongest Pearson/Spearman feature `space_group_number_ini` (r=0.4753, rho=0.5931); strongest MI feature `5-norm` (1.7996, ranking statistic only)
- **Feature sets:** `FULL_CLEAN` 324; `BALANCED_PRELIMINARY` 198; `MINIMAL_PRELIMINARY` 19. No model importance or held-out performance used.
- **Outputs:** five scientific reports, Phase 4 metrics JSON, 14 compact result-table families mirrored into thesis outputs, full correlation CSV, 18 thesis-quality figures, captions/analysis notes/results summary
- **Validation:** exact cohort/key counts, HCP exclusion, leakage/proxy rank checks, complete feature-group coverage, deterministic rerun, CSV artifact inspection, PNG dimension/DPI checks, full unit/integration test suite
- **Warnings:** association is not causation; rows are nested within compositions/systems; MI magnitudes depend on estimator/sample; initial symmetry/geometry can encode configuration regime; Phase 5 requires group-aware validation and structure-feature ablation
- **HCP:** no new data downloaded; validated count remains zero; MLP-cSRO reference arrays or compact HfTiZr WC/configuration bundle still required
- **Training:** not started
