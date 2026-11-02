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

## 2026-08-22 — Phase 5: leakage-controlled grouped machine learning

- **Input:** ignored validated `ml_dataset.parquet`; Phase 4 feature mapping and preliminary sets; target `target_mean_abs_sro_shell1`
- **Population:** 83,797 rows (FCC 40,425; BCC 43,372); HCP 0; all 255 provisional HCP configurations excluded
- **Primary split:** 196 training and 50 held-out alloy systems; 71,117/12,680 rows; zero group overlap; fixed seed 42; three-fold shuffled alloy-system GroupKFold inside training
- **Models:** dummy median, linear, Ridge, Elastic Net, Random Forest, Extra Trees, Gradient Boosting, HistGradientBoosting, and 10,000-row SVR baseline. XGBoost/LightGBM/SHAP skipped because not installed.
- **Selection:** model/feature configuration chosen only by inner grouped-CV R²; outer test never used to select. Fitted constant filtering and required scaling live inside sklearn pipelines.
- **Best:** HistGradientBoosting + BALANCED (198 features) for all cohorts; unified test R²/MAE/RMSE 0.8997/0.0535/0.0764; FCC 0.9058/0.0348/0.0534; BCC 0.9154/0.0563/0.0808
- **Split sensitivity:** unified R² 0.9266 random, 0.9161 composition-held-out, 0.8997 alloy-system-held-out; grouped result governs conclusions
- **Ablation:** unified grouped-CV R² 0.0262 composition-only, 0.1764 composition+phase, 0.8783 composition+initial structure, 0.1008 MINIMAL, 0.8803 BALANCED
- **Space group:** removing `space_group_number_ini` lowers held-out R² by 0.0794 unified, 0.0811 FCC, 0.0777 BCC; sensitivity persists within phase but is not causal evidence
- **Importance:** space group, configurational entropy, packing/neighbor geometry, atom count and local-difference descriptors lead held-out permutation importance; interpretation remains preliminary
- **Models:** three compressed joblib pipelines retained locally under ignored `models/phase5/`; compact JSON metadata tracked
- **Outputs:** complete result/prediction/importance/split/alloy CSVs; seven ML reports; 18 Phase 5 300 dpi figures; updated thesis captions, notes and numerical summary
- **Runtime:** approximately 31.9 minutes for the complete local run; no raw ingestion rerun; no model binary committed
- **Training caution:** Phase 4 BALANCED selection was informed by whole-dataset EDA, so Phase 5 is exploratory rather than pristine confirmatory validation

## 2026-08-22 — Phase 6: robustness, refinement and thesis synthesis

- **Input:** validated 83,797-row FCC/BCC ML table; Phase 4 mappings; Phase 5 fixed HistGradientBoosting specification, predictions and ignored local model pipelines
- **Population/target:** FCC 40,425; BCC 43,372; HCP 0; `target_mean_abs_sro_shell1`
- **Robustness:** repeated complete alloy-system holdout for seeds 7/19/42/73/101; mean R² 0.8946±0.0187 unified, 0.9046±0.0128 FCC, 0.9042±0.0287 BCC
- **Compact refinement:** feature rankings calculated inside fold-training partitions; size chosen by three-fold grouped validation only; ten predictors selected at CV R² 0.8636 versus 0.8803 BALANCED; untouched unified outer R² 0.8917
- **Group ablation:** largest ΔCV R² from symmetry −0.0666, structural geometry −0.0246, configurational entropy −0.0220 and electronic/VEC/periodic −0.0126
- **Configuration sensitivity:** removing initial space group lowers outer R² by 0.0830 unified; result persists within FCC/BCC but is treated as predictive/configuration-sensitive, not causal
- **Error/extrapolation:** 95th-percentile absolute-error threshold 0.1682; errors concentrate at high targets and selected held-out systems; no compact feature exceeds literal training min/max, but joint-domain extrapolation remains possible
- **Outputs:** eight Phase 6 300 dpi figures, requested robustness/ablation CSVs, exact four-level feature lists, sensitivity/error/extrapolation tables, final scientific reports, thesis support map, figure/table manifests and results/discussion material
- **HCP:** zero validated observations; 255 provisional CrCoNi configurations excluded; no HCP model trained
- **Validation:** Phase 6 rerun reproduced all numerical results; metrics are independently recomputable from saved predictions; outer-test columns absent from compact-selection table; PNG DPI/schema/leakage/HCP tests added
- **Runtime:** approximately 7.2 minutes for the deterministic Phase 6 analysis on this workstation
- **Local-only files:** raw data, four processed Parquet tables, provisional HCP Parquet and compressed Phase 5 model binaries remain ignored

## 2026-11-02 — Phase 7: four-structure DFT selection and environment gate

