# Model overfitting analysis

## Selected HistGradientBoosting pipelines

- ALL: train R² 0.934, grouped-CV 0.880 ± 0.022, outer test 0.900; train–test gap 0.034.
- BCC: train R² 0.945, grouped-CV 0.883 ± 0.028, outer test 0.915; train–test gap 0.030.
- FCC: train R² 0.951, grouped-CV 0.894 ± 0.006, outer test 0.906; train–test gap 0.046.

These moderate gaps indicate some fitting to training configurations but do not erase strong grouped generalization. Early stopping and regularization were fixed before outer evaluation.

## Largest observed gaps

- FCC `SVR_subset` / `MINIMAL_PRELIMINARY`: train 0.285, grouped-CV -0.191 ± 0.230, outer test -0.226, gap 0.511.
- ALL `SVR_subset` / `MINIMAL_PRELIMINARY`: train 0.334, grouped-CV -0.143 ± 0.283, outer test -0.144, gap 0.478.
- BCC `SVR_subset` / `MINIMAL_PRELIMINARY`: train 0.245, grouped-CV -0.218 ± 0.158, outer test -0.178, gap 0.423.
- BCC `RandomForest` / `MINIMAL_PRELIMINARY`: train 0.364, grouped-CV -0.061 ± 0.279, outer test 0.194, gap 0.170.
- ALL `RandomForest` / `MINIMAL_PRELIMINARY`: train 0.414, grouped-CV 0.017 ± 0.225, outer test 0.256, gap 0.158.

The largest gaps are dominated by the capped SVR and weak minimal-set baselines, not the selected models. Outer grouped performance, not training accuracy or random-split accuracy, governs scientific conclusions.
