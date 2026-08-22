# Chemical Short-Range Order in Metallic Alloys

Local, reproducible research-software project for constructing a provenance-preserving theoretical/experimental SRO database and studying physics-informed descriptors across FCC, BCC and HCP solid solutions.

## Current status

The project has completed Phase 3 database construction and extensive leakage-controlled feature engineering. No machine-learning model has been trained.

- Seven local source families and 46,123 raw files have been inventoried.
- The 84k DFT source provides 83,797 initial FCC/BCC configurations with aggregate shell-resolved SRO labels.
- The exact 84k label convention has been independently reproduced and documented in `reports/sro_definition_84k.md`.
- The local processed database contains 83,797 validated rows (40,425 FCC; 43,372 BCC) and 348 candidate predictors with complete provenance and no missing feature values.
- Four Zstandard-compressed Parquet tables are reproducibly generated under ignored `data/processed/`.
- HCP remains a critical gap: 255 candidate HCP CrCoNi CFG configurations were audited at the documented 500 K, but zero WC labels pass reference validation.
- Five 300 dpi thesis figures and compact CSV summaries report phase, alloy-system, element, feature-availability and missingness coverage.

## Data policy

`data/raw/` is immutable and excluded from Git. Processed datasets and trained models also remain local by default. Provenance, reports, code, tests and compact result summaries are version-controlled.

## 84k target

The recommended source-specific scalar target is `mean abs SRO1`: the mean absolute first-neighbour Warren–Cowley coefficient across all unique unlike-element pairs in a structure. It measures aggregate ordering magnitude and is not a pair-specific alpha value. See `reports/sro_definition_84k.md` for the equation, all 40 column definitions, shell conventions and limitations.

## Reproduction

Create an environment and install dependencies from `requirements.txt`, then run:

```text
python -m unittest discover -s tests -v
python scripts/profile_raw_inventory.py
python scripts/profile_mlp_csro_cfg.py
python run_pipeline.py ingest-84k --dry-run
python run_pipeline.py build-phase3
```

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
- `tests/`: scientifically important validation tests
- `run_pipeline.py`: modular command-line entry point

## Scientific safeguards

Raw provenance is retained; physically different SRO metrics are not merged; initial and relaxed features are separated; final DFT energy, volume and symmetry are excluded from default 84k predictors; direct ordering proxies are also excluded. Future validation must group related structures, compositions, trajectories and sources to prevent pseudo-replication.

See `reports/data_quality_report.md` and `reports/tables/feature_provenance.csv` before any EDA or modeling. Initial structure-derived descriptors require an explicit ablation against composition-only features because they can encode the occupations used to calculate SRO.