- **Input:** validated 83,797-row FCC/BCC table and exact `structure_ini_as_dict` records in the immutable 84k master CSV
- **Selection:** fixed phase/composition/atom-count groups ranked by atom count then SRO range; selected FCC `gra62121526`/`gra62121527` and BCC `gra64001864`/`gra62121595`, all Co0.5Cr0.5 with two atoms
- **Validation:** exact source lattice, species, fractional coordinates and atom ordering extracted; phase, composition and atom count cross-checked; selected pairs span SRO 0.000000–0.333333 FCC and 0.000000–1.000000 BCC
- **Preparation:** static spin-polarized PBE Quantum ESPRESSO templates only; identical Co/Cr magnetic initialization, metallic smearing and reciprocal-spacing policy within all comparisons
- **Environment gate:** no `pw.x`, VASP executable, local UPF file or `ESPRESSO_PSEUDO` path detected; pseudopotential-dependent cutoffs left unresolved rather than fabricated
- **Outputs:** `results/tables/dft/selected_configurations.csv`, four compact JSON structures, four QE templates, `dft_inputs/qe_config.json`, `reports/dft_summary.md`, CLI commands and unit/artifact tests
- **Not produced:** no cutoff test, SCF execution, total energy, `dft_results.csv`, DFT figure or scientific SRO–energy conclusion
- **Local policy:** `dft_runs/`, UPFs, wavefunctions, mixing files and QE save directories are ignored

## 2026-11-02 — Phase 7: QE 7.6 cutoff decision and manual production handoff

- **Runtime:** verified `/home/aditya/miniconda3/envs/qe7/bin/pw.x` as Quantum ESPRESSO 7.6 through WSL Conda environment `qe7`; the broken `/usr/bin/pw.x` is explicitly excluded
- **Pseudopotentials:** local Git-ignored SSSP PBE Efficiency v1.3.0 Co/Cr UPFs passed recorded MD5/SHA-256 checks; no pseudopotential binary was staged
- **Cutoff check:** FCC low-SRO `gra62121526` converged formally at 55/440 Ry with total energy `-473.95628523 Ry`; the optional 65/520 Ry point was manually stopped without `JOB DONE` after energy stabilization
- **Near-converged endpoint:** latest completed 65 Ry energy `-473.95654789 Ry`; immediately preceding energy `-473.95654736 Ry` at approximately `7e-8 Ry` estimated SCF error; 65 Ry remains labelled not formally converged
- **Decision:** the latest 65 Ry energy is `1.78684 meV/atom` below the 55 Ry value, so 55/440 Ry was selected for this preliminary fixed-composition comparison
- **Preparation:** regenerated and validated four exact two-atom, one-Co/one-Cr static SCF inputs with fixed 12×12×12 sampling, Marzari–Vanderbilt smearing, spin polarization and identical starting magnetizations
- **Manual runner:** added `dft_runs/run_final_scfs.sh`; it runs sequentially in `qe7`, preserves incomplete prior outputs, reports `SUCCESS` only for `JOB DONE`, continues after failure and does not delete outputs
- **Validation:** eight Phase 7 unit/artifact tests pass; runner passes WSL `bash -n`; executable resolves to the `qe7` path; all QE runtime/scratch directories remain ignored
- **Deferred:** Codex did not execute the four production SCFs; result parsing, DFT plots and scientific FCC/BCC energy conclusions await the user's manual run

## 2026-11-03 — Phase 7: final four-configuration static-DFT analysis

- **Output gate:** all four production files contain formal SCF convergence, a finite final total energy and `JOB DONE`; no NaN, QE error, MPI abort or failure marker was found
- **FCC result:** `gra62121527` (SRO 0.333333) is lower than `gra62121526` (SRO 0.000000) by `106.954422 meV/atom`
- **BCC result:** `gra64001864` (SRO 0.000000) is lower than `gra62121595` (SRO 1.000000) by `143.376114 meV/atom`
- **Magnetization:** FCC low-SRO total/absolute magnetization `0.22/0.39 μB/cell`; the other three final total/absolute values print as zero within QE output precision
- **Cutoff provenance:** the production decision used the manually stopped near-converged 65 Ry checkpoint (`1.78684 meV/atom` from 55 Ry); the already-running background process later reached formal convergence and a final `1.77214 meV/atom` difference without a restart; 55/440 Ry remains selected
- **Outputs:** `results/tables/dft/dft_results.csv`, `figures/dft/dft_relative_energy.png`, `figures/dft/sro_vs_relative_energy.png`, and updated `reports/dft_summary.md`
- **Interpretation:** FCC and BCC show opposite selected-pair trends; four configurations demonstrate configuration-sensitive static energies but cannot establish a universal causal SRO–energy relationship
- **Validation:** pairwise relative energies independently recomputed from Ry/atom values using `13.605693122994 eV/Ry`; both PNGs visually inspected and verified at 300 dpi; ten Phase 7 unit/artifact tests pass
- **Local-only files:** QE outputs, scratch/save data and pseudopotential binaries remain ignored and unstaged
