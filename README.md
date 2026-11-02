# Chemical Short-Range Order in Metallic Alloys

Local, reproducible research-software project for constructing a provenance-preserving SRO database and predicting chemical short-range-order magnitude from leakage-controlled alloy descriptors.

## Current status

The project has completed database construction, EDA, leakage-controlled regression, robustness/refinement, scientific interpretation and the final reproducibility audit.

- Seven local source families and 46,123 raw files have been inventoried.
- The 84k DFT source provides 83,797 initial FCC/BCC configurations with aggregate shell-resolved SRO labels.
- The exact 84k label convention has been independently reproduced and documented in `reports/sro_definition_84k.md`.
- The local processed database contains 83,797 validated rows (40,425 FCC; 43,372 BCC) and 348 candidate predictors with complete provenance and no missing feature values.
- Four Zstandard-compressed Parquet tables are reproducibly generated under ignored `data/processed/`.
- HCP remains a critical gap: 255 candidate HCP CrCoNi CFG configurations were audited at the documented 500 K, but zero WC labels pass reference validation.
- Phase 4 analyzes exactly the 83,797 validated FCC/BCC rows; all 255 provisional HCP configurations remain excluded.
- Pearson, Spearman and mutual-information screens were calculated for the aggregate, FCC-only and BCC-only cohorts. The 348-feature library contains 24 constants, 29 near-zero-variance features, and 426 feature pairs with aggregate |Pearson r| >= 0.95.
- The final hierarchy contains 324 FULL, 198 BALANCED, 10 COMPACT_HIGH_PERFORMANCE and 18 phase-independent MINIMAL_COMMON predictors.
- Phase 4 contributes eighteen 300 dpi EDA/correlation figures; the final supervisor report incorporates these together with the Phase 5-6 model, robustness, interpretation and error-analysis figures.
- The primary ML evaluation holds out 50 entire alloy systems (12,680 rows) and uses grouped inner CV for model/feature-set selection.
- CV-selected HistGradientBoosting models with 198 BALANCED predictors achieve alloy-held-out R²/MAE/RMSE of 0.8997/0.0535/0.0764 unified, 0.9058/0.0348/0.0534 FCC, and 0.9154/0.0563/0.0808 BCC.
- Across five deterministic alloy-system allocations, mean R² is 0.8946±0.0187 unified, 0.9046±0.0128 FCC and 0.9042±0.0287 BCC.
- Training-only nested refinement selects ten predictors. Its untouched unified outer R² is 0.8917, an absolute loss of 0.0081 relative to BALANCED.
- Composition-only grouped-CV R² is only 0.0262 unified; leakage-safe initial structural descriptors raise it to 0.8783. This is strong configuration-level prediction, not evidence of composition-only transferability.
- Symmetry, initial structural geometry, configurational entropy and electronic/VEC/periodic descriptors give the largest conditional group-ablation losses. Initial space group is highly predictive but may encode configuration-generation signatures.
- FCC mean SRO magnitude is 0.2640 versus 0.4002 for BCC (d=0.5253). This dataset contrast is not attributed causally to phase because chemistry and configuration distributions differ.
- Best model binaries are stored only under ignored `models/`; compact metadata, predictions, metrics, tables, reports and 300 dpi thesis figures are version-controlled.
- Phase 7 completed four spin-polarized Quantum ESPRESSO 7.6 static SCFs for exact two-atom Co–Cr low/high-SRO pairs at 55/440 Ry. Within the selected FCC pair, the higher-SRO configuration is lower by 106.9544 meV/atom; within the selected BCC pair, the lower-SRO configuration is lower by 143.3761 meV/atom. These opposite pair-specific trends are a focused fixed-composition comparison, not a universal causal SRO–energy law; see `reports/dft_summary.md`.

## Scientific objective and scope

The primary task is to predict the magnitude of first-neighbour chemical ordering in theoretical multicomponent alloys while separating composition-derived information from initial-configuration information. The validated chemical domain is Al–Co–Cr–Cu–Fe–Mn–Ni in FCC and BCC structures. No validated HCP response is included, and no result should be generalized to arbitrary metallic alloys or experimental sources without new validation.

## Data provenance and leakage controls

The 84k DFT source is documented in `SOURCES.md`, `sources.yaml` and `reports/sro_definition_84k.md`. Every predictor records its direct, composition-derived, elemental-reference-derived, structure-derived or enriched origin. Default models exclude final energy, final/relaxed volume, final symmetry, relaxed structures, forces/pressure/magnetization outputs and direct ordering proxies. Initial geometry is allowed but explicitly ablated because it can encode the configuration used to calculate SRO.

## Data policy

`data/raw/` is immutable and excluded from Git. Processed datasets and trained models also remain local by default. Provenance, reports, code, tests and compact result summaries are version-controlled.

## 84k target

The primary target is `target_mean_abs_sro_shell1`, sourced from `mean abs SRO1`: the mean absolute first-neighbour Warren–Cowley coefficient across all unique unlike-element pairs in a structure. It measures aggregate ordering magnitude; it is neither a signed nor pair-specific alpha. See `reports/sro_definition_84k.md` for the equation, all 40 column definitions, shell conventions and limitations.

