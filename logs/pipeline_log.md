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
