# Reproducibility audit

Audit date: 2026-08-22.

## Reproduction path

From the repository root, a local user with the immutable raw source tree can install `requirements.txt`, run the 34-test suite, and execute:

```text
python run_pipeline.py ingest-84k --dry-run
python run_pipeline.py build-phase3
python run_pipeline.py analyze-phase4
python run_pipeline.py train-phase5
python run_pipeline.py interpret-phase6
```

All commands use repository-relative paths. Phase 4/5/6 seeds are fixed, grouped split definitions are stored, and preprocessing is fitted within sklearn pipelines. Phase 6 compact ranking and size selection use only outer-training partitions; saved selection tables contain no outer-test metric. Compact outer metrics independently recompute from saved predictions.

## Verified controls

- Processed ML rows: 83,797; FCC 40,425; BCC 43,372; HCP 0.
- Target: `target_mean_abs_sro_shell1`; no SRO/target/direct-ordering field occurs in final predictor lists.
- Four final feature lists contain 324, 198, 10 and 18 unique predictors.
- Requested robustness and group-ablation CSVs have stable schemas and are readable with pandas.
- All eight Phase 6 PNGs have embedded resolution at or above 299 dpi and widths above 1,200 pixels.
- `data/raw/`, `data/processed/`, `models/`, virtual environments, caches and large binary/intermediate patterns remain ignored; no force-add is used.
- HCP candidates remain provisional/local and no HCP model or prediction is present.
- README documents the full command sequence, scope, leakage controls and local-only artifacts.
- `python -m unittest discover -s tests -v`: 34 tests passed in 30.2 s on the final audit run.

## Cost and environment notes

Phase 5 is the expensive broad comparison stage. Phase 6 avoids a new hyperparameter search but performs repeated fixed-model fits and took about 7.2 minutes on the audit workstation. Optional XGBoost, LightGBM and SHAP were not installed; final interpretation uses sklearn permutation importance, ablation and focused partial dependence. Generated Parquet datasets and joblib models are reproducible local artifacts and intentionally not version-controlled.
