# Unified versus phase-specific models

Primary alloy-system-held-out results:

- Unified: **HistGradientBoosting / BALANCED_PRELIMINARY**, R² 0.8997, MAE 0.0535, RMSE 0.0764.
- FCC-specific: **HistGradientBoosting / BALANCED_PRELIMINARY**, R² 0.9058, MAE 0.0348, RMSE 0.0534.
- BCC-specific: **HistGradientBoosting / BALANCED_PRELIMINARY**, R² 0.9154, MAE 0.0563, RMSE 0.0808.

Models were selected by inner grouped-CV R², never outer-test performance. Raw errors must be interpreted against phase target spread; normalized metrics are included in the tables. The comparison is exploratory because the Phase 4 feature investigation preceded creation of this outer test.

On the identical held-out phase rows, the phase-specific pipelines compare with the unified pipeline as follows:

- FCC: unified R² 0.8668, MAE 0.0438, RMSE 0.0635; phase-specific R² 0.9058, MAE 0.0348, RMSE 0.0534.
- BCC: unified R² 0.9038, MAE 0.0621, RMSE 0.0861; phase-specific R² 0.9154, MAE 0.0563, RMSE 0.0808.

Phase-specific fitting improves both phases, with the larger gain for FCC. This supports separate phase models for configuration-level prediction while retaining the unified model as a useful pooled baseline.
