# Chemical Short-Range Order in Metallic Alloys

Local, reproducible research-software project for constructing a provenance-preserving theoretical/experimental SRO database and studying physics-informed descriptors across FCC, BCC and HCP solid solutions.

## Current status

The project has completed raw-data inventory and the first standardized-ingestion implementation. No machine-learning model has been trained.

- Seven local source families and 46,123 raw files have been inventoried.
- The 84k DFT source provides 83,797 initial FCC/BCC configurations with aggregate shell-resolved SRO labels.
- The exact 84k label convention has been independently reproduced and documented in `reports/sro_definition_84k.md`.
- A leakage-aware, chunked 84k ingestion adapter is available.
- HCP remains a critical gap: 255 candidate HCP CrCoNi CFG configurations are local, but validated pair-resolved WC labels are not.

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
```

After review, standardized ignored local CSVs can be generated with:

```text
python run_pipeline.py ingest-84k
```

## Project map

- `SOURCES.md`, `sources.yaml`: human- and machine-readable source registry
- `reports/`: inventory, scientific definitions, HCP status and project decisions
- `logs/pipeline_log.md`: dated audit trail
- `src/cleaning/`: composition, phase and pair standardization
- `src/ingestion/`: source-specific ingestion adapters
- `tests/`: scientifically important validation tests
- `run_pipeline.py`: modular command-line entry point

## Scientific safeguards

Raw provenance is retained; physically different SRO metrics are not merged; initial and relaxed features are separated; final DFT energy, volume and symmetry are excluded from default 84k predictors; direct ordering proxies are also excluded. Future validation must group related structures, compositions, trajectories and sources to prevent pseudo-replication.
