# Feature-set ablation analysis

Unified best-by-inner-CV configurations under the fixed alloy-held-out design:

- `BALANCED_PRELIMINARY` (198 declared): HistGradientBoosting, CV R² 0.8803 ± 0.0217; test R² 0.8997, MAE 0.0535.
- `FULL_CLEAN` (324 declared): HistGradientBoosting, CV R² 0.8783 ± 0.0255; test R² 0.8973, MAE 0.0539.
- `COMPOSITION_PLUS_INITIAL_STRUCTURE` (320 declared): HistGradientBoosting, CV R² 0.8783 ± 0.0259; test R² 0.8970, MAE 0.0543.
- `COMPOSITION_PLUS_PHASE` (205 declared): HistGradientBoosting, CV R² 0.1764 ± 0.1940; test R² 0.3339, MAE 0.1399.
- `MINIMAL_PRELIMINARY` (19 declared): HistGradientBoosting, CV R² 0.1008 ± 0.1973; test R² 0.3089, MAE 0.1436.
- `COMPOSITION_ONLY` (204 declared): HistGradientBoosting, CV R² 0.0262 ± 0.2340; test R² 0.2745, MAE 0.1447.

`THERMODYNAMIC_OR_ENERGETIC` is empty because every available energetic quantity is a relaxed/final-state outcome and remains excluded. Initial-structure gains must be weighed against portability and possible configuration sensitivity. The 19-feature minimal set is the intended cross-source baseline. [LITERATURE SUPPORT REQUIRED] for mechanistic claims.
