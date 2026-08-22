# Phase 5 ML data validation

Phase 5 uses exactly **83,797** validated rows: **40,425 FCC**, **43,372 BCC**, and **0 HCP**. The 255 provisional HCP configurations are absent. `target_mean_abs_sro_shell1` is complete, finite, non-negative, and used only as the response.

The predictor library contains 348 Phase 4 candidates before set-specific filtering, with zero identifiers, zero direct SRO/order-parameter proxies, and zero relaxed/final-state leakage fields. `VarianceThreshold(0)` is the first step of every sklearn pipeline, so constants are learned and removed using training data only. Scalers for linear, regularized, and SVR models are also inside the pipeline. No imputation is required because the validated predictors are complete.

Phase 4's `BALANCED_PRELIMINARY` was informed by whole-dataset exploratory association rankings. It is therefore a predeclared exploratory set, not a pristine confirmatory selection. `FULL_CLEAN`, `MINIMAL_PRELIMINARY`, and physically defined composition ablations are reported alongside it. No HCP result is claimed.