## Validation and interpretation

The primary evaluation holds out complete alloy systems; grouped inner CV selects the model/feature configuration. Easier random/configuration and composition-held-out splits are sensitivity baselines. Final compact feature count is chosen using training-fold-only permutation rankings and grouped validation, followed by one untouched outer evaluation. Interpretation combines held-out permutation importance, physical-group ablation, targeted descriptor removal and a small partial-dependence set. These quantify association and predictive contribution, not causality.

## Deliverables

The comprehensive supervisor-review report is available in editable and fixed-layout forms:

- `deliverables/SRO_ML_Project_Progress_Report.docx`: editable A4 Word report with a live table of contents, 27 numbered sections, 45 figures, 49 authored data tables and eight appendices.
- `deliverables/SRO_ML_Project_Progress_Report.pdf`: field-refreshed 47-page PDF used for final visual inspection.
- `deliverables/report_evidence_map.md`: claim-to-source map for major numerical and scientific statements.
- `deliverables/report_figure_inventory.csv`: inclusion, resolution and caption audit for every report figure.
- `deliverables/report_manifest.json`: machine-readable build and validation summary.

The report is a supervisor-review document, not a submitted thesis. Literature-dependent physical claims are explicitly separated from repository-verified project evidence.

## Reproduction

Create an environment and install dependencies from `requirements.txt`, then run:

```text
python -m unittest discover -s tests -v
python scripts/profile_raw_inventory.py
python scripts/profile_mlp_csro_cfg.py
python run_pipeline.py ingest-84k --dry-run
python run_pipeline.py build-phase3
python run_pipeline.py analyze-phase4
python run_pipeline.py train-phase5
python run_pipeline.py interpret-phase6
python run_pipeline.py dft-select
python run_pipeline.py dft-prepare
# With QE 7.6 and the ignored local Co/Cr UPFs configured, run manually in WSL:
wsl bash -lc "bash /mnt/d/SRO_ML_UGP/dft_runs/run_final_scfs.sh"
# After all four outputs contain JOB DONE:
python run_pipeline.py dft-analyze
python src/reporting/build_supervisor_report.py
powershell -ExecutionPolicy Bypass -File src/reporting/export_report_pdf.ps1
python src/reporting/audit_supervisor_report.py
```

`train-phase5` is the expensive model-comparison stage; `interpret-phase6` reuses its fixed best specification for five grouped allocations and focused ablations. Deterministic seeds and relative output paths are encoded in the modules. Run commands from the repository root. Raw data and locally generated Parquet/model files are intentionally ignored.

The legacy standardized ignored local CSV view can still be generated with:

```text
python run_pipeline.py ingest-84k
```

## Project map

- `SOURCES.md`, `sources.yaml`: human- and machine-readable source registry
- `reports/`: inventory, scientific definitions, HCP status and project decisions
- `logs/pipeline_log.md`: dated audit trail
- `src/cleaning/`: composition, phase and pair standardization
- `src/ingestion/`: source-specific ingestion adapters
- `src/features/`: composition, elemental-property and pair feature engineering
- `src/pipeline/`: validated Phase 3 Parquet/QA/figure construction
- `src/analysis/`: reproducible Phase 4 EDA, association, redundancy and preliminary-set logic
- `src/ml/`: Phase 5 grouped splits, sklearn pipelines, model/ablation comparison, importance, residual and alloy-system analysis
- `src/analysis/phase6.py`: repeated grouped robustness, training-only compact refinement, physical-group/configuration sensitivity, error and extrapolation audits
- `src/reporting/`: reproducible supervisor-report construction, Word-to-PDF export and structural/numerical auditing
- `src/dft/`: four-structure Phase 7 selection, exact-source extraction, QE input preparation, execution guard and result parsing
- `dft_structures/`, `dft_inputs/`: compact exact initial structures and tracked non-runnable QE templates/configuration
- `deliverables/`: editable/fixed-layout supervisor report and its evidence, figure and build manifests
- `tests/`: scientifically important validation tests
- `results/feature_sets/`: exact final feature hierarchy
- `thesis_outputs/`: selected 300 dpi figures, compact tables, manifests and results/discussion material
- `run_pipeline.py`: modular command-line entry point

## Scientific safeguards

Raw provenance is retained; physically different SRO metrics are not merged; initial and relaxed features are separated; final DFT energy, volume and symmetry are excluded from default 84k predictors; direct ordering proxies are also excluded. Future validation must group related structures, compositions, trajectories and sources to prevent pseudo-replication.

See `reports/final_feature_set.md`, `reports/feature_transferability.md`, `reports/configuration_descriptor_sensitivity.md`, `reports/study_limitations.md` and the thesis manifests for final interpretation. The 255 provisional CrCoNi HCP configurations remain excluded because author WC reference arrays and exact topology mapping are missing; the current validated HCP count is zero. Conclusions apply only to validated FCC/BCC observations.
